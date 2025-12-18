"""Configuration file handling."""

from importlib.resources import files as resource_files
from pathlib import Path


def get_config_dir() -> Path:
    """Get the config directory.

    Works in both development mode (editable install) and installed mode (PyPI wheel).
    Uses importlib.resources which handles both cases automatically.
    """
    try:
        config_resource = resource_files("shell_configs") / "config"
        return Path(str(config_resource))
    except Exception:
        return Path(__file__).parent / "config"


class ConfigReader:
    """Reads configuration files from the package."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the config reader.

        Args:
            config_dir: Optional override for config directory path.
                       If None, automatically locates using importlib.resources.
        """
        self.config_dir = config_dir if config_dir is not None else get_config_dir()

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
