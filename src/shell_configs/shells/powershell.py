"""PowerShell configuration."""

import subprocess

from functools import lru_cache
from pathlib import Path

from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell


@lru_cache(maxsize=1)
def _get_powershell_profile_path() -> Path | None:
    for exe in ("pwsh", "powershell"):
        try:
            result = subprocess.run(
                [exe, "-NoProfile", "-Command", "Write-Output $PROFILE"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip())
        except FileNotFoundError, subprocess.TimeoutExpired:
            continue
    return None


class PowerShellShell(Shell):
    @property
    def name(self) -> str:
        return "powershell"

    @property
    def display_name(self) -> str:
        return "PowerShell"

    def get_config_files(self) -> list[ConfigFile]:
        profile = _get_powershell_profile_path()
        if profile is None:
            return []
        return [
            ConfigFile(
                name="Microsoft.PowerShell_profile.ps1",
                path=profile,
                repo_config_name="powershellprofile",
            ),
        ]

    def get_additional_files(self) -> list[AdditionalFile]:
        return []

    def supports_shared_config(self) -> bool:
        return True

    @property
    def shared_config_suffix(self) -> str:
        return ".ps1"

    def format_config_dir_export(self, config_dir: Path) -> str | None:
        return f"$env:SHELL_CONFIGS_DIR = '{config_dir}'"
