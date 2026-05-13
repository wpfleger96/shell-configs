"""SigningComponent — SSH key lifecycle setup and status."""

from __future__ import annotations

from shell_configs.cli.context import Component, ComponentPlan, Context, SigningPlan


class SigningComponent(Component):
    label = "signing"

    def plan(self, ctx: Context) -> SigningPlan:
        from shell_configs.signing import setup_signing

        results = setup_signing(auto_fix=False, interactive=False)
        failed = [r for r in results if not r.success and not r.skipped]
        return SigningPlan(has_changes=bool(failed), results=results, failed=failed)

    def display_plan(self, plan: ComponentPlan) -> None:
        assert isinstance(plan, SigningPlan)
        if not plan.has_changes:
            return

        from shell_configs.display import console

        console.print("\n[bold cyan]SSH Key Lifecycle[/bold cyan]\n")
        for r in plan.failed:
            console.print(f"  [yellow]⚠[/yellow] {r.message}")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        assert isinstance(plan, SigningPlan)
        if not plan.has_changes:
            return True

        from shell_configs.signing import setup_signing

        results = setup_signing(auto_fix=True, interactive=False)
        return all(r.success or r.skipped for r in results)

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        from rich.prompt import Confirm

        from shell_configs.display import console
        from shell_configs.signing import setup_signing

        console.print()
        console.print("[yellow]Validating SSH key lifecycle...[/yellow]")

        auto_fix = ctx.yes or Confirm.ask(
            "Set up SSH key lifecycle (generate, auth, sign)?", default=True
        )
        signing_results = setup_signing(auto_fix=auto_fix, interactive=False)
        for r in signing_results:
            if r.skipped:
                console.print(f"[yellow]⚠[/yellow] {r.message}")
            elif r.success:
                console.print(f"[green]✓[/green] {r.message}")
            else:
                console.print(f"[red]✗[/red] {r.message}")

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.signing import setup_signing

        console.print("[bold cyan]SSH Key Lifecycle[/bold cyan]\n")

        signing_results = setup_signing(auto_fix=False, interactive=False)
        for r in signing_results:
            if r.success:
                console.print(f"  [green]✓[/green] {r.message}")
            else:
                console.print(f"  [yellow]⚠[/yellow] {r.message}")

        console.print()

    def diff(self, ctx: Context) -> bool:
        plan = self.plan(ctx)
        self.display_plan(plan)
        return plan.has_changes
