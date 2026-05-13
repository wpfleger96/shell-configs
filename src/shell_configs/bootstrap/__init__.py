"""Bootstrap module for system-wide installation and auto-update functionality.

This module provides utilities for:
- Installing tools via uv (GitHub-based)
- Checking for and applying updates from GitHub
- Managing auto-update configuration

Designed to be self-contained and easily extractable for use in other projects.
"""

from .config import (
    AutoUpdateConfig,
    get_config_dir,
    load_auto_update_config,
    save_auto_update_config,
)
from .installer import (
    UV_NOT_FOUND_ERROR,
    get_tool_config_dir,
    get_tool_version,
    install_tool,
    is_command_available,
    uninstall_tool,
)
from .updater import (
    UPDATABLE_TOOLS,
    check_tool_updates,
    get_tool_by_id,
    perform_github_update,
)
from .version import is_newer

__all__ = [
    "is_newer",
    "UV_NOT_FOUND_ERROR",
    "get_tool_config_dir",
    "get_tool_version",
    "install_tool",
    "is_command_available",
    "uninstall_tool",
    "UPDATABLE_TOOLS",
    "check_tool_updates",
    "get_tool_by_id",
    "perform_github_update",
    "AutoUpdateConfig",
    "get_config_dir",
    "load_auto_update_config",
    "save_auto_update_config",
]
