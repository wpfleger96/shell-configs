"""IDE extension management for VSCode and Cursor."""

import json
import logging
import re
import subprocess

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell_configs.profiles.profile import Profile

logger = logging.getLogger(__name__)

_EXTENSION_ID_RE = re.compile(r"^[a-z0-9_-]+\.[a-z0-9_-]+$")

BUILTIN_EXTENSIONS: dict[str, set[str]] = {
    "vscode": {"github.copilot-chat"},
    "vscode-local": {"github.copilot-chat", "ms-vscode-remote.remote-wsl"},
    "cursor": {
        "anysphere.cursorpyright",
        "github.copilot-chat",
        "ms-python.vscode-pylance",
    },
    "cursor-local": {
        "anysphere.cursorpyright",
        "anysphere.remote-wsl",
        "ms-vscode-remote.remote-wsl",
    },
}


class ExtensionInvoker(ABC):
    """Encapsulates how to invoke a VS Code-compatible CLI for extension management."""

    @abstractmethod
    def list_command(self) -> list[str]: ...

    @abstractmethod
    def install_command(self, ext_id: str) -> list[str]: ...

    @abstractmethod
    def uninstall_command(self, ext_id: str) -> list[str]: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...


@dataclass(frozen=True)
class CliExtensionInvoker(ExtensionInvoker):
    """Standard CLI-based invoker (e.g., 'code', 'cursor')."""

    cli: str

    @property
    def display_name(self) -> str:
        return self.cli

    def list_command(self) -> list[str]:
        return [self.cli, "--list-extensions"]

    def install_command(self, ext_id: str) -> list[str]:
        return [self.cli, "--install-extension", ext_id, "--force"]

    def uninstall_command(self, ext_id: str) -> list[str]:
        return [self.cli, "--uninstall-extension", ext_id]


@dataclass(frozen=True)
class PowerShellExtensionInvoker(ExtensionInvoker):
    """PowerShell-based invoker for Windows-side VS Code from WSL."""

    win_code_cmd_path: str

    @property
    def display_name(self) -> str:
        return "powershell.exe"

    def _ps_command(self, args: str) -> list[str]:
        return [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"$ErrorActionPreference = 'SilentlyContinue'; "
            f"& '{self.win_code_cmd_path}' {args} 2>$null; "
            f"exit $LASTEXITCODE",
        ]

    def list_command(self) -> list[str]:
        return self._ps_command("--list-extensions")

    def install_command(self, ext_id: str) -> list[str]:
        return self._ps_command(f"--install-extension {ext_id} --force")

    def uninstall_command(self, ext_id: str) -> list[str]:
        return self._ps_command(f"--uninstall-extension {ext_id}")


def get_builtin_extensions(shell_name: str | None) -> frozenset[str]:
    """Get the builtin extension IDs for an IDE shell."""
    return frozenset(BUILTIN_EXTENSIONS.get(shell_name or "", set()))


def is_builtin_install_error(message: str) -> bool:
    """Check whether CLI install output indicates the extension is builtin."""
    return "built-in extension" in message.lower()


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


