"""Sublime Text configuration."""

from __future__ import annotations

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_username


class SublimeShell(Shell):
    @property
    def name(self) -> str:
        return "sublime"

    @property
    def display_name(self) -> str:
        return "Sublime Text"

    def _get_settings_dir(self) -> Path | None:
        if is_platform(Platform.WSL):
            win_user = get_windows_username()
            if not win_user:
                return None
            return Path(
                f"/mnt/c/Users/{win_user}/AppData/Roaming/Sublime Text/Packages/User"
            )
        elif is_platform(Platform.MACOS):
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Sublime Text"
                / "Packages"
                / "User"
            )
        else:
            return Path.home() / ".config" / "sublime-text" / "Packages" / "User"

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        settings_dir = self._get_settings_dir()
        if settings_dir is None:
            return []
        # settings_dir is .../Packages/User — three levels up is the base install dir
        # (e.g. "Sublime Text" or "sublime-text"). Skip if Sublime isn't installed.
        if not settings_dir.parent.parent.parent.exists():
            return []
        config_dir = get_config_dir()
        return [
            AdditionalFile(
                name="Preferences.sublime-settings",
                source_path=config_dir / "sublime" / "settings.json",
                target_path=settings_dir / "Preferences.sublime-settings",
                target_merge=True,
            ),
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return ["true"]

    def _get_temp_suffix(self) -> str:
        return ".json"
