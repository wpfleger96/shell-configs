"""GhExtensionsComponent — gh CLI extension installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import Component, Context


class GhExtensionsComponent(Component):
    label = "gh-extensions"

    def install(self, ctx: Context) -> bool:
        from shell_configs.display import console
        from shell_configs.gh_extensions import (
            install_extension,
            list_installed,
            load_extensions,
        )

        console.print()
        console.print("[yellow]Installing gh CLI extensions...[/yellow]")
        desired = load_extensions()
        installed = list_installed()
        missing = [ext for ext in desired if ext.repo not in installed]

        if not missing:
            console.print("[green]✓[/green] All gh extensions already installed")
            return True

        all_ok = True
        for ext in missing:
            success, msg = install_extension(ext.repo, pin=ext.pin, dry_run=ctx.dry_run)
            if ctx.dry_run:
                console.print(f"[dim]→[/dim] {msg}")
            elif success:
                console.print(f"[green]✓[/green] {msg}")
            else:
                console.print(f"[red]✗[/red] {msg}")
                all_ok = False
        return all_ok

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.gh_extensions import list_installed, load_extensions

        console.print("[bold cyan]gh CLI Extensions[/bold cyan]\n")
        desired = load_extensions()
        installed = list_installed()
        missing = [ext for ext in desired if ext.repo not in installed]
        extra = set(installed.keys()) - {ext.repo for ext in desired}

        if not missing and not extra:
            console.print(
                f"  [green]✓[/green] {len(desired)}/{len(desired)} extensions installed"
            )
        else:
            parts = []
            if missing:
                parts.append(f"{len(missing)} missing")
            if extra:
                parts.append(f"{len(extra)} unmanaged")
            console.print(
                f"  [yellow]⚠[/yellow] {len(desired) - len(missing)}/{len(desired)} extensions installed "
                f"({', '.join(parts)})"
            )

        console.print()

    def diff(self, ctx: Context) -> bool:
        from shell_configs.display import console
        from shell_configs.gh_extensions import list_installed, load_extensions

        desired = load_extensions()
        installed = list_installed()
        missing = [ext for ext in desired if ext.repo not in installed]
        extra = set(installed.keys()) - {ext.repo for ext in desired}

        if not missing and not extra:
            return False

        console.print("\n[bold cyan]gh CLI Extensions[/bold cyan]\n")
        for ext in missing:
            console.print(f"  [yellow]✗[/yellow] {ext.repo} (not installed)")
        for ext_name in sorted(extra):
            console.print(f"  [dim]+[/dim] {ext_name} (not in manifest)")
        return True
