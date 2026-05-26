"""Configuration file handling."""

from importlib.resources import files as resource_files
from pathlib import Path
from typing import TYPE_CHECKING

from shell_configs.platform import detect_platform

if TYPE_CHECKING:
    from shell_configs.profiles.profile import Profile


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
        self,
        shell_name: str,
        config_name: str | None,
        profile: Profile | None = None,
    ) -> str | None:
        """Get the content of a configuration file.

        Args:
            shell_name: Name of the shell (e.g., 'bash', 'zsh', 'git')
            config_name: Name of the config file (e.g., 'bashrc', 'zshrc'), or None for shared-only shells
            profile: Optional active Profile; shell_overrides for this shell are appended

        Returns:
            Content of the config file, or None if not found
        """
        if config_name is None:
            return None

        config_path = self.config_dir / shell_name / config_name
        if not config_path.exists():
            return None

        content = config_path.read_text().rstrip("\n")

        if profile and shell_name in profile.shell_overrides:
            override = profile.shell_overrides[shell_name].rstrip("\n")
            content = (
                f"{content}\n\n### Profile Override ({profile.name}) ###\n{override}"
            )

        return content

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

    def get_shared_config_content(
        self,
        shell_name: str,
        profile: Profile | None = None,
    ) -> str | None:
        """Get the content of shared configuration with platform overlay.

        This method:
        1. Loads the base shared config (shared.sh or shared.gitconfig)
        2. Appends platform-specific overlay if it exists
        3. Prepends SHELL_CONFIGS_DIR export for shell configs (not git)
        4. Appends profile shell_overrides["shared"] if present

        Args:
            shell_name: Name of the shell (e.g., 'bash', 'zsh', 'git')
            profile: Optional active Profile; shell_overrides["shared"] are appended

        Returns:
            Combined content with platform overlay, or None if not found
        """
        if shell_name == "git":
            base_path = self.config_dir / "shared.gitconfig"
            suffix = ".gitconfig"
        else:
            base_path = self.config_dir / "shared.sh"
            suffix = ".sh"

        if not base_path.exists():
            return None

        content = base_path.read_text().rstrip("\n")

        platform = detect_platform()
        overlay_path = self.config_dir / "platform" / f"{platform.value}{suffix}"

        if overlay_path.exists():
            overlay = overlay_path.read_text().rstrip("\n")
            if overlay:
                content = f"{content}\n\n### Platform-Specific ({platform.display_name}) ###\n{overlay}"

        if shell_name != "git":
            config_dir_export = f'export SHELL_CONFIGS_DIR="{self.config_dir}"'
            content = f"{config_dir_export}\n\n{content}"

        if shell_name != "git" and profile and "shared" in profile.shell_overrides:
            override = profile.shell_overrides["shared"].rstrip("\n")
            content = (
                f"{content}\n\n### Profile Override ({profile.name}) ###\n{override}"
            )

        return content
