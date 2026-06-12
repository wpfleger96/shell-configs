"""VS Code IDE configuration."""

from __future__ import annotations

from pathlib import Path

from shell_configs.shells.editor import EditorShell, LocalEditorShell
from shell_configs.shells.utils import get_windows_programs, get_windows_username


class VSCodeShell(EditorShell):
    """VS Code IDE configuration handler with cross-platform support."""

    shell_name = "vscode"
    shell_display_name = "VS Code"
    app_dir_name = "Code"
    config_subdir = "vscode"
    server_dir_name = ".vscode-server"
    cli_name = "code"


class VSCodeLocalShell(LocalEditorShell):
    """VS Code Windows-side (Local) extension management from WSL."""

    shell_name = "vscode-local"
    shell_display_name = "VS Code (Local)"
    config_subdir = "vscode"

    def _find_windows_cmd(self) -> tuple[str, Path] | None:
        win_user = get_windows_username()
        if not win_user:
            return None
        win_path = (
            f"C:\\Users\\{win_user}\\AppData\\Local\\Programs"
            f"\\Microsoft VS Code\\bin\\code.cmd"
        )
        programs = get_windows_programs()
        if programs is None:
            return None
        wsl_path = programs / "Microsoft VS Code" / "bin" / "code.cmd"
        if not wsl_path.exists():
            return None
        return win_path, wsl_path
