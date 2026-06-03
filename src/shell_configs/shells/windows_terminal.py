"""Windows Terminal configuration."""

from __future__ import annotations

import logging

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_appdata_local

logger = logging.getLogger(__name__)


class WindowsTerminalShell(Shell):
    @property
    def name(self) -> str:
        return "windows-terminal"

    @property
    def display_name(self) -> str:
        return "Windows Terminal"

    def _get_windows_terminal_settings_dir(self) -> Path | None:
        if is_platform(Platform.WINDOWS):
            import os

            localappdata = os.environ.get("LOCALAPPDATA")
            if not localappdata:
                return None
            return (
                Path(localappdata)
                / "Packages"
                / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
                / "LocalState"
            )
        if not is_platform(Platform.WSL):
            return None
        appdata_local = get_windows_appdata_local()
        if appdata_local is None:
            logger.debug("Windows Terminal: Windows AppData/Local not found")
            return None
        return (
            appdata_local
            / "Packages"
            / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
            / "LocalState"
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
                target_merge=True,
            ),
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return self._noop_validation_command()

    def _get_temp_suffix(self) -> str:
        return ".json"
