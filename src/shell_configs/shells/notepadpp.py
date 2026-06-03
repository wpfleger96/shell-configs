"""Notepad++ configuration."""

from __future__ import annotations

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_appdata_roaming


class NotepadPPShell(Shell):
    @property
    def name(self) -> str:
        return "notepadpp"

    @property
    def display_name(self) -> str:
        return "Notepad++"

    def _get_config_dir(self) -> Path | None:
        if is_platform(Platform.WINDOWS):
            appdata = get_windows_appdata_roaming()
            if appdata is None:
                return None
            return appdata / "Notepad++"
        if not is_platform(Platform.WSL):
            return None
        appdata = get_windows_appdata_roaming()
        if appdata is None:
            return None
        return appdata / "Notepad++"

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        config_dir = self._get_config_dir()
        if config_dir is None:
            return []
        repo_config_dir = get_config_dir()
        return [
            AdditionalFile(
                name="config.xml",
                source_path=repo_config_dir / "notepadpp" / "config.xml",
                target_path=config_dir / "config.xml",
                xml_guiconfig_merge=True,
            ),
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return self._noop_validation_command()

    def _get_temp_suffix(self) -> str:
        return ".xml"
