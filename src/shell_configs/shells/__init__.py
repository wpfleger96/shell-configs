"""Shell configuration implementations."""

from shell_configs.shells.base import Shell
from shell_configs.shells.bash import BashShell
from shell_configs.shells.cursor import CursorShell
from shell_configs.shells.git import GitShell
from shell_configs.shells.iterm2 import ITerm2Shell
from shell_configs.shells.registry import ShellRegistry
from shell_configs.shells.vscode import VSCodeShell
from shell_configs.shells.xdg import XdgShell
from shell_configs.shells.zsh import ZshShell

__all__ = [
    "Shell",
    "BashShell",
    "ZshShell",
    "GitShell",
    "XdgShell",
    "ITerm2Shell",
    "CursorShell",
    "VSCodeShell",
    "ShellRegistry",
]