def load_extensions_json(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to parse extensions manifest: %s", path)
        return None
    extensions: set[str] = set()
    for entry in data:
        try:
            ext_id = entry["identifier"]["id"].lower().strip()
            if _EXTENSION_ID_RE.match(ext_id):
                extensions.add(ext_id)
        except (KeyError, AttributeError):
            continue
    return extensions


@dataclass(frozen=True)
class ExtensionDiff:
    """Result of comparing desired vs installed extensions."""

    missing: frozenset[str]
    extra: frozenset[str]
    matched: frozenset[str]
    ignored: frozenset[str] = frozenset()


class ExtensionResultStatus(StrEnum):
    """Result classification for an extension install or uninstall attempt."""

    SUCCESS = "success"
    SKIPPED_BUILTIN = "skipped_builtin"
    FAILED = "failed"


@dataclass(frozen=True)
class ExtensionResult:
    """Result of an install/uninstall operation for a single extension."""

    extension_id: str
    success: bool
    message: str
    status: ExtensionResultStatus = ExtensionResultStatus.SUCCESS


class ExtensionManager:
    """Manages IDE extensions via CLI tools."""

    def load_desired_extensions(
        self,
        shell_name: str,
        extension_paths: list[Path],
        profile: Profile | None = None,
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

    def _get_installed_via_cli(
        self, cli_command: str | None = None, *, invoker: ExtensionInvoker | None = None
    ) -> set[str] | None:
        if invoker is None:
            if cli_command is None:
                return None
            invoker = CliExtensionInvoker(cli_command)

        try:
            result = subprocess.run(
                invoker.list_command(),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "%s --list-extensions failed: %s",
                    invoker.display_name,
                    result.stderr.strip(),
                )
                return None

            installed: set[str] = set()
            for line in result.stdout.splitlines():
                stripped = line.strip().lower()
                if stripped and _EXTENSION_ID_RE.match(stripped):
                    installed.add(stripped)
            return installed
        except FileNotFoundError:
            logger.warning("%s not found in PATH", invoker.display_name)
            return None
        except subprocess.TimeoutExpired:
            logger.warning("%s --list-extensions timed out", invoker.display_name)
            return None

    def get_installed_extensions(
        self,
        cli_command: str | None = None,
        *,
        invoker: ExtensionInvoker | None = None,
        extensions_json_path: Path | None = None,
    ) -> set[str] | None:
        cli_result = self._get_installed_via_cli(cli_command, invoker=invoker)
        if cli_result is not None and len(cli_result) > 0:
            return cli_result

        if extensions_json_path is not None:
            fs_result = load_extensions_json(extensions_json_path)
            if fs_result is not None:
                logger.debug(
                    "Using filesystem fallback for extension listing: %s",
                    extensions_json_path,
                )
                return fs_result

        return cli_result

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
        builtins = get_builtin_extensions(shell_name)
        ignored = frozenset(desired & builtins)
        managed_desired = desired - builtins
        managed_installed = installed - builtins

        missing = frozenset(managed_desired - managed_installed)
        extra = frozenset(managed_installed - managed_desired)
        matched = frozenset(managed_desired & managed_installed)

        return ExtensionDiff(
            missing=missing,
            extra=extra,
            matched=matched,
            ignored=ignored,
        )

    def install_extensions(
        self,
        cli_command: str | None = None,
        extensions: set[str] | None = None,
        dry_run: bool = False,
        *,
        invoker: ExtensionInvoker | None = None,
    ) -> list[ExtensionResult]:
        """Install extensions via the IDE CLI.

        Continues on individual failures to handle marketplace gaps gracefully.
        """
        if extensions is None:
            extensions = set()
        if invoker is None:
            if cli_command is None:
                return []
            invoker = CliExtensionInvoker(cli_command)

        results: list[ExtensionResult] = []
        for ext_id in sorted(extensions):
            if dry_run:
                results.append(ExtensionResult(ext_id, True, f"Would install {ext_id}"))
                continue

            try:
                result = subprocess.run(
                    invoker.install_command(ext_id),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    results.append(ExtensionResult(ext_id, True, f"Installed {ext_id}"))
                else:
                    msg = result.stderr.strip() or result.stdout.strip()
                    if is_builtin_install_error(msg):
                        results.append(
                            ExtensionResult(
                                ext_id,
                                True,
                                msg,
                                status=ExtensionResultStatus.SKIPPED_BUILTIN,
                            )
                        )
                    else:
                        results.append(
                            ExtensionResult(
                                ext_id,
                                False,
                                msg,
                                status=ExtensionResultStatus.FAILED,
                            )
                        )
            except FileNotFoundError:
                results.append(
                    ExtensionResult(
                        ext_id,
                        False,
                        f"{invoker.display_name} not found in PATH",
                        status=ExtensionResultStatus.FAILED,
                    )
                )
                break
            except subprocess.TimeoutExpired:
                results.append(
                    ExtensionResult(
                        ext_id,
                        False,
                        f"Timed out installing {ext_id}",
                        status=ExtensionResultStatus.FAILED,
                    )
                )

        return results

    def uninstall_extensions(
        self,
        cli_command: str | None = None,
        extensions: set[str] | None = None,
        dry_run: bool = False,
        *,
        invoker: ExtensionInvoker | None = None,
    ) -> list[ExtensionResult]:
        """Uninstall extensions via the IDE CLI."""
        if extensions is None:
            extensions = set()
        if invoker is None:
            if cli_command is None:
                return []
            invoker = CliExtensionInvoker(cli_command)

        results: list[ExtensionResult] = []
        for ext_id in sorted(extensions):
            if dry_run:
                results.append(
                    ExtensionResult(ext_id, True, f"Would uninstall {ext_id}")
                )
                continue

            try:
                result = subprocess.run(
                    invoker.uninstall_command(ext_id),
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
                    results.append(
                        ExtensionResult(
                            ext_id,
                            False,
                            msg,
                            status=ExtensionResultStatus.FAILED,
                        )
                    )
            except FileNotFoundError:
                results.append(
                    ExtensionResult(
                        ext_id,
                        False,
                        f"{invoker.display_name} not found in PATH",
                        status=ExtensionResultStatus.FAILED,
                    )
                )
                break
            except subprocess.TimeoutExpired:
                results.append(
                    ExtensionResult(
                        ext_id,
                        False,
                        f"Timed out uninstalling {ext_id}",
                        status=ExtensionResultStatus.FAILED,
                    )
                )

        return results
