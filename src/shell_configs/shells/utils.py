"""Shared utilities for shell configuration handlers."""

import configparser
import logging
import subprocess

from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_windows_username() -> str:
    """Get Windows username when running in WSL.

    Returns:
        Windows username or empty string if unable to determine
    """
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERNAME%"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        username = result.stdout.strip()
        if result.returncode == 0 and username:
            return username
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["whoami.exe"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        username = result.stdout.strip().split("\\")[-1]
        if result.returncode == 0 and username:
            return username
    except Exception:
        pass

    logger.warning("Unable to detect Windows username — WSL interop may be disabled")
    return ""


@lru_cache(maxsize=1)
def get_wsl_windows_drive(drive: str = "c") -> Path:
    """Get the WSL mount path for a Windows drive letter.

    Reads [automount] root from /etc/wsl.conf, defaulting to /mnt/.
    """
    mount_root = "/mnt/"
    try:
        cp = configparser.ConfigParser()
        cp.read("/etc/wsl.conf")
        mount_root = cp.get("automount", "root", fallback="/mnt/")
        if not mount_root.endswith("/"):
            mount_root += "/"
    except configparser.Error:
        pass
    return Path(f"{mount_root}{drive}")


def get_windows_home() -> Path | None:
    """Return the Windows user home directory via WSL mount, or None if unavailable."""
    username = get_windows_username()
    if not username:
        return None
    home = get_wsl_windows_drive() / "Users" / username
    return home if home.is_dir() else None


def get_windows_appdata_roaming() -> Path | None:
    """Return the Windows AppData/Roaming path, or None if unavailable."""
    home = get_windows_home()
    if home is None:
        return None
    appdata = home / "AppData" / "Roaming"
    return appdata if appdata.is_dir() else None


def get_windows_appdata_local() -> Path | None:
    """Return the Windows AppData/Local path, or None if unavailable."""
    home = get_windows_home()
    if home is None:
        return None
    appdata = home / "AppData" / "Local"
    return appdata if appdata.is_dir() else None


def get_windows_programs() -> Path | None:
    """Return the Windows AppData/Local/Programs path, or None if unavailable."""
    local = get_windows_appdata_local()
    if local is None:
        return None
    programs = local / "Programs"
    return programs if programs.is_dir() else None
