"""VS Code IDE configuration."""

from __future__ import annotations

import logging

from pathlib import Path
from typing import TYPE_CHECKING

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import (
    get_windows_appdata_roaming,
    get_windows_programs,
    get_windows_username,
)

if TYPE_CHECKING:
    from shell_configs.extensions import ExtensionInvoker

logger = logging.getLogger(__name__)


class VSCodeShell(Shell):
    """VS Code IDE configuration handler with cross-platform support."""

    @property
    def name(self) -> str:
        return "vscode"

    @property
    def display_name(self) -> str:
        return "VS Code"

    def _get_vscode_user_dir(self) -> Path | None:
        """Get platform-specific VS Code User directory.

        Returns:
            Path to VS Code User directory or None if unable to determine
        """
        if is_platform(Platform.WINDOWS):
            appdata = get_windows_appdata_roaming()
            if appdata is None:
                return None
            return appdata / "Code" / "User"
        if is_platform(Platform.WSL):
            appdata = get_windows_appdata_roaming()
            if appdata is None:
                logger.debug("VS Code: Windows AppData/Roaming not found")
                return None
            return appdata / "Code" / "User"
        elif is_platform(Platform.MACOS):
            return Path.home() / "Library" / "Application Support" / "Code" / "User"
        else:
            return Path.home() / ".config" / "Code" / "User"

    def get_extension_cli(self) -> str | None:
        if is_platform(Platform.WINDOWS):
            from shell_configs.shells.utils import resolve_windows_cli

            return resolve_windows_cli("code")
        return "code"

    def get_extension_list_paths(self) -> list[Path]:
        config_dir = get_config_dir()
        return [
            config_dir / "editor" / "extensions.txt",
            config_dir / "vscode" / "extensions.txt",
        ]

    def get_extensions_json_path(self) -> Path | None:
        if not is_platform(Platform.WSL):
            return None
        path = Path.home() / ".vscode-server" / "extensions" / "extensions.json"
        return path if path.exists() else None

    def get_config_files(self) -> list[ConfigFile]:
        """Get VS Code configuration files.

        Returns:
            Empty list - no section-managed config files
        """
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        """Get additional files for VS Code.

        Returns:
            List of settings.json and keybindings.json
        """
        vscode_dir = self._get_vscode_user_dir()
        if vscode_dir is None:
            return []
        config_dir = get_config_dir()
        editor_dir = config_dir / "editor"
        return [
            AdditionalFile(
                name="settings.json",
                source_path=config_dir / "vscode" / "settings.json",
                target_path=vscode_dir / "settings.json",
                base_source_path=editor_dir / "settings.json",
            ),
            AdditionalFile(
                name="keybindings.json",
                source_path=editor_dir / "keybindings.json",
                target_path=vscode_dir / "keybindings.json",
            ),
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get VS Code validation command.

        Args:
            temp_file: Path to temporary file with content

        Returns:
            No-op command - JSON validation not required
        """
        return self._noop_validation_command()

    def _get_temp_suffix(self) -> str:
        """Get temp file suffix for VS Code.

        Returns:
            File suffix for JSON files
        """
        return ".json"


class VSCodeLocalShell(Shell):
    """VS Code Windows-side (Local) extension management from WSL.

    Only active on WSL. Manages the Local extension host using PowerShell
    to invoke the Windows code.cmd binary.
    """

    @property
    def name(self) -> str:
        return "vscode-local"

    @property
    def display_name(self) -> str:
        return "VS Code (Local)"

    def _find_windows_code_cmd(self) -> tuple[str, Path] | None:
        """Find the Windows-side code.cmd path.

        Returns:
            Tuple of (Windows backslash path for PowerShell, WSL-accessible Path)
            or None if not found.
        """
        win_user = get_windows_username()
        if not win_user:
            return None
        win_path = (
            f"C:\\Users\\{win_user}\\AppData\\Local\\Programs"
            f"\\Microsoft VS Code\\bin\\code.cmd"
        )
        programs = get_windows_programs()
        if programs is None:
            return None
        wsl_path = programs / "Microsoft VS Code" / "bin" / "code.cmd"
        if not wsl_path.exists():
            return None
        return win_path, wsl_path

    def get_extension_invoker(self) -> ExtensionInvoker | None:
        if not is_platform(Platform.WSL):
            return None
        result = self._find_windows_code_cmd()
        if result is None:
            return None
        win_path, _ = result
        from shell_configs.extensions import PowerShellExtensionInvoker

        return PowerShellExtensionInvoker(win_code_cmd_path=win_path)

    def get_extension_list_paths(self) -> list[Path]:
        config_dir = get_config_dir()
        return [config_dir / "vscode" / "extensions-local.txt"]

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        return []

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return self._noop_validation_command()

    def _get_temp_suffix(self) -> str:
        return ".json"
