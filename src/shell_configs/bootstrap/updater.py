"""Update checking and application utilities."""

import json
import logging
import re
import subprocess
import urllib.request

from collections.abc import Callable
from dataclasses import dataclass

from .installer import (
    UV_NOT_FOUND_ERROR,
    is_command_available,
)
from .version import get_package_version, is_newer

logger = logging.getLogger(__name__)
GITHUB_REPO = "wpfleger96/shell-configs"


@dataclass
class UpdateInfo:
    """Information about available updates."""

    has_update: bool
    current_version: str
    latest_version: str
    source: str


def check_github_updates(
    repo: str, current_version: str, timeout: int = 10
) -> UpdateInfo:
    """Check GitHub tags for newer version.

    Args:
        repo: GitHub repository in format "owner/repo"
        current_version: Currently installed version
        timeout: Request timeout in seconds (default: 10)

    Returns:
        UpdateInfo with update status
    """
    try:
        url = f"https://api.github.com/repos/{repo}/tags"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", f"shell-configs/{current_version}")

        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode())

        if not data or len(data) == 0:
            return UpdateInfo(
                has_update=False,
                current_version=current_version,
                latest_version=current_version,
                source="github",
            )

        latest_tag = data[0]["name"]
        latest_version = latest_tag.lstrip("v")

        has_update = is_newer(latest_version, current_version)

        return UpdateInfo(
            has_update=has_update,
            current_version=current_version,
            latest_version=latest_version,
            source="github",
        )

    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as e:
        logger.debug(f"GitHub check failed: {e}")
        return UpdateInfo(
            has_update=False,
            current_version=current_version,
            latest_version=current_version,
            source="github",
        )


def perform_github_update(repo_url: str) -> tuple[bool, str, bool]:
    """Upgrade via uv tool install --force from GitHub.

    Args:
        repo_url: GitHub repository URL (e.g., git+ssh://git@github.com/owner/repo.git)

    Returns:
        Tuple of (success, message, was_upgraded)
        - success: Whether command succeeded
        - message: Human-readable status message
        - was_upgraded: True if package was actually upgraded (not already up-to-date)
    """
    if not is_command_available("uv"):
        return False, UV_NOT_FOUND_ERROR, False

    cmd = ["uv", "tool", "install", "--force", "--reinstall", repo_url]

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


UPDATABLE_TOOLS: list[ToolSpec] = [
    ToolSpec(
        tool_id="shell-configs",
        package_name="shell-configs",
        display_name="shell-configs",
        get_version=lambda: get_package_version("shell-configs"),
        is_installed=lambda: True,
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

    return check_github_updates(GITHUB_REPO, current, timeout)


def get_tool_by_id(tool_id: str) -> ToolSpec | None:
    """Look up tool spec by ID.

    Args:
        tool_id: Tool identifier (e.g., "shell-configs")

    Returns:
        ToolSpec if found, None otherwise
    """
    return next((t for t in UPDATABLE_TOOLS if t.tool_id == tool_id), None)
