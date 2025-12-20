"""Cursor IDE configuration."""

import platform
import subprocess

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.packages.packages import is_wsl
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell


def _get_windows_username() -> str:
    """Get Windows username when running in WSL.

    Returns:
        Windows username or empty string if unable to determine
    """
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERNAME%"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        try:
            result = subprocess.run(
                ["whoami.exe"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip().split("\\")[-1]
        except Exception:
            return ""


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
        if is_wsl():
            win_user = _get_windows_username()
            if not win_user:
                return None
            return Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/Cursor/User")
        elif platform.system() == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Cursor" / "User"
        else:
            return Path.home() / ".config" / "Cursor" / "User"

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
        return [
            AdditionalFile(
                name="settings.json",
                source_path=config_dir / "cursor" / "settings.json",
                target_path=cursor_dir / "settings.json",
            ),
            AdditionalFile(
                name="keybindings.json",
                source_path=config_dir / "cursor" / "keybindings.json",
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
