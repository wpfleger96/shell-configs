"""Tool installation utilities."""

import os
import sys

from pathlib import Path


def get_tool_config_dir(package_name: str = "shell-configs") -> Path:
    """Get config directory for a uv tool installation.

    Computes the expected path where uv tool install places the package:
    $XDG_DATA_HOME/uv/tools/{package}/lib/python{version}/site-packages/shell_configs/config/

    Args:
        package_name: Name of the uv tool package

    Returns:
        Path to the config directory in the uv tools location
    """
    data_home = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"

    return (
        Path(data_home)
        / "uv"
        / "tools"
        / package_name
        / "lib"
        / python_version
        / "site-packages"
        / "shell_configs"
        / "config"
    )
