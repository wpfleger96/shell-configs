"""Shared tool-detection helpers for the bootstrap module.

Small, dependency-free utilities used by both the installer and updater for
detecting installed commands and locating uv tool installation paths.
"""

import os
import shutil
import sys

from pathlib import Path


def is_command_available(command: str) -> bool:
    """Check if a command is available in PATH.

    Args:
        command: Command name to check

    Returns:
        True if command is available, False otherwise
    """
    return shutil.which(command) is not None


def uv_tool_dir(package_name: str) -> Path:
    """Root directory of a uv tool installation.

    $XDG_DATA_HOME/uv/tools/{package} (the dir holding uv-receipt.toml). Owns the
    XDG_DATA_HOME fallback shared by the path helpers and receipt lookup.

    Args:
        package_name: Name of the uv tool package

    Returns:
        Path to the tool's root directory in the uv tools location
    """
    data_home = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(data_home) / "uv" / "tools" / package_name


def uv_tool_site_packages_dir(package_name: str) -> Path:
    """Compute the site-packages dir for a uv tool installation.

    Shared base path for a uv-installed tool's payload:
    $XDG_DATA_HOME/uv/tools/{package}/lib/python{version}/site-packages/shell_configs

    Callers append the final segment (e.g. "config" or "scripts").

    Args:
        package_name: Name of the uv tool package

    Returns:
        Path to the shell_configs package inside the uv tools location
    """
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"

    return (
        uv_tool_dir(package_name)
        / "lib"
        / python_version
        / "site-packages"
        / "shell_configs"
    )
