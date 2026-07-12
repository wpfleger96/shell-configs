"""Update checking and application utilities."""

import json
import logging
import re
import subprocess
import sys

from collections.abc import Callable
from dataclasses import dataclass

from .detection import is_command_available
from .installer import (
    UV_NOT_FOUND_ERROR,
    get_tool_version,
)
from .version import is_newer

logger = logging.getLogger(__name__)


def fetch_changelog_entries(
    repo: str,
    current_version: str,
    latest_version: str,
    timeout: int = 10,
) -> list[tuple[str, str]]:
    """Fetch changelog entries for versions between current and latest.

    Uses GitHub Releases API via GitHub CLI for private repo authentication.

    Args:
        repo: GitHub repository in format "owner/repo"
        current_version: Currently installed version
        latest_version: Latest available version
        timeout: Request timeout in seconds (default: 10)

    Returns:
        List of (version, notes) tuples for each version in the range.
        Returns empty list on any error (private repo, network failure, etc).
    """
    try:
        if not is_command_available("gh"):
            return []

        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/releases",
                "--jq",
                "[.[] | {tag_name, body}]",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.debug(f"Changelog fetch failed: {result.stderr.strip()}")
            return []

        releases = json.loads(result.stdout)

        entries: list[tuple[str, str]] = []
        for release in releases:
            version = release["tag_name"].lstrip("v")
            if is_newer(version, current_version) and (
                version == latest_version or not is_newer(version, latest_version)
            ):
                entries.append((version, release.get("body", "")))

        return entries

    except subprocess.TimeoutExpired:
        logger.debug(f"Changelog fetch timed out after {timeout} seconds")
        return []
    except Exception as e:
        logger.debug(f"Changelog fetch failed: {e}")
        return []


@dataclass
class UpdateInfo:
    """Information about available updates."""

    has_update: bool
    current_version: str
    latest_version: str
    source: str
    changelog_entries: list[tuple[str, str]] | None = None


def check_github_updates(
    repo: str, current_version: str, timeout: int = 10
) -> UpdateInfo:
    """Check GitHub tags for newer version using GitHub CLI.

    Args:
        repo: GitHub repository in format "owner/repo"
        current_version: Currently installed version
        timeout: Request timeout in seconds (default: 10)

    Returns:
        UpdateInfo with update status

    Note:
        Requires GitHub CLI (gh) to be installed and authenticated.
        Install: https://cli.github.com
        Authenticate: gh auth login
    """
    try:
        if not is_command_available("gh"):
            logger.debug("GitHub CLI not found. Install from https://cli.github.com")
            return UpdateInfo(
                has_update=False,
                current_version=current_version,
                latest_version=current_version,
                source="github",
            )

        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/tags", "--jq", ".[0].name"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.debug(f"gh api failed: {result.stderr.strip()}")
            return UpdateInfo(
                has_update=False,
                current_version=current_version,
                latest_version=current_version,
                source="github",
            )

        latest_tag = result.stdout.strip()

        if not latest_tag:
            logger.debug("No tags found in repository")
            return UpdateInfo(
                has_update=False,
                current_version=current_version,
                latest_version=current_version,
                source="github",
            )

        latest_version = latest_tag.lstrip("v")

        has_update = is_newer(latest_version, current_version)

        changelog_entries = None
        if has_update:
            changelog_entries = fetch_changelog_entries(
                repo, current_version, latest_version, timeout
            )

        return UpdateInfo(
            has_update=has_update,
            current_version=current_version,
            latest_version=latest_version,
            source="github",
            changelog_entries=changelog_entries,
        )

    except subprocess.TimeoutExpired:
        logger.debug(f"GitHub check timed out after {timeout} seconds")
        return UpdateInfo(
            has_update=False,
            current_version=current_version,
            latest_version=current_version,
            source="github",
        )
    except Exception as e:
        logger.debug(f"GitHub check failed: {e}")
        return UpdateInfo(
            has_update=False,
            current_version=current_version,
            latest_version=current_version,
            source="github",
        )


