"""Zsh shell configuration."""

from pathlib import Path

from shell_configs.shells.base import AdditionalFile, ConfigFile, Shell


class ZshShell(Shell):
    """Zsh shell configuration handler."""

    @property
    def name(self) -> str:
        return "zsh"

    @property
    def display_name(self) -> str:
        return "Zsh"

    def get_config_files(self) -> list[ConfigFile]:
        """Get Zsh configuration files."""
        home = Path.home()
        return [
            ConfigFile(
                name=".zshrc",
                path=home / ".zshrc",
                repo_config_name="zshrc",
            ),
        ]

    def get_additional_files(self) -> list[AdditionalFile]:
        """Get additional files for Zsh shell.

        Discovers files from:
        - config/zsh/ (except zshrc)
        - config/shared-scripts/ (shell scripts shared across bash/zsh)

        Files are installed to ~/.zsh/
        """
        return self._discover_additional_files(
            ["zsh", "shared-scripts"],
            Path.home() / ".zsh",
        )

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get Zsh validation command."""
        return ["zsh", "-n", str(temp_file)]

    def _get_temp_suffix(self) -> str:
        """Get temp file suffix for Zsh."""
        return ".zsh"

    def supports_shared_config(self) -> bool:
        """Zsh supports shared configuration."""
        return True

    def get_managed_preamble(self) -> str | None:
        return (
            "# compdef stub — queues calls made before compinit runs\n"
            "if (( ! ${+functions[compdef]} )); then\n"
            "    typeset -ga _sc_compdef_queue\n"
            '    compdef() { _sc_compdef_queue+=("${(j: :)@}") }\n'
            "fi"
        )
