"""Cursor IDE configuration."""

from __future__ import annotations

import logging

from pathlib import Path

from shell_configs.platform import Platform, is_platform
from shell_configs.shells.editor import EditorShell, LocalEditorShell
from shell_configs.shells.utils import get_windows_programs, get_windows_username

logger = logging.getLogger(__name__)


class CursorShell(EditorShell):
    """Cursor IDE configuration handler with cross-platform support."""

    shell_name = "cursor"
    shell_display_name = "Cursor"
    app_dir_name = "Cursor"
    config_subdir = "cursor"
    server_dir_name = ".cursor-server"
    cli_name = "cursor"

    def get_extension_cli(self) -> str | None:
        # Cursor's WSL extension host needs the remote CLI from ~/.cursor-server
        if is_platform(Platform.WSL):
            remote_cli = self._find_cursor_remote_cli()
            if remote_cli:
                return str(remote_cli)
            logger.info(
                "Cursor remote CLI not found — open a Cursor WSL window first to initialize"
            )
            return None
        return super().get_extension_cli()

    def _find_cursor_remote_cli(self) -> Path | None:
        server_bin = Path.home() / ".cursor-server" / "bin"
        if not server_bin.exists():
            return None
        try:
            hash_dirs = sorted(
                (d for d in server_bin.iterdir() if d.is_dir()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return None
        for d in hash_dirs:
            cli = d / "bin" / "remote-cli" / "cursor"
            if cli.exists():
                return cli
        return None


class CursorLocalShell(LocalEditorShell):
    """Cursor Windows-side (Local) extension management from WSL."""

    shell_name = "cursor-local"
    shell_display_name = "Cursor (Local)"
    config_subdir = "cursor"

    def _find_windows_cmd(self) -> tuple[str, Path] | None:
        win_user = get_windows_username()
        if not win_user:
            return None
        programs = get_windows_programs()
        if programs is None:
            return None
        base_win = f"C:\\Users\\{win_user}\\AppData\\Local\\Programs\\cursor"
        base_wsl = programs / "cursor"
        candidates = [
            (
                f"{base_win}\\_\\resources\\app\\bin\\cursor.cmd",
                base_wsl / "_" / "resources" / "app" / "bin" / "cursor.cmd",
            ),
            (
                f"{base_win}\\resources\\app\\bin\\cursor.cmd",
                base_wsl / "resources" / "app" / "bin" / "cursor.cmd",
            ),
        ]
        for win_path, wsl_path in candidates:
            if wsl_path.exists():
                return win_path, wsl_path
        return None