def _spawn_deferred_upgrade(
    uv_cmd: list[str],
    post_upgrade_cmd: list[str] | None = None,
) -> tuple[bool, str, bool]:
    """Spawn a detached cmd.exe to run the upgrade after the current process exits.

    Used on Windows when upgrading shell-configs itself: the running .exe holds a
    lock on the Scripts/ directory, so uv cannot replace it while the process is
    alive. Delaying via a detached shell lets the current process exit first.
    """
    parts = ["timeout /t 3 /nobreak >nul", subprocess.list2cmdline(uv_cmd)]
    if post_upgrade_cmd:
        parts.append(subprocess.list2cmdline(post_upgrade_cmd))

    subprocess.Popen(
        ["cmd.exe", "/c", " && ".join(parts)],
        creationflags=0x00000008
        | 0x00000200,  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    return True, "deferred", True


def perform_github_update(
    repo_url: str,
    is_self: bool = False,
    post_upgrade_cmd: list[str] | None = None,
) -> tuple[bool, str, bool]:
    """Upgrade via uv tool install --force from GitHub.

    Args:
        repo_url: GitHub repository URL (e.g., git+https://github.com/owner/repo.git)
        is_self: True when upgrading the shell-configs binary itself. On Windows,
            triggers a spawn-and-exit strategy to avoid file-lock errors.
        post_upgrade_cmd: Optional command to run after the upgrade completes.
            Only used when is_self=True on Windows (deferred path).

    Returns:
        Tuple of (success, message, was_upgraded)
        - success: Whether command succeeded
        - message: Human-readable status message; "deferred" when a background
            upgrade was spawned (Windows self-upgrade)
        - was_upgraded: True if package was actually upgraded (not already up-to-date)
    """
    if not is_command_available("uv"):
        return False, UV_NOT_FOUND_ERROR, False

    cmd = ["uv", "tool", "install", "--force", "--reinstall", repo_url]

    if is_self and sys.platform == "win32":
        return _spawn_deferred_upgrade(cmd, post_upgrade_cmd)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            output = result.stdout + result.stderr

            upgrade_patterns = [
                r"Upgraded .+ from .+ to .+",
                r"Installed .+ \d+\.\d+",
                r"Successfully installed",
            ]

            already_up_to_date_patterns = [
                r"Nothing to upgrade",
                r"already.*installed",
                r"already.*up.*to.*date",
            ]

            was_upgraded = False
            if any(
                re.search(pattern, output, re.IGNORECASE)
                for pattern in upgrade_patterns
            ):
                was_upgraded = True
            elif any(
                re.search(pattern, output, re.IGNORECASE)
                for pattern in already_up_to_date_patterns
            ):
                was_upgraded = False
            else:
                was_upgraded = True

            return True, "Upgrade successful", was_upgraded

        error_msg = result.stderr.strip()
        if not error_msg:
            error_msg = "Upgrade failed with no error message"

        return False, error_msg, False

    except subprocess.TimeoutExpired:
        return False, "Upgrade timed out after 60 seconds", False
    except Exception as e:
        return False, f"Unexpected error: {e}", False


@dataclass
class ToolSpec:
    """Specification for an updatable tool."""

    tool_id: str
    package_name: str
    display_name: str
    get_version: Callable[[], str | None]
    is_installed: Callable[[], bool]
    github_repo: str


UPDATABLE_TOOLS: list[ToolSpec] = [
    ToolSpec(
        tool_id="shell-configs",
        package_name="shell-configs",
        display_name="shell-configs",
        get_version=lambda: get_tool_version("shell-configs"),
        is_installed=lambda: get_tool_version("shell-configs") is not None,
        github_repo="wpfleger96/shell-configs",
    ),
]


def check_tool_updates(tool: ToolSpec, timeout: int = 10) -> UpdateInfo | None:
    """Check for updates for any tool.

    Args:
        tool: Tool specification
        timeout: Request timeout in seconds (default: 10)

    Returns:
        UpdateInfo if tool is installed and update check succeeds, None otherwise
    """
    if not tool.is_installed():
        return None

    current = tool.get_version()
    if current is None:
        return None

    return check_github_updates(tool.github_repo, current, timeout)


def get_tool_by_id(tool_id: str) -> ToolSpec | None:
    """Look up tool spec by ID.

    Args:
        tool_id: Tool identifier (e.g., "shell-configs")

    Returns:
        ToolSpec if found, None otherwise
    """
    return next((t for t in UPDATABLE_TOOLS if t.tool_id == tool_id), None)
