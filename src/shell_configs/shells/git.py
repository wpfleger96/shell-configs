"""Git configuration."""

from pathlib import Path

from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell


class GitShell(Shell):
    """Git configuration handler."""

    @property
    def name(self) -> str:
        return "git"

    @property
    def display_name(self) -> str:
        return "Git"

    def get_config_files(self) -> list[ConfigFile]:
        """Get Git configuration files.

        Git uses only shared configuration (config/shared.gitconfig).
        Machine-specific settings should be added directly to ~/.gitconfig
        outside the shell-configs managed section.
        """
        home = Path.home()
        return [
            ConfigFile(
                name=".gitconfig",
                path=home / ".gitconfig",
                repo_config_name=None,
            ),
        ]

    def get_additional_files(self, repo_root: Path) -> list[AdditionalFile]:
        """Get additional files for Git.

        Discovers files from config/git/ directory.
        Files are installed to ~/.config/git/
        """
        return self._discover_additional_files(
            repo_root,
            ["git"],
            Path.home() / ".config" / "git",
        )

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get Git validation command."""
        return ["git", "config", "--list", "--file", str(temp_file)]

    def _get_temp_suffix(self) -> str:
        """Get temp file suffix for Git."""
        return ".gitconfig"

    def supports_shared_config(self) -> bool:
        """Git supports shared configuration."""
        return True
