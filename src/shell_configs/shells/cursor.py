"""Cursor IDE configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_username

if TYPE_CHECKING:
    from shell_configs.extensions import ExtensionInvoker


class CursorShell(Shell):
    """Cursor IDE configuration handler with cross-platform support."""

    @property
    def name(self) -> str:
        return "cursor"

    @property
    def display_name(self) -> str:
        return "Cursor"

    def _get_cursor_user_dir(self) -> Path | None:
        """Get platform-specific Cursor User directory.

        Returns:
            Path to Cursor User directory or None if unable to determine
        """
        if is_platform(Platform.WSL):
            win_user = get_windows_username()
            if not win_user:
                return None
            return Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/Cursor/User")
        elif is_platform(Platform.MACOS):
            return Path.home() / "Library" / "Application Support" / "Cursor" / "User"
        else:
            return Path.home() / ".config" / "Cursor" / "User"

    def get_extension_cli(self) -> str | None:
        if is_platform(Platform.WSL):
            remote_cli = self._find_cursor_remote_cli()
            if remote_cli:
                return str(remote_cli)
            return None
        return "cursor"

    def _find_cursor_remote_cli(self) -> Path | None:
        server_bin = Path.home() / ".cursor-server" / "bin"
        if not server_bin.exists():
            return None
        try:
            hash_dirs = sorted(
                (d for d in server_bin.iterdir() if d.is_dir()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return None
        for d in hash_dirs:
            cli = d / "bin" / "remote-cli" / "cursor"
            if cli.exists():
                return cli
        return None

    def get_extension_list_paths(self) -> list[Path]:
        config_dir = get_config_dir()
        return [
            config_dir / "editor" / "extensions.txt",
            config_dir / "cursor" / "extensions.txt",
        ]

    def get_config_files(self) -> list[ConfigFile]:
        """Get Cursor configuration files.

        Returns:
            Empty list - no section-managed config files
        """
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        """Get additional files for Cursor.

        Returns:
            List of settings.json and keybindings.json
        """
        cursor_dir = self._get_cursor_user_dir()
        if cursor_dir is None:
            return []
        config_dir = get_config_dir()
        editor_dir = config_dir / "editor"
        return [
            AdditionalFile(
                name="settings.json",
                source_path=config_dir / "cursor" / "settings.json",
                target_path=cursor_dir / "settings.json",
                base_source_path=editor_dir / "settings.json",
            ),
            AdditionalFile(
                name="keybindings.json",
                source_path=editor_dir / "keybindings.json",
                target_path=cursor_dir / "keybindings.json",
            ),
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get Cursor validation command.

        Args:
            temp_file: Path to temporary file with content

        Returns:
            No-op command - JSON validation not required
        """
        return ["true"]

    def _get_temp_suffix(self) -> str:
        """Get temp file suffix for Cursor.

        Returns:
            File suffix for JSON files
        """
        return ".json"


class CursorLocalShell(Shell):
    """Cursor Windows-side (Local) extension management from WSL.

    Only active on WSL. Manages the Local extension host using PowerShell
    to invoke the Windows cursor.cmd binary.
    """

    @property
    def name(self) -> str:
        return "cursor-local"

    @property
    def display_name(self) -> str:
        return "Cursor (Local)"

    def _find_windows_cursor_cmd(self) -> tuple[str, Path] | None:
        win_user = get_windows_username()
        if not win_user:
            return None
        win_path = (
            f"C:\\Users\\{win_user}\\AppData\\Local\\Programs"
            f"\\cursor\\resources\\app\\bin\\cursor.cmd"
        )
        wsl_path = Path(
            f"/mnt/c/Users/{win_user}/AppData/Local/Programs"
            f"/cursor/resources/app/bin/cursor.cmd"
        )
        if not wsl_path.exists():
            return None
        return win_path, wsl_path

    def get_extension_invoker(self) -> ExtensionInvoker | None:
        if not is_platform(Platform.WSL):
            return None
        result = self._find_windows_cursor_cmd()
        if result is None:
            return None
        win_path, _ = result
        from shell_configs.extensions import PowerShellExtensionInvoker

        return PowerShellExtensionInvoker(win_code_cmd_path=win_path)

    def get_extension_list_paths(self) -> list[Path]:
        config_dir = get_config_dir()
        return [config_dir / "cursor" / "extensions-local.txt"]

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        return []

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return ["true"]

    def _get_temp_suffix(self) -> str:
        return ".json"
