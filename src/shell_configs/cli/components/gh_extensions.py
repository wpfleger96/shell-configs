"""GhExtensionsComponent — gh CLI extension installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    Context,
    GhExtensionsPlan,
)


class GhExtensionsComponent(Component):
    label = "gh-extensions"
    display_name = "gh CLI Extensions"

    def plan(self, ctx: Context) -> GhExtensionsPlan:
        from shell_configs.bootstrap import is_command_available
        from shell_configs.gh_extensions import command_name, load_extensions

        desired = load_extensions()

        if not is_command_available("gh"):
            return GhExtensionsPlan(
                has_changes=True,
                gh_available=False,
                desired=desired,
            )

        from shell_configs.gh_extensions import list_installed

        installed = list_installed()
        missing = [
            ext
            for ext in desired
            if ext.repo not in installed and command_name(ext.repo) not in installed
        ]
        desired_keys = {ext.repo for ext in desired}
        desired_cmd_names = {command_name(ext.repo) for ext in desired}
        extra = {
            k for k in installed if k not in desired_keys and k not in desired_cmd_names
        }

        return GhExtensionsPlan(
            has_changes=bool(missing) or bool(extra),
            desired=desired,
            installed=installed,
            missing=missing,
            extra=extra,
        )

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, GhExtensionsPlan):
            raise TypeError(f"expected GhExtensionsPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return

        from shell_configs.display import console

        console.print(f"\n[bold cyan]{self.display_name}[/bold cyan]\n")

        if not plan.gh_available:
            console.print(
                "  [dim]gh not installed — will be installed by required packages first[/dim]"
            )
            return

        for ext in plan.missing:
            console.print(f"  [red]✗[/red] {ext.repo} (not installed)")
        for ext_name in sorted(plan.extra):
            console.print(f"  [dim]+[/dim] {ext_name} (not in manifest)")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, GhExtensionsPlan):
            raise TypeError(f"expected GhExtensionsPlan, got {type(plan).__name__}")
        if not plan.missing:
            return True

        from shell_configs.display import console
        from shell_configs.gh_extensions import install_extension

        all_ok = True
        for ext in plan.missing:
            success, msg = install_extension(
                ext.repo, pin=ext.pin, dry_run=ctx.dry_run, build_path=ext.build_path
            )
            if ctx.dry_run:
                console.print(f"[dim]→[/dim] {msg}")
            elif success:
                console.print(f"[green]✓[/green] {msg}")
            else:
                console.print(f"[red]✗[/red] {msg}")
                all_ok = False
        return all_ok

    def install(self, ctx: Context) -> bool:
        from shell_configs.display import console

        console.print()
        console.print("[yellow]Installing gh CLI extensions...[/yellow]")

        plan = self.plan(ctx)

        if not plan.missing:
            console.print("[green]✓[/green] All gh extensions already installed")
            return True

        return self.apply(ctx, plan)

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console

        plan = self.plan(ctx)

        if not plan.missing and not plan.extra:
            console.print(
                f"  [green]✓[/green] {len(plan.desired)}/{len(plan.desired)} extensions installed"
            )
        else:
            parts = []
            if plan.missing:
                parts.append(f"{len(plan.missing)} missing")
            if plan.extra:
                parts.append(f"{len(plan.extra)} unmanaged")
            console.print(
                f"  [yellow]⚠[/yellow] {len(plan.desired) - len(plan.missing)}/{len(plan.desired)} extensions installed "
                f"({', '.join(parts)})"
            )

        console.print()

    def diff(self, ctx: Context) -> bool:
        plan = self.plan(ctx)

        if not plan.has_changes:
            return False

        self.display_plan(plan)
        return True
