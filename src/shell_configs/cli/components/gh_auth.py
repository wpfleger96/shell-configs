"""GhAuthComponent — GitHub CLI auth and OAuth scope setup."""

from __future__ import annotations

import sys

from shell_configs.cli.context import Component, ComponentPlan, Context, GhAuthPlan


class GhAuthComponent(Component):
    label = "gh-auth"
    display_name = "GitHub CLI Auth"

    def plan(self, ctx: Context) -> GhAuthPlan:
        from shell_configs.bootstrap import is_command_available

        if not is_command_available("gh"):
            return GhAuthPlan(has_changes=True, gh_available=False)

        from shell_configs.gh_auth import get_current_gh_scopes, load_desired_scopes
        from shell_configs.signing import ensure_gh_auth

        auth_ok, _ = ensure_gh_auth(interactive=False)
        if not auth_ok:
            desired = load_desired_scopes()
            return GhAuthPlan(has_changes=True, auth_ok=False, missing_scopes=desired)

        desired = load_desired_scopes()
        current = get_current_gh_scopes()
        missing = [s for s in desired if s not in current]
        if not missing:
            return GhAuthPlan(has_changes=False, auth_ok=True)

        return GhAuthPlan(has_changes=True, auth_ok=True, missing_scopes=missing)

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, GhAuthPlan):
            raise TypeError(f"expected GhAuthPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return

        from shell_configs.display import (
            print_dim,
            print_section,
            print_warning,
        )

        print_section(self.display_name)

        if not plan.gh_available:
            print_dim(
                "gh not installed — auth validation will run after packages are installed",
                indent=2,
            )
            return

        if not plan.auth_ok:
            print_warning("GitHub CLI is not authenticated", indent=2)

        for scope in plan.missing_scopes:
            print_warning(f"{scope} (missing)", indent=2)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, GhAuthPlan):
            raise TypeError(f"expected GhAuthPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return True

        from shell_configs.display import (
            console,
            print_error,
            print_progress,
            print_success,
        )
        from shell_configs.signing import ensure_gh_auth, ensure_gh_scopes

        console.print()
        print_progress("Ensuring GitHub CLI auth and scopes...")

        interactive = sys.stdin.isatty()

        auth_ok, auth_msg = ensure_gh_auth(interactive=interactive)
        if auth_ok:
            print_success(auth_msg)
        else:
            print_error(auth_msg)
            return False

        if plan.missing_scopes:
            scopes_ok, scopes_msg = ensure_gh_scopes(
                scopes=plan.missing_scopes, interactive=interactive
            )
            if scopes_ok:
                print_success(scopes_msg)
            else:
                print_error(scopes_msg)
                return False

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console, print_success, print_warning
        from shell_configs.gh_auth import load_desired_scopes
        from shell_configs.signing import ensure_gh_auth, ensure_gh_scopes

        auth_ok, auth_msg = ensure_gh_auth(interactive=False)
        if auth_ok:
            print_success(auth_msg, indent=2)
        else:
            print_warning(auth_msg, indent=2)

        if auth_ok:
            desired = load_desired_scopes()
            scopes_ok, scopes_msg = ensure_gh_scopes(scopes=desired, interactive=False)
            if scopes_ok:
                print_success(scopes_msg, indent=2)
            else:
                print_warning(scopes_msg, indent=2)

        console.print()
