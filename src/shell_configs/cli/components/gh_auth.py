"""GhAuthComponent — GitHub CLI auth and OAuth scope setup."""

from __future__ import annotations

import sys

from shell_configs.cli.context import Component, ComponentPlan, Context, GhAuthPlan


class GhAuthComponent(Component):
    label = "gh-auth"

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

        from shell_configs.display import console

        console.print("\n[bold cyan]GitHub CLI Auth[/bold cyan]\n")

        if not plan.gh_available:
            console.print(
                "  [dim]gh not installed — auth validation will run after packages are installed[/dim]"
            )
            return

        if not plan.auth_ok:
            console.print("  [yellow]⚠[/yellow] GitHub CLI is not authenticated")

        for scope in plan.missing_scopes:
            console.print(f"  [yellow]⚠[/yellow] {scope} (missing)")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, GhAuthPlan):
            raise TypeError(f"expected GhAuthPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return True

        from shell_configs.display import console
        from shell_configs.signing import ensure_gh_auth, ensure_gh_scopes

        console.print()
        console.print("[yellow]Ensuring GitHub CLI auth and scopes...[/yellow]")

        interactive = sys.stdin.isatty()

        auth_ok, auth_msg = ensure_gh_auth(interactive=interactive)
        if auth_ok:
            console.print(f"[green]✓[/green] {auth_msg}")
        else:
            console.print(f"[red]✗[/red] {auth_msg}")
            return False

        if plan.missing_scopes:
            scopes_ok, scopes_msg = ensure_gh_scopes(
                scopes=plan.missing_scopes, interactive=interactive
            )
            if scopes_ok:
                console.print(f"[green]✓[/green] {scopes_msg}")
            else:
                console.print(f"[red]✗[/red] {scopes_msg}")
                return False

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.gh_auth import load_desired_scopes
        from shell_configs.signing import ensure_gh_auth, ensure_gh_scopes

        console.print("[bold cyan]GitHub CLI Auth[/bold cyan]\n")

        auth_ok, auth_msg = ensure_gh_auth(interactive=False)
        if auth_ok:
            console.print(f"  [green]✓[/green] {auth_msg}")
        else:
            console.print(f"  [yellow]⚠[/yellow] {auth_msg}")

        if auth_ok:
            desired = load_desired_scopes()
            scopes_ok, scopes_msg = ensure_gh_scopes(scopes=desired, interactive=False)
            if scopes_ok:
                console.print(f"  [green]✓[/green] {scopes_msg}")
            else:
                console.print(f"  [yellow]⚠[/yellow] {scopes_msg}")

        console.print()
