"""Extensions subcommand group."""

from __future__ import annotations

import sys

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
        console.print("[yellow]No IDEs with extension management found[/yellow]")
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
        cli_cmd = shell.get_extension_cli()
        if cli_cmd is None:
            continue

        desired = ext_manager.load_desired_extensions(
            shell.name, shell.get_extension_list_paths(), profile=active_profile
        )
        installed = ext_manager.get_installed_extensions(cli_cmd)
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
    from shell_configs.display import console, print_info
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
        console.print("[yellow]No IDEs with extension management found[/yellow]")
        return

    found_diffs = False
    for shell in ide_shells:
        cli_cmd = shell.get_extension_cli()
        if cli_cmd is None:
            continue

        desired = ext_manager.load_desired_extensions(
            shell.name, shell.get_extension_list_paths(), profile=active_profile
        )
        installed = ext_manager.get_installed_extensions(cli_cmd)
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
                console.print(f"    [yellow]✗[/yellow] {ext_id}")

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
    from shell_configs.display import console, print_info
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
        console.print("[yellow]No IDEs with extension management found[/yellow]")
        return

    any_activity = False
    for shell in ide_shells:
        cli_cmd = shell.get_extension_cli()
        if cli_cmd is None:
            continue

        desired = ext_manager.load_desired_extensions(
            shell.name, shell.get_extension_list_paths(), profile=active_profile
        )
        installed = ext_manager.get_installed_extensions(cli_cmd)
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
                    cli_cmd, set(to_install), dry_run=dry_run
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
                    cli_cmd, set(to_uninstall), dry_run=dry_run
                )
                for r in results:
                    _print_extension_result(console, r)

    if not any_activity:
        print_info("All IDE extensions are already in sync")

    if dry_run and any_activity:
        print_info("\nDry run complete. Use without --dry-run to apply changes.")


@extensions.command(name="export")
@click.option(
    "--shell",
    "shell_name",
    required=True,
    help="IDE to export from (e.g., vscode, cursor)",
)
def extensions_export(shell_name: str) -> None:
    """Export currently installed extensions for an IDE."""
    from shell_configs.display import console, print_error
    from shell_configs.extensions import ExtensionManager
    from shell_configs.shells.registry import ShellRegistry

    registry = ShellRegistry()
    ext_manager = ExtensionManager()

    shells, invalid = registry.filter_by_names([shell_name])
    if invalid or not shells:
        print_error(f"Unknown shell: {shell_name}")
        console.print(f"[dim]Available: {', '.join(registry.get_names())}[/dim]")
        sys.exit(1)

    shell = shells[0]
    cli_cmd = shell.get_extension_cli()
    if cli_cmd is None:
        print_error(f"{shell.display_name} does not support extension management")
        sys.exit(1)

    output = ext_manager.export_extensions(cli_cmd, shell_name=shell.name)
    if output is None:
        print_error(f"Failed to query {shell.display_name} extensions")
        sys.exit(1)
    elif output:
        console.print(output)
    else:
        console.print("[dim]No extensions installed[/dim]")
