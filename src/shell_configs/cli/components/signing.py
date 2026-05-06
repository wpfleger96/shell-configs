"""SigningComponent — SSH key lifecycle setup and status."""

from __future__ import annotations

import sys

from shell_configs.cli.context import Component, Context


class SigningComponent(Component):
    label = "signing"

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        from rich.prompt import Confirm

        from shell_configs.display import console
        from shell_configs.signing import setup_signing

        console.print()
        console.print("[yellow]Validating SSH key lifecycle...[/yellow]")
        interactive = sys.stdin.isatty()
        signing_results = setup_signing(
            auto_fix=ctx.yes
            or Confirm.ask(
                "Set up SSH key lifecycle (generate, auth, sign)?", default=True
            ),
            interactive=interactive,
        )
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
        from shell_configs.display import console
        from shell_configs.signing import setup_signing

        signing_results = setup_signing(auto_fix=False, interactive=False)
        failed = [r for r in signing_results if not r.success and not r.skipped]

        if not failed:
            return False

        console.print("\n[bold cyan]SSH Key Lifecycle[/bold cyan]\n")
        for r in failed:
            console.print(f"  [yellow]⚠[/yellow] {r.message}")
        return True
