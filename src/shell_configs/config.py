"""Configuration file handling."""

from pathlib import Path


class ConfigReader:
    """Reads configuration files from the repository."""

    def __init__(self, repo_root: Path):
        """Initialize the config reader.

        Args:
            repo_root: Root directory of the repository
        """
        self.repo_root = repo_root
        self.config_dir = repo_root / "config"

    def get_config_content(
        self, shell_name: str, config_name: str | None
    ) -> str | None:
        """Get the content of a configuration file.

        Args:
            shell_name: Name of the shell (e.g., 'bash', 'zsh', 'git')
            config_name: Name of the config file (e.g., 'bashrc', 'zshrc'), or None for shared-only shells

        Returns:
            Content of the config file, or None if not found
        """
        if config_name is None:
            return None

        config_path = self.config_dir / shell_name / config_name
        if not config_path.exists():
            return None

        content = config_path.read_text()
        return content.rstrip("\n")

    def has_config(self, shell_name: str, config_name: str) -> bool:
        """Check if a configuration file exists.

        Args:
            shell_name: Name of the shell
            config_name: Name of the config file

        Returns:
            True if the config file exists
        """
        config_path = self.config_dir / shell_name / config_name
        return config_path.exists()

    def get_available_shells(self) -> list[str]:
        """Get a list of available shell configurations.

        Returns:
            List of shell names that have configuration directories
        """
        if not self.config_dir.exists():
            return []

        shells = []
        for item in self.config_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                shells.append(item.name)

        return sorted(shells)

    def get_shared_config_content(self, shell_name: str) -> str | None:
        """Get the content of a shared configuration file.

        Args:
            shell_name: Name of the shell (e.g., 'bash', 'zsh', 'git')

        Returns:
            Content of the shared config file, or None if not found
        """
        if shell_name == "git":
            config_path = self.config_dir / "shared.gitconfig"
        else:
            config_path = self.config_dir / "shared.sh"

        if not config_path.exists():
            return None

        content = config_path.read_text()
        return content.rstrip("\n")


def find_repo_root(start_path: Path | None = None) -> Path | None:
    """Find the repository root by looking for the config directory.

    Args:
        start_path: Path to start searching from (defaults to current directory)

    Returns:
        Path to the repository root, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while current != current.parent:
        config_dir = current / "config"
        if config_dir.exists() and config_dir.is_dir():
            return current
        current = current.parent

    return None
