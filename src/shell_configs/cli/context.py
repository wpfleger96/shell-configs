"""Context dataclass and Component base class for the CLI registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell_configs.config import ConfigReader
    from shell_configs.profiles.profile import Profile
    from shell_configs.shells.base import Shell
    from shell_configs.shells.registry import ShellRegistry


@dataclass(frozen=True)
class Context:
    dry_run: bool
    yes: bool
    profile_name: str | None
    profile: Profile | None
    selected_shells: list[Shell]
    config_reader: ConfigReader
    registry: ShellRegistry


class Component:
    label: str = ""

    def install(self, ctx: Context) -> bool:
        return True

    def status(self, ctx: Context) -> None:
        pass

    def diff(self, ctx: Context) -> bool:
        return False

    def uninstall(self, ctx: Context) -> None:
        pass
