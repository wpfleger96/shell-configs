"""Notepad++ configuration."""

from __future__ import annotations

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell
from shell_configs.shells.utils import get_windows_username


class NotepadPPShell(Shell):
    @property
    def name(self) -> str:
        return "notepadpp"

    @property
    def display_name(self) -> str:
        return "Notepad++"

    def _get_config_dir(self) -> Path | None:
        if not is_platform(Platform.WSL):
            return None
        win_user = get_windows_username()
        if not win_user:
            return None
        return Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/Notepad++")

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
        return ["true"]

    def _get_temp_suffix(self) -> str:
        return ".xml"
