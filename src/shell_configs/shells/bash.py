"""Bash shell configuration."""

from pathlib import Path

from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell


class BashShell(Shell):
    """Bash shell configuration handler."""

    @property
    def name(self) -> str:
        return "bash"

    @property
    def display_name(self) -> str:
        return "Bash"

    def get_config_files(self) -> list[ConfigFile]:
        """Get Bash configuration files."""
        home = Path.home()
        return [
            ConfigFile(
                name=".bashrc",
                path=home / ".bashrc",
                repo_config_name="bashrc",
            ),
        ]

    def get_additional_files(self, repo_root: Path) -> list[AdditionalFile]:
        """Get additional files for Bash shell.

        Discovers files from:
        - config/bash/ (except bashrc)
        - config/shared-scripts/ (shell scripts shared across bash/zsh)

        Files are installed to ~/.bash/
        """
        return self._discover_additional_files(
            repo_root,
            ["bash", "shared-scripts"],
            Path.home() / ".bash",
        )

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get Bash validation command."""
        return ["bash", "-n", str(temp_file)]

    def _get_temp_suffix(self) -> str:
        """Get temp file suffix for Bash."""
        return ".sh"

    def supports_shared_config(self) -> bool:
        """Bash supports shared configuration."""
        return True
