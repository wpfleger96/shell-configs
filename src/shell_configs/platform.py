"""Platform detection and abstraction."""

import platform

from enum import Enum
from functools import lru_cache


class Platform(Enum):
    """Supported platforms."""

    MACOS = "macos"
    WSL = "wsl"
    LINUX = "linux"

    @property
    def display_name(self) -> str:
        """Human-readable platform name."""
        mapping = {
            Platform.MACOS: "macOS",
            Platform.WSL: "WSL",
            Platform.LINUX: "Linux",
        }
        return mapping[self]


@lru_cache(maxsize=1)
def detect_platform() -> Platform:
    """Detect the current platform (cached).

    Returns:
        Platform enum value
    """
    system = platform.system().lower()

    if system == "darwin":
        return Platform.MACOS

    if system == "linux":
        try:
            with open("/proc/version") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    return Platform.WSL
        except OSError:
            pass
        return Platform.LINUX

    return Platform.LINUX


def is_platform(target: Platform) -> bool:
    """Check if running on a specific platform."""
    return detect_platform() == target
