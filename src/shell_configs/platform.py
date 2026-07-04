"""Platform detection and abstraction."""

import os
import platform as _platform

from enum import Enum
from functools import lru_cache


class Platform(Enum):
    """Supported platforms."""

    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"
    WSL = "wsl"

    @property
    def display_name(self) -> str:
        mapping = {
            Platform.MACOS: "macOS",
            Platform.LINUX: "Linux",
            Platform.WINDOWS: "Windows",
            Platform.WSL: "WSL",
        }
        return mapping[self]

    @property
    def is_unix_like(self) -> bool:
        return self in (Platform.MACOS, Platform.LINUX, Platform.WSL)

    @property
    def overlay_chain(self) -> list[str]:
        if self == Platform.WSL:
            return [Platform.LINUX.value, Platform.WSL.value]
        return [self.value]


@lru_cache(maxsize=1)
def detect_platform() -> Platform:
    system = _platform.system().lower()

    if system == "darwin":
        return Platform.MACOS

    if system == "windows":
        return Platform.WINDOWS

    if system == "linux":
        if "microsoft" in _platform.uname().release.lower():
            return Platform.WSL
        if os.environ.get("WSL_DISTRO_NAME"):
            return Platform.WSL
        return Platform.LINUX

    return Platform.LINUX


def is_platform(target: Platform) -> bool:
    return detect_platform() == target
