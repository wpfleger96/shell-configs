"""Shared base classes for VS Code-compatible editor shells (VS Code, Cursor)."""

from __future__ import annotations

import logging

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform
from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell, StateDbEntry
from shell_configs.shells.utils import get_windows_appdata_roaming

if TYPE_CHECKING:
    from shell_configs.extensions import ExtensionInvoker

logger = logging.getLogger(__name__)


class EditorShell(Shell):
    """Cross-platform editor with a VS Code-style User directory layout.

    Subclasses set the class attributes; everything else (user-dir
    resolution, settings/keybindings additional files, extension list
    paths, state-db entries) is shared.
    """

    shell_name: ClassVar[str]  # "vscode" / "cursor"
    shell_display_name: ClassVar[str]  # "VS Code" / "Cursor"
    app_dir_name: ClassVar[str]  # "Code" / "Cursor" (platform app dir)
    config_subdir: ClassVar[str]  # repo config dir: "vscode" / "cursor"
    server_dir_name: ClassVar[str]  # ".vscode-server" / ".cursor-server"
    cli_name: ClassVar[str]  # "code" / "cursor"

    @property
    def name(self) -> str:
        return self.shell_name

    @property
    def display_name(self) -> str:
        return self.shell_display_name

    def _get_user_dir(self) -> Path | None:
        """Get the platform-specific editor User directory, or None."""
        if is_platform(Platform.WINDOWS) or is_platform(Platform.WSL):
            appdata = get_windows_appdata_roaming()
            if appdata is None:
                if is_platform(Platform.WSL):
                    logger.debug(
                        "%s: Windows AppData/Roaming not found", self.display_name
                    )
                return None
            return appdata / self.app_dir_name / "User"
        if is_platform(Platform.MACOS):
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / self.app_dir_name
                / "User"
            )
        return Path.home() / ".config" / self.app_dir_name / "User"

    def get_extension_cli(self) -> str | None:
        if is_platform(Platform.WINDOWS):
            from shell_configs.shells.utils import resolve_windows_cli

            return resolve_windows_cli(self.cli_name)
        return self.cli_name

    def get_extension_list_paths(self) -> list[Path]:
        config_dir = get_config_dir()
        return [
            config_dir / "editor" / "extensions.txt",
            config_dir / self.config_subdir / "extensions.txt",
        ]

    def get_extensions_json_path(self) -> Path | None:
        if not is_platform(Platform.WSL):
            return None
        path = Path.home() / self.server_dir_name / "extensions" / "extensions.json"
        return path if path.exists() else None

    def get_config_files(self) -> list[ConfigFile]:
        return []

    def get_additional_files(self) -> list[AdditionalFile]:
        """Get settings.json (editor base + app overrides) and keybindings.json."""
        user_dir = self._get_user_dir()
        if user_dir is None:
            return []
        config_dir = get_config_dir()
        editor_dir = config_dir / "editor"
        return [
            AdditionalFile(
                name="settings.json",
                source_path=config_dir / self.config_subdir / "settings.json",
                target_path=user_dir / "settings.json",
                base_source_path=editor_dir / "settings.json",
            ),
            AdditionalFile(
                name="keybindings.json",
                source_path=editor_dir / "keybindings.json",
                target_path=user_dir / "keybindings.json",
            ),
        ]

    def get_state_db_entries(self) -> list[StateDbEntry]:
        user_dir = self._get_user_dir()
        if user_dir is None:
            return []
        return [
            StateDbEntry(
                name="Link protection trusted domains",
                db_path=user_dir / "globalStorage" / "state.vscdb",
                key="http.linkProtectionTrustedDomains",
                value='["*"]',
            ),
        ]


class LocalEditorShell(Shell):
    """Windows-side (Local) extension management for an editor, from WSL.

    Only active on WSL. Manages the Local extension host using PowerShell
    to invoke the Windows-side CLI binary found by _find_windows_cmd().
    """

    shell_name: ClassVar[str]  # "vscode-local" / "cursor-local"
    shell_display_name: ClassVar[str]  # "VS Code (Local)" / "Cursor (Local)"
    config_subdir: ClassVar[str]  # repo config dir: "vscode" / "cursor"

    @property
    def name(self) -> str:
        return self.shell_name

    @property
    def display_name(self) -> str:
        return self.shell_display_name

    @abstractmethod
    def _find_windows_cmd(self) -> tuple[str, Path] | None:
        """Find the Windows-side CLI.

        Returns:
            Tuple of (Windows backslash path for PowerShell, WSL-accessible Path)
            or None if not found.
        """

    def get_extension_invoker(self) -> ExtensionInvoker | None:
        if not is_platform(Platform.WSL):
            return None
        result = self._find_windows_cmd()
        if result is None:
            return None
        win_path, _ = result
        from shell_configs.extensions import PowerShellExtensionInvoker

        return PowerShellExtensionInvoker(win_code_cmd_path=win_path)

    def get_extension_list_paths(self) -> list[Path]:
        return [get_config_dir() / self.config_subdir / "extensions-local.txt"]

    def get_config_files(self) -> list[ConfigFile]:
        return []
