"""Context dataclass and Component base class for the CLI registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Literal

if TYPE_CHECKING:
    from shell_configs.agents import Agent, DeprecatedAgentSpec
    from shell_configs.config import ConfigReader
    from shell_configs.extensions import ExtensionDiff
    from shell_configs.gh_extensions import GhExtension
    from shell_configs.languages import Language
    from shell_configs.packages.packages import Package
    from shell_configs.profiles.profile import Profile
    from shell_configs.script_manager import DiscoveredScript, ScriptStatus
    from shell_configs.shells.base import Shell
    from shell_configs.shells.registry import ShellRegistry
    from shell_configs.signing import StepResult


@dataclass(frozen=True)
class Context:
    dry_run: bool
    yes: bool
    force: bool
    profile_name: str | None
    profile: Profile | None
    selected_shells: tuple[Shell, ...]
    config_reader: ConfigReader
    registry: ShellRegistry


# ---------------------------------------------------------------------------
# Plan dataclasses — one per component, returned by Component.plan()
# ---------------------------------------------------------------------------


@dataclass
class ComponentPlan:
    """Base for all component plans. Subclass per component."""

    has_changes: bool = False


@dataclass
class FileDiff:
    """A single file diff produced by the configs component."""

    shell_name: str
    file_path: str
    diff_text: str
    file_type: str  # "config", "additional", or "preferences"
    current_content: str = ""
    desired_content: str = ""


@dataclass
class StateDbChange:
    """A state database entry that needs to be created or updated."""

    shell_name: str
    entry_name: str
    db_path: str
    key: str
    current_value: str | None
    desired_value: str


@dataclass
class ConfigsPlan(ComponentPlan):
    diffs: list[FileDiff] = field(default_factory=list)
    orphaned_additional_files: list[str] = field(default_factory=list)
    state_db_changes: list[StateDbChange] = field(default_factory=list)


@dataclass
class RequiredPackagesPlan(ComponentPlan):
    missing: list[Package] = field(default_factory=list)


@dataclass
class OptionalPackagesPlan(ComponentPlan):
    total: list[Package] = field(default_factory=list)
    missing: list[Package] = field(default_factory=list)


@dataclass
class SigningPlan(ComponentPlan):
    results: list[StepResult] = field(default_factory=list)
    failed: list[StepResult] = field(default_factory=list)
    gh_available: bool = True


@dataclass
class GhAuthPlan(ComponentPlan):
    auth_ok: bool = True
    missing_scopes: list[str] = field(default_factory=list)
    gh_available: bool = True


@dataclass
class ExtensionsPlan(ComponentPlan):
    per_shell: dict[str, ExtensionDiff] = field(default_factory=dict)
    ignored_per_shell: dict[str, frozenset[str]] = field(default_factory=dict)


@dataclass
class GhExtensionsPlan(ComponentPlan):
    desired: list[GhExtension] = field(default_factory=list)
    installed: dict[str, str | None] = field(default_factory=dict)
    missing: list[GhExtension] = field(default_factory=list)
    extra: set[str] = field(default_factory=set)
    gh_available: bool = True


@dataclass
class ScriptsPlan(ComponentPlan):
    entries: list[tuple[DiscoveredScript, ScriptStatus]] = field(default_factory=list)
    orphaned: list[str] = field(default_factory=list)


@dataclass
class LanguagesPlan(ComponentPlan):
    all_languages: list[Language] = field(default_factory=list)
    missing: list[Language] = field(default_factory=list)
    status_only: list[Language] = field(default_factory=list)


@dataclass
class AgentsPlan(ComponentPlan):
    all_agents: list[Agent] = field(default_factory=list)
    missing: list[Agent] = field(default_factory=list)
    deprecated_installed: list[DeprecatedAgentSpec] = field(default_factory=list)
    orphaned: list[str] = field(default_factory=list)


def expect_plan[P: ComponentPlan](plan: ComponentPlan, cls: type[P]) -> P:
    """Narrow a ComponentPlan to the concrete type a component expects."""
    if not isinstance(plan, cls):
        raise TypeError(f"expected {cls.__name__}, got {type(plan).__name__}")
    return plan


# ---------------------------------------------------------------------------
# Component base class
# ---------------------------------------------------------------------------


class Component:
    label: str = ""  # machine slug for progress spinners and error messages
    display_name: str = ""  # human-readable title for section headers
    # When the install command applies this component: "pre" components run
    # sequentially first (later components depend on the tools they install),
    # "post" components run sequentially last (they mutate shared gh auth
    # state), everything else applies in parallel.
    apply_stage: ClassVar[Literal["pre", "parallel", "post"]] = "parallel"

    def plan(self, ctx: Context) -> ComponentPlan:
        """Compute what needs to change (read-only, no prompts, no writes)."""
        return ComponentPlan()

    def display_plan(self, plan: ComponentPlan) -> None:
        """Render plan to console on the main thread."""

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        """Execute the plan (writes only, no prompts). Returns success."""
        return True

    def status(self, ctx: Context) -> None:
        """Display current status (read-only)."""

    def needs_sudo(self, ctx: Context, plan: ComponentPlan) -> bool:
        """Whether applying this plan may invoke sudo (install pre-authorizes once)."""
        return False

    def uninstall(self, ctx: Context) -> None:
        """Remove everything this component installed (used by the uninstall command)."""
