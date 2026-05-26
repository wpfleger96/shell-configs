"""Auto-update configuration management."""

import dataclasses
import logging

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class AutoUpdateConfig:
    """Configuration for backup retention and active profile."""

    backup_retention: int = 5
    active_profile: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutoUpdateConfig:
        """Create from dict, using dataclass defaults for missing keys."""
        fields = {f.name for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in fields}
        return cls(**kwargs)


def get_config_dir(package_name: str = "shell-configs") -> Path:
    """Get the config directory for the package.

    Args:
        package_name: Name of the package

    Returns:
        Path to config directory (e.g., ~/.shell-configs/)
    """
    config_dir = Path.home() / f".{package_name}"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path(package_name: str = "shell-configs") -> Path:
    """Get path to bootstrap config file.

    Args:
        package_name: Name of the package

    Returns:
        Path to update_config.yaml
    """
    return get_config_dir(package_name) / "update_config.yaml"


def load_auto_update_config(package_name: str = "shell-configs") -> AutoUpdateConfig:
    """Load auto-update configuration.

    Args:
        package_name: Name of the package

    Returns:
        AutoUpdateConfig with loaded or default values
    """
    config_path = get_config_path(package_name)

    if not config_path.exists():
        return AutoUpdateConfig()

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return AutoUpdateConfig.from_dict(data)
    except yaml.YAMLError, OSError:
        return AutoUpdateConfig()


def save_auto_update_config(
    config: AutoUpdateConfig, package_name: str = "shell-configs"
) -> None:
    """Save auto-update configuration.

    Args:
        config: Configuration to save
        package_name: Name of the package
    """
    config_path = get_config_path(package_name)

    try:
        new_data = asdict(config)

        if config_path.exists():
            with open(config_path) as f:
                existing_data = yaml.safe_load(f) or {}
            if existing_data == new_data:
                return

        with open(config_path, "w") as f:
            yaml.dump(new_data, f, default_flow_style=False, sort_keys=False)
    except OSError as e:
        logger.debug(f"Failed to save config to {config_path}: {e}")
