"""Extensions subcommand group."""

from __future__ import annotations

import click

from shell_configs.cli.helpers import (
    _get_extension_shells,
    _print_extension_result,
    _print_ignored_builtin_extensions,
    parse_shell_filter,
)
from shell_configs.config import ConfigReader


@click.group()
def extensions() -> None:
    """Manage IDE extensions for VSCode and Cursor."""
    pass


@extensions.command(name="status")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of IDEs (e.g., vscode,cursor)",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def extensions_status(shells: list[str] | None, profile_name: str | None) -> None:
    """Show extension sync status for each IDE."""
    from rich.table import Table

    from shell_configs.display import console
    from shell_configs.extensions import ExtensionManager
    from shell_configs.profiles import ProfileLoader, resolve_active_profile
    from shell_configs.shells.registry import ShellRegistry

    config_reader = ConfigReader()
    registry = ShellRegistry()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)
    ext_manager = ExtensionManager()

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        from shell_configs.display import print_warning

        print_warning("No IDEs with extension management found")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("IDE", style="cyan")
    table.add_column("Desired")
    table.add_column("Installed")
    table.add_column("Missing")
    table.add_column("Extra")
    table.add_column("Status")
    ignored_by_shell: list[tuple[str, frozenset[str]]] = []

    for shell in ide_shells:
        invoker = shell.get_extension_invoker()
        cli_cmd = shell.get_extension_cli()
        if invoker is None and cli_cmd is None:
            continue

        desired = ext_manager.load_desired_extensions(
            shell.name, shell.get_extension_list_paths(), profile=active_profile
        )
        installed = ext_manager.get_installed_extensions(cli_cmd, invoker=invoker)
        if installed is None:
            continue
        diff = ext_manager.compute_diff(desired, installed, shell_name=shell.name)
        if diff.ignored:
            ignored_by_shell.append((shell.display_name, diff.ignored))

        if diff.missing or diff.extra:
            status_str = "[yellow]⚠ out of sync[/yellow]"
        elif diff.ignored:
            status_str = "[yellow]⚠ built-ins ignored[/yellow]"
        else:
            status_str = "[green]✓ synced[/green]"

        table.add_row(
            shell.display_name,
            str(len(desired)),
            str(len(installed)),
            str(len(diff.missing)) if diff.missing else "[green]0[/green]",
            str(len(diff.extra)) if diff.extra else "[green]0[/green]",
            status_str,
        )

    console.print(table)
    for shell_display_name, ignored in ignored_by_shell:
        ignored_list = ", ".join(sorted(ignored))
        console.print(
            f"[yellow]! {shell_display_name}: ignoring built-in extensions from config: {ignored_list}[/yellow]"
        )


@extensions.command(name="diff")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of IDEs (e.g., vscode,cursor)",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def extensions_diff(shells: list[str] | None, profile_name: str | None) -> None:
    """Show differences between desired and installed extensions."""
    from shell_configs.display import console, print_error, print_info, print_warning
    from shell_configs.extensions import ExtensionManager
    from shell_configs.profiles import ProfileLoader, resolve_active_profile
    from shell_configs.shells.registry import ShellRegistry

    config_reader = ConfigReader()
    registry = ShellRegistry()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)
    ext_manager = ExtensionManager()

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        print_warning("No IDEs with extension management found")
        return

    found_diffs = False
    for shell in ide_shells:
        invoker = shell.get_extension_invoker()
        cli_cmd = shell.get_extension_cli()
        if invoker is None and cli_cmd is None:
            continue

        desired = ext_manager.load_desired_extensions(
            shell.name, shell.get_extension_list_paths(), profile=active_profile
        )
        installed = ext_manager.get_installed_extensions(cli_cmd, invoker=invoker)
        if installed is None:
            continue
        diff = ext_manager.compute_diff(desired, installed, shell_name=shell.name)

        if not diff.missing and not diff.extra and not diff.ignored:
            continue

        found_diffs = True
        console.print(f"\n[bold cyan]{shell.display_name}[/bold cyan]")

        if diff.ignored:
            console.print(
                f"  [yellow]Ignored built-ins in config ({len(diff.ignored)}):[/yellow]"
            )
            for ext_id in sorted(diff.ignored):
                console.print(f"    [yellow]![/yellow] {ext_id}")

        if diff.missing:
            console.print(f"  [yellow]Missing ({len(diff.missing)}):[/yellow]")
            for ext_id in sorted(diff.missing):
                print_error(ext_id, indent=4)

        if diff.extra:
            console.print(f"  [dim]Extra ({len(diff.extra)}):[/dim]")
            for ext_id in sorted(diff.extra):
                console.print(f"    [dim]+[/dim] {ext_id}")

    if not found_diffs:
        print_info("All IDE extensions are in sync")


