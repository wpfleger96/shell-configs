"""Profile dataclass and error types."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Profile:
    """A named collection of configuration overrides applied on top of the base config."""

    name: str
    description: str = ""
    extends: str | None = None

    settings_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    shell_overrides: dict[str, str] = field(default_factory=dict)

    packages: dict[str, list[str]] = field(default_factory=dict)

    extensions: dict[str, dict[str, list[str]]] = field(default_factory=dict)


class ProfileError(Exception):
    """Base exception for profile-related errors."""


class ProfileNotFoundError(ProfileError):
    """Raised when a named profile does not exist."""


class CircularInheritanceError(ProfileError):
    """Raised when profile inheritance forms a cycle."""
