"""Shell registry for managing available shells."""

from shell_configs.shells.base import Shell
from shell_configs.shells.bash import BashShell
from shell_configs.shells.cursor import CursorShell
from shell_configs.shells.git import GitShell
from shell_configs.shells.iterm2 import ITerm2Shell
from shell_configs.shells.vscode import VSCodeShell
from shell_configs.shells.xdg import XdgShell
from shell_configs.shells.zsh import ZshShell


class ShellRegistry:
    """Registry for managing shell implementations."""

    def __init__(self) -> None:
        """Initialize the shell registry."""
        self._shells: dict[str, Shell] = {}
        self._register_default_shells()

    def _register_default_shells(self) -> None:
        """Register the default shell implementations."""
        self.register(BashShell())
        self.register(ZshShell())
        self.register(GitShell())
        self.register(XdgShell())
        self.register(ITerm2Shell())
        self.register(CursorShell())
        self.register(VSCodeShell())

    def register(self, shell: Shell) -> None:
        """Register a shell implementation.

        Args:
            shell: Shell implementation to register
        """
        self._shells[shell.name] = shell

    def get(self, name: str) -> Shell | None:
        """Get a shell by name.

        Args:
            name: Shell name

        Returns:
            Shell implementation or None if not found
        """
        return self._shells.get(name)

    def get_all(self) -> list[Shell]:
        """Get all registered shells.

        Returns:
            List of all registered shells
        """
        return list(self._shells.values())

    def get_names(self) -> list[str]:
        """Get names of all registered shells.

        Returns:
            List of shell names
        """
        return sorted(self._shells.keys())

    def filter_by_names(self, names: list[str]) -> tuple[list[Shell], list[str]]:
        """Filter shells by names.

        Args:
            names: List of shell names to filter by

        Returns:
            Tuple of (matching shells, invalid names)
        """
        shells = []
        invalid = []

        for name in names:
            shell = self.get(name)
            if shell:
                shells.append(shell)
            else:
                invalid.append(name)

        return (shells, invalid)
