"""XDG configuration for mimeapps.list."""

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell


class XdgShell(Shell):
    """XDG configuration handler for mimeapps.list (WSL-only)."""

    @property
    def name(self) -> str:
        return "xdg"

    @property
    def display_name(self) -> str:
        return "XDG"

    def get_config_files(self) -> list[ConfigFile]:
        """Get XDG configuration files.

        Returns:
            Empty list - no section-managed config files
        """
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        """Get additional files for XDG.

        Returns:
            List containing mimeapps.list if running on WSL
        """
        if not is_platform(Platform.WSL):
            return []
        return [
            AdditionalFile(
                name="mimeapps.list",
                source_path=get_config_dir() / "xdg" / "mimeapps.list",
                target_path=Path.home() / ".config" / "mimeapps.list",
                ini_merge=True,
            )
        ]
