"""VS Code IDE configuration."""

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_username


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
        if is_platform(Platform.WSL):
            win_user = get_windows_username()
            if not win_user:
                return None
            return Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/Code/User")
        elif is_platform(Platform.MACOS):
            return Path.home() / "Library" / "Application Support" / "Code" / "User"
        else:
            return Path.home() / ".config" / "Code" / "User"

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
        return ["true"]

    def _get_temp_suffix(self) -> str:
        """Get temp file suffix for VS Code.

        Returns:
            File suffix for JSON files
        """
        return ".json"
