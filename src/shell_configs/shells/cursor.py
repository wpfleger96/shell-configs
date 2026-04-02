"""Cursor IDE configuration."""

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_username


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
