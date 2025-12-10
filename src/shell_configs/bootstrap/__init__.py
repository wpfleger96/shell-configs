"""Bootstrap module for system-wide installation and auto-update functionality.

This module provides utilities for:
- Installing tools via uv (GitHub-based)
- Checking for and applying updates from GitHub
- Managing auto-update configuration

Designed to be self-contained and easily extractable for use in other projects.
"""

from .config import (
    AutoUpdateConfig,
    clear_all_pending_updates,
    clear_pending_update,
    get_config_dir,
    get_config_path,
    get_pending_update_path,
    load_all_pending_updates,
    load_auto_update_config,
    load_pending_update,
    save_auto_update_config,
    save_pending_update,
    should_check_now,
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
    ToolSpec,
    UpdateInfo,
    check_github_updates,
    check_tool_updates,
    get_tool_by_id,
    perform_github_update,
)
from .version import get_package_version, is_newer, parse_version

__all__ = [
    "get_package_version",
    "is_newer",
    "parse_version",
    "UV_NOT_FOUND_ERROR",
    "get_tool_config_dir",
    "get_tool_version",
    "install_tool",
    "is_command_available",
    "uninstall_tool",
    "UPDATABLE_TOOLS",
    "ToolSpec",
    "UpdateInfo",
    "check_github_updates",
    "check_tool_updates",
    "get_tool_by_id",
    "perform_github_update",
    "AutoUpdateConfig",
    "clear_all_pending_updates",
    "clear_pending_update",
    "get_config_dir",
    "get_config_path",
    "get_pending_update_path",
    "load_all_pending_updates",
    "load_auto_update_config",
    "load_pending_update",
    "save_auto_update_config",
    "save_pending_update",
    "should_check_now",
]
