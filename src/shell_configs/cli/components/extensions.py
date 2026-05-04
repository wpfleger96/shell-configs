"""ExtensionsComponent — IDE extension installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import Component, Context


class ExtensionsComponent(Component):
    label = "extensions"

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        from shell_configs.cli.helpers import (
            _get_extension_shells,
            _print_extension_result,
            _print_ignored_builtin_extensions,
        )
        from shell_configs.display import console
        from shell_configs.extensions import ExtensionManager

        ext_manager = ExtensionManager()
        ide_shells = _get_extension_shells(ctx.registry)
        if not ide_shells:
            return True

        any_ext_activity = False
        for shell in ide_shells:
            cli_cmd = shell.get_extension_cli()
            if cli_cmd is None:
                continue

            desired = ext_manager.load_desired_extensions(
                shell.name,
                shell.get_extension_list_paths(),
                profile=ctx.profile,
            )
            installed = ext_manager.get_installed_extensions(cli_cmd)
            diff = ext_manager.compute_diff(desired, installed, shell_name=shell.name)
            printed_header = False

            if diff.ignored:
                if not any_ext_activity:
                    console.print()
                    console.print("[yellow]Installing IDE extensions...[/yellow]")
                any_ext_activity = True
                console.print(f"  [bold cyan]{shell.display_name}[/bold cyan]")
                printed_header = _print_ignored_builtin_extensions(
                    console,
                    shell.display_name,
                    diff.ignored,
                    header_printed=True,
                )

            if not diff.missing:
                continue

            if not any_ext_activity:
                console.print()
                console.print("[yellow]Installing IDE extensions...[/yellow]")
            any_ext_activity = True

            if not printed_header:
                console.print(
                    f"  [bold cyan]{shell.display_name}[/bold cyan]: "
                    f"{len(diff.missing)} missing"
                )
            else:
                console.print(
                    f"  [yellow]Installing {len(diff.missing)} missing extension(s)...[/yellow]"
                )
            ext_results = ext_manager.install_extensions(
                cli_cmd, set(diff.missing), dry_run=ctx.dry_run
            )
            for ext_r in ext_results:
                _print_extension_result(console, ext_r)

        if not any_ext_activity:
            console.print()
            console.print("[green]✓[/green] All IDE extensions already in sync")

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.cli.helpers import _get_extension_shells
        from shell_configs.display import console
        from shell_configs.extensions import ExtensionManager

        console.print("[bold cyan]Extensions[/bold cyan]\n")

        ext_manager = ExtensionManager()
        ide_shells = _get_extension_shells(ctx.registry)
        for shell in ide_shells:
            cli_cmd = shell.get_extension_cli()
            if cli_cmd is None:
                continue

            ext_desired = ext_manager.load_desired_extensions(
                shell.name, shell.get_extension_list_paths(), profile=ctx.profile
            )
            ext_installed = ext_manager.get_installed_extensions(cli_cmd)
            ext_diff = ext_manager.compute_diff(
                ext_desired, ext_installed, shell_name=shell.name
            )

            if not ext_diff.missing and not ext_diff.extra:
                console.print(
                    f"  [green]✓[/green] {shell.display_name}: "
                    f"{len(ext_diff.matched)}/{len(ext_desired)} extensions synced"
                )
            else:
                parts = []
                if ext_diff.missing:
                    parts.append(f"{len(ext_diff.missing)} missing")
                if ext_diff.extra:
                    parts.append(f"{len(ext_diff.extra)} extra")
                console.print(
                    f"  [yellow]⚠[/yellow] {shell.display_name}: "
                    f"{len(ext_diff.matched)}/{len(ext_desired)} synced ({', '.join(parts)})"
                )
                console.print(
                    "  [dim]Run 'shell-configs extensions diff' for details[/dim]"
                )

        console.print()

    def diff(self, ctx: Context) -> bool:
        from shell_configs.cli.helpers import _get_extension_shells
        from shell_configs.display import console
        from shell_configs.extensions import ExtensionManager

        ext_manager = ExtensionManager()
        ide_shells = _get_extension_shells(ctx.registry)
        if not ide_shells:
            return False

        found_diffs = False
        for shell in ide_shells:
            cli_cmd = shell.get_extension_cli()
            if cli_cmd is None:
                continue

            desired = ext_manager.load_desired_extensions(
                shell.name, shell.get_extension_list_paths(), profile=ctx.profile
            )
            installed = ext_manager.get_installed_extensions(cli_cmd)
            diff = ext_manager.compute_diff(desired, installed, shell_name=shell.name)

            if not diff.missing and not diff.extra and not diff.ignored:
                continue

            if not found_diffs:
                console.print("\n[bold cyan]Extensions[/bold cyan]")
            found_diffs = True
            console.print(f"\n  [bold]{shell.display_name}[/bold]")

            if diff.ignored:
                console.print(
                    f"    [yellow]Ignored built-ins in config ({len(diff.ignored)}):[/yellow]"
                )
                for ext_id in sorted(diff.ignored):
                    console.print(f"      [yellow]![/yellow] {ext_id}")

            if diff.missing:
                console.print(f"    [yellow]Missing ({len(diff.missing)}):[/yellow]")
                for ext_id in sorted(diff.missing):
                    console.print(f"      [yellow]✗[/yellow] {ext_id}")

            if diff.extra:
                console.print(f"    [dim]Extra ({len(diff.extra)}):[/dim]")
                for ext_id in sorted(diff.extra):
                    console.print(f"      [dim]+[/dim] {ext_id}")

        return found_diffs
