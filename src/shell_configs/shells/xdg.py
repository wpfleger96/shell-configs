"""XDG configuration for mimeapps.list."""

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.packages.packages import is_wsl
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
        if not is_wsl():
            return []
        return [
            AdditionalFile(
                name="mimeapps.list",
                source_path=get_config_dir() / "xdg" / "mimeapps.list",
                target_path=Path.home() / ".config" / "mimeapps.list",
            )
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get XDG validation command.

        Args:
            temp_file: Path to temporary file with content

        Returns:
            No-op command - no validation needed for INI files
        """
        return ["true"]

    def _get_temp_suffix(self) -> str:
        """Get temp file suffix for XDG.

        Returns:
            File suffix for mimeapps.list
        """
        return ".list"
