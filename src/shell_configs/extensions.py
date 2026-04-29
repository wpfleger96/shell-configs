"""IDE extension management for VSCode and Cursor."""

import logging
import subprocess

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell_configs.profiles.profile import Profile

logger = logging.getLogger(__name__)

BUILTIN_EXTENSIONS: dict[str, set[str]] = {
    "cursor": {"anysphere.cursorpyright"},
}


def load_extension_file(path: Path) -> set[str]:
    """Parse a plain-text extension list file.

    Lines starting with # are comments. Blank lines are ignored.
    Extension IDs are normalized to lowercase.
    """
    if not path.exists():
        return set()

    try:
        content = path.read_text()
    except OSError:
        return set()

    extensions: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        extensions.add(stripped.lower())
    return extensions


@dataclass(frozen=True)
class ExtensionDiff:
    """Result of comparing desired vs installed extensions."""

    missing: frozenset[str]
    extra: frozenset[str]
    matched: frozenset[str]


@dataclass(frozen=True)
class ExtensionResult:
    """Result of an install/uninstall operation for a single extension."""

    extension_id: str
    success: bool
    message: str


class ExtensionManager:
    """Manages IDE extensions via CLI tools."""

    def load_desired_extensions(
        self,
        shell_name: str,
        extension_paths: list[Path],
        profile: "Profile | None" = None,
    ) -> set[str]:
        """Load the desired extension set by merging base + IDE-specific + profile.

        Args:
            shell_name: IDE shell name (e.g., "vscode", "cursor")
            extension_paths: Ordered list of extension list file paths to merge
            profile: Optional profile with extension add/remove overrides
        """
        desired: set[str] = set()
        for path in extension_paths:
            desired |= load_extension_file(path)

        if profile and shell_name in profile.extensions:
            overrides = profile.extensions[shell_name]
            for ext in overrides.get("add", []):
                desired.add(ext.lower())
            for ext in overrides.get("remove", []):
                desired.discard(ext.lower())

        return desired

    def get_installed_extensions(self, cli_command: str) -> set[str]:
        """Query installed extensions via the IDE CLI.

        Args:
            cli_command: CLI binary name (e.g., "code", "cursor")

        Returns:
            Set of lowercase extension IDs
        """
        try:
            result = subprocess.run(
                [cli_command, "--list-extensions"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "%s --list-extensions failed: %s",
                    cli_command,
                    result.stderr.strip(),
                )
                return set()

            return {
                line.strip().lower()
                for line in result.stdout.splitlines()
                if line.strip()
            }
        except FileNotFoundError:
            logger.warning("%s not found in PATH", cli_command)
            return set()
        except subprocess.TimeoutExpired:
            logger.warning("%s --list-extensions timed out", cli_command)
            return set()

    def compute_diff(
        self,
        desired: set[str],
        installed: set[str],
        shell_name: str | None = None,
    ) -> ExtensionDiff:
        """Compare desired vs installed extensions.

        Args:
            desired: Set of desired extension IDs
            installed: Set of installed extension IDs
            shell_name: Optional shell name to filter out builtin extensions
        """
        builtins = BUILTIN_EXTENSIONS.get(shell_name or "", set())

        missing = desired - installed
        extra = (installed - desired) - builtins
        matched = desired & installed

        return ExtensionDiff(
            missing=frozenset(missing),
            extra=frozenset(extra),
            matched=frozenset(matched),
        )

    def install_extensions(
        self,
        cli_command: str,
        extensions: set[str],
        dry_run: bool = False,
    ) -> list[ExtensionResult]:
        """Install extensions via the IDE CLI.

        Continues on individual failures to handle marketplace gaps gracefully.
        """
        results: list[ExtensionResult] = []
        for ext_id in sorted(extensions):
            if dry_run:
                results.append(ExtensionResult(ext_id, True, f"Would install {ext_id}"))
                continue

            try:
                result = subprocess.run(
                    [cli_command, "--install-extension", ext_id, "--force"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    results.append(ExtensionResult(ext_id, True, f"Installed {ext_id}"))
                else:
                    msg = result.stderr.strip() or result.stdout.strip()
                    results.append(ExtensionResult(ext_id, False, msg))
            except FileNotFoundError:
                results.append(
                    ExtensionResult(ext_id, False, f"{cli_command} not found in PATH")
                )
                break
            except subprocess.TimeoutExpired:
                results.append(
                    ExtensionResult(ext_id, False, f"Timed out installing {ext_id}")
                )

        return results

    def uninstall_extensions(
        self,
        cli_command: str,
        extensions: set[str],
        dry_run: bool = False,
    ) -> list[ExtensionResult]:
        """Uninstall extensions via the IDE CLI."""
        results: list[ExtensionResult] = []
        for ext_id in sorted(extensions):
            if dry_run:
                results.append(
                    ExtensionResult(ext_id, True, f"Would uninstall {ext_id}")
                )
                continue

            try:
                result = subprocess.run(
                    [cli_command, "--uninstall-extension", ext_id],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    results.append(
                        ExtensionResult(ext_id, True, f"Uninstalled {ext_id}")
                    )
                else:
                    msg = result.stderr.strip() or result.stdout.strip()
                    results.append(ExtensionResult(ext_id, False, msg))
            except FileNotFoundError:
                results.append(
                    ExtensionResult(ext_id, False, f"{cli_command} not found in PATH")
                )
                break
            except subprocess.TimeoutExpired:
                results.append(
                    ExtensionResult(ext_id, False, f"Timed out uninstalling {ext_id}")
                )

        return results

    def export_extensions(self, cli_command: str, shell_name: str | None = None) -> str:
        """Export currently installed extensions as a sorted newline-separated string.

        Filters out builtin extensions to prevent poisoning config files.
        """
        installed = self.get_installed_extensions(cli_command)
        builtins = BUILTIN_EXTENSIONS.get(shell_name or "", set())
        return "\n".join(sorted(installed - builtins))
