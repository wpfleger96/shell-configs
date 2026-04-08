"""iTerm2 terminal emulator configuration."""

from pathlib import Path

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import (
    AdditionalFile,
    ConfigFile,
    PreferencesFile,
    Shell,
)

ITERM2_PREFERENCES_DOMAIN = "com.googlecode.iterm2"


class ITerm2Shell(Shell):
    """iTerm2 terminal emulator configuration handler (macOS-only)."""

    @property
    def name(self) -> str:
        return "iterm2"

    @property
    def display_name(self) -> str:
        return "iTerm2"

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        if not is_platform(Platform.MACOS):
            return []
        config_dir = get_config_dir()
        dynamic_profiles_dir = (
            Path.home()
            / "Library"
            / "Application Support"
            / "iTerm2"
            / "DynamicProfiles"
        )
        backup_dir = Path.home() / ".config" / "shell-configs" / "backups" / "iterm2"
        return [
            AdditionalFile(
                name="shell-configs.json",
                source_path=config_dir / "iterm2" / "profile.json",
                target_path=dynamic_profiles_dir / "shell-configs.json",
                backup_dir=backup_dir,
            )
        ]

    def get_preferences_files(self) -> list[PreferencesFile]:
        if not is_platform(Platform.MACOS):
            return []
        config_dir = get_config_dir()
        return [
            PreferencesFile(
                name="iTerm2 Preferences",
                source_path=config_dir / "iterm2" / "preferences.json",
                domain=ITERM2_PREFERENCES_DOMAIN,
                app_name="iTerm2",
            )
        ]

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        return ["python3", "-m", "json.tool", str(temp_file)]

    def _get_temp_suffix(self) -> str:
        return ".json"
