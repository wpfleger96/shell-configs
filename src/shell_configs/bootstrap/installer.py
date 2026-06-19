"""Tool installation utilities."""

import re
import subprocess
import tomllib

from enum import Enum, auto
from pathlib import Path

from .detection import (
    is_command_available,
    uv_tool_dir,
    uv_tool_site_packages_dir,
)


class ToolSource(Enum):
    """Source from which a tool was installed."""

    PYPI = auto()
    GITHUB = auto()
    LOCAL = auto()


UV_NOT_FOUND_ERROR = "uv not found in PATH. Install from https://docs.astral.sh/uv/"
GITHUB_REPO = "wpfleger96/shell-configs"


def make_github_install_url(repo: str) -> str:
    """Construct GitHub install URL for uv tool install.

    Args:
        repo: GitHub repository in format "owner/repo"

    Returns:
        Full git+ssh URL for uv tool install
    """
    return f"git+ssh://git@github.com/{repo}.git"


def _validate_package_name(package_name: str) -> bool:
    """Validate package name matches PyPI naming convention (PEP 508)."""
    return bool(re.match(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$", package_name))


def get_tool_config_dir(package_name: str = "shell-configs") -> Path:
    """Get config directory for a uv tool installation.

    Computes the expected path where uv tool install places the package:
    $XDG_DATA_HOME/uv/tools/{package}/lib/python{version}/site-packages/shell_configs/config/

    Args:
        package_name: Name of the uv tool package

    Returns:
        Path to the config directory in the uv tools location
    """

    return uv_tool_site_packages_dir(package_name) / "config"


def get_tool_scripts_dir(package_name: str = "shell-configs") -> Path:
    """Get scripts directory for a uv tool installation.

    Mirrors get_tool_config_dir() but for the scripts payload.
    """
    return uv_tool_site_packages_dir(package_name) / "scripts"


def get_tool_source(package_name: str) -> ToolSource | None:
    """Detect how a uv tool was installed.

    Args:
        package_name: Name of the uv tool package

    Returns:
        ToolSource.PYPI if installed from PyPI
        ToolSource.GITHUB if installed from GitHub
        None if tool not installed or receipt file not found
    """
    receipt_path = uv_tool_dir(package_name) / "uv-receipt.toml"

    if not receipt_path.exists():
        return None

    try:
        with open(receipt_path, "rb") as f:
            receipt = tomllib.load(f)

        requirements = receipt.get("tool", {}).get("requirements", [])
        if not requirements:
            return None

        first_req = requirements[0]
        if isinstance(first_req, dict):
            if "path" in first_req:
                return ToolSource.LOCAL
            if "git" in first_req and "github.com" in first_req["git"]:
                return ToolSource.GITHUB

        return ToolSource.PYPI

    except (OSError, tomllib.TOMLDecodeError, KeyError, IndexError):
        return None


def install_tool(
    force: bool = False,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Install shell-configs as a uv tool from GitHub.

    Args:
        force: Force reinstall if already installed
        dry_run: Show what would be done without executing

    Returns:
        Tuple of (success, message)
    """
    if not is_command_available("uv"):
        return False, UV_NOT_FOUND_ERROR

    cmd = ["uv", "tool", "install", make_github_install_url(GITHUB_REPO)]
    if force:
        cmd.insert(3, "--force")
        cmd.insert(4, "--reinstall")

    if dry_run:
        return True, f"Would run: {' '.join(cmd)}"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True, "Installation successful"

        error_msg = result.stderr.strip()
        if not error_msg:
            error_msg = "Installation failed with no error message"

        return False, error_msg

    except subprocess.TimeoutExpired:
        return False, "Installation timed out after 60 seconds"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def uninstall_tool(package_name: str = "shell-configs") -> tuple[bool, str]:
    """Uninstall package from uv tools.

    Args:
        package_name: Name of package to uninstall

    Returns:
        Tuple of (success, message)
    """
    if not _validate_package_name(package_name):
        return False, f"Invalid package name: {package_name}"

    if not is_command_available("uv"):
        return False, UV_NOT_FOUND_ERROR

    cmd = ["uv", "tool", "uninstall", package_name]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return True, "Uninstallation successful"

        error_msg = result.stderr.strip()
        if not error_msg:
            error_msg = "Uninstallation failed with no error message"

        return False, error_msg

    except subprocess.TimeoutExpired:
        return False, "Uninstallation timed out after 30 seconds"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def get_tool_version(tool_name: str) -> str | None:
    """Get installed version of a uv tool by parsing `uv tool list`.

    Args:
        tool_name: Name of the tool package (e.g., "shell-configs")

    Returns:
        Version string (e.g., "0.1.0") or None if not installed
    """
    if not _validate_package_name(tool_name):
        return None

    if not is_command_available("uv"):
        return None

    try:
        result = subprocess.run(
            ["uv", "tool", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            if line.startswith(tool_name):
                match = re.search(r"v?(\d+\.\d+\.\d+)", line)
                if match:
                    return match.group(1)

        return None

    except (subprocess.TimeoutExpired, Exception):
        return None
