"""Windows Terminal configuration."""

from __future__ import annotations

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_username


class WindowsTerminalShell(Shell):
    @property
    def name(self) -> str:
        return "windows-terminal"

    @property
    def display_name(self) -> str:
        return "Windows Terminal"

    def _get_windows_terminal_settings_dir(self) -> Path | None:
        if not is_platform(Platform.WSL):
            return None
        win_user = get_windows_username()
        if not win_user:
            return None
        return Path(
            f"/mnt/c/Users/{win_user}/AppData/Local/Packages"
            f"/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState"
        )

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        settings_dir = self._get_windows_terminal_settings_dir()
        if settings_dir is None:
            return []
        config_dir = get_config_dir()
        return [
            AdditionalFile(
                name="settings.json",
                source_path=config_dir / "windows-terminal" / "settings.json",
                target_path=settings_dir / "settings.json",
            ),
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return ["true"]

    def _get_temp_suffix(self) -> str:
        return ".json"