@extensions.command(name="install")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of IDEs (e.g., vscode,cursor)",
)
@click.option(
    "--prune", is_flag=True, help="Uninstall extensions not in the desired list"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it"
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def extensions_install(
    shells: list[str] | None,
    prune: bool,
    dry_run: bool,
    yes: bool,
    profile_name: str | None,
) -> None:
    """Install (and optionally prune) extensions for each IDE."""
    from shell_configs.display import console, print_hint, print_info, print_warning
    from shell_configs.extensions import ExtensionManager
    from shell_configs.profiles import ProfileLoader, resolve_active_profile
    from shell_configs.shells.registry import ShellRegistry

    config_reader = ConfigReader()
    registry = ShellRegistry()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)
    ext_manager = ExtensionManager()

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        print_warning("No IDEs with extension management found")
        return

    any_activity = False
    for shell in ide_shells:
        invoker = shell.get_extension_invoker()
        cli_cmd = shell.get_extension_cli()
        if invoker is None and cli_cmd is None:
            continue

        desired = ext_manager.load_desired_extensions(
            shell.name, shell.get_extension_list_paths(), profile=active_profile
        )
        installed = ext_manager.get_installed_extensions(cli_cmd, invoker=invoker)
        if installed is None:
            continue
        diff = ext_manager.compute_diff(desired, installed, shell_name=shell.name)

        to_install = diff.missing
        to_uninstall = diff.extra if prune else frozenset()
        printed_header = False

        if diff.ignored:
            any_activity = True
            printed_header = _print_ignored_builtin_extensions(
                console,
                shell.display_name,
                diff.ignored,
                header_printed=printed_header,
            )

        if not to_install and not to_uninstall:
            continue

        any_activity = True
        if not printed_header:
            console.print(f"\n[bold cyan]{shell.display_name}[/bold cyan]")
            printed_header = True

        if to_install:
            console.print(
                f"  [yellow]Installing {len(to_install)} extension(s)...[/yellow]"
            )
            if not dry_run and not yes:
                if not click.confirm("  Proceed?", default=True):
                    print_info(f"  Skipping {shell.display_name} installs")
                    to_install = frozenset()

            if to_install:
                results = ext_manager.install_extensions(
                    cli_cmd, set(to_install), dry_run=dry_run, invoker=invoker
                )
                for r in results:
                    _print_extension_result(console, r)

        if to_uninstall:
            console.print(
                f"  [yellow]Pruning {len(to_uninstall)} extra extension(s)...[/yellow]"
            )
            if not dry_run and not yes:
                if not click.confirm("  Proceed with pruning?", default=False):
                    print_info(f"  Skipping {shell.display_name} prune")
                    to_uninstall = frozenset()

            if to_uninstall:
                results = ext_manager.uninstall_extensions(
                    cli_cmd, set(to_uninstall), dry_run=dry_run, invoker=invoker
                )
                for r in results:
                    _print_extension_result(console, r)

    if not any_activity:
        print_info("All IDE extensions are already in sync")

    if dry_run and any_activity:
        print_hint("Use without --dry-run to apply changes.")


@extensions.command(name="list")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of IDEs (e.g., vscode,cursor)",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def extensions_list(shells: list[str] | None, profile_name: str | None) -> None:
    """List all extensions for each IDE with their install status."""
    from rich.table import Table

    from shell_configs.display import console, print_info, print_warning
    from shell_configs.extensions import ExtensionManager
    from shell_configs.profiles import ProfileLoader, resolve_active_profile
    from shell_configs.shells.registry import ShellRegistry

    config_reader = ConfigReader()
    registry = ShellRegistry()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)
    ext_manager = ExtensionManager()

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        print_warning("No IDEs with extension management found")
        return

    any_output = False
    for shell in ide_shells:
        invoker = shell.get_extension_invoker()
        cli_cmd = shell.get_extension_cli()
        if invoker is None and cli_cmd is None:
            continue

        desired = ext_manager.load_desired_extensions(
            shell.name, shell.get_extension_list_paths(), profile=active_profile
        )
        installed = ext_manager.get_installed_extensions(cli_cmd, invoker=invoker)
        if installed is None:
            continue
        diff = ext_manager.compute_diff(desired, installed, shell_name=shell.name)

        rows: list[tuple[str, str]] = []
        for ext_id in diff.matched:
            rows.append((ext_id, "[green]✓ installed[/green]"))
        for ext_id in diff.missing:
            rows.append((ext_id, "[red]✗ missing[/red]"))
        for ext_id in diff.extra:
            rows.append((ext_id, "[dim]+ extra[/dim]"))
        for ext_id in diff.ignored:
            rows.append((ext_id, "[dim]~ builtin[/dim]"))

        if not rows:
            continue

        any_output = True
        table = Table(
            title=shell.display_name,
            show_header=True,
            header_style="bold",
            title_style="bold cyan",
            title_justify="left",
        )
        table.add_column("Extension")
        table.add_column("Status")

        for ext_id, status in sorted(rows, key=lambda r: r[0]):
            table.add_row(ext_id, status)

        console.print(table)

    if not any_output:
        print_info("No extension data available")
