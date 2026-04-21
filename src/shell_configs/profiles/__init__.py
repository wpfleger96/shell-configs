"""Profile system for shell-configs."""

from shell_configs.profiles.loader import ProfileLoader
from shell_configs.profiles.profile import (
    CircularInheritanceError,
    Profile,
    ProfileError,
    ProfileNotFoundError,
)
from shell_configs.profiles.state import resolve_active_profile

__all__ = [
    "CircularInheritanceError",
    "Profile",
    "ProfileError",
    "ProfileLoader",
    "ProfileNotFoundError",
    "resolve_active_profile",
]
