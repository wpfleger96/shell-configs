"""Scripts subcommand group."""

from __future__ import annotations

import click


@click.group()
def scripts() -> None:
    """Manage utility scripts distributed by shell-configs."""
    pass


@scripts.command(name="install")
@click.option("--dry-run", is_flag=True, help="Show what would be installed")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def scripts_install(dry_run: bool, yes: bool) -> None:
    """Install utility scripts to ~/.local/bin."""
    from shell_configs.display import console, print_info, print_warning
    from shell_configs.script_manager import (
        InstallResult,
        ScriptManifest,
        discover_scripts,
        get_default_manifest_path,
        get_default_target_dir,
        install_script,
    )

    target_dir = get_default_target_dir()
    manifest = ScriptManifest(get_default_manifest_path())
    entries = discover_scripts()

    if not entries:
        print_warning("No scripts available for this platform")
        return

    if not dry_run and not yes:
        console.print(
            f"[bold]Will install {len(entries)} script(s) to {target_dir}[/bold]\n"
        )
        for entry in entries:
            console.print(f"  {entry.name}")
        console.print()
        if not click.confirm("Proceed?", default=True):
            print_info("Cancelled")
            return

    collisions = []
    for entry in entries:
        result, message = install_script(entry, target_dir, manifest, dry_run=dry_run)
        if result == InstallResult.COLLISION:
            console.print(f"[yellow]⚠[/yellow] {message}")
            collisions.append(entry.name)
        elif result == InstallResult.ALREADY_SYNCED:
            console.print(f"[green]✓[/green] {message}")
        elif result in (InstallResult.INSTALLED, InstallResult.UPDATED):
            console.print(f"[green]✓[/green] {message}")
        elif result in (InstallResult.WOULD_INSTALL, InstallResult.WOULD_UPDATE):
            console.print(f"[dim]→[/dim] {message}")
        elif result == InstallResult.SKIPPED_PLATFORM:
            pass
        else:
            console.print(f"[red]✗[/red] {message}")

    if collisions:
        print_warning(
            f"{len(collisions)} collision(s) skipped. "
            "Remove the existing file(s) first, then re-run install."
        )


@scripts.command(name="uninstall")
@click.option("--dry-run", is_flag=True, help="Show what would be removed")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option("--force", is_flag=True, help="Remove even user-modified scripts")
def scripts_uninstall(dry_run: bool, yes: bool, force: bool) -> None:
    """Remove shell-configs-managed scripts from ~/.local/bin."""
    from shell_configs.display import console, print_info
    from shell_configs.script_manager import (
        ScriptManifest,
        UninstallResult,
        get_default_manifest_path,
        get_default_target_dir,
        uninstall_script,
    )

    manifest = ScriptManifest(get_default_manifest_path())
    target_dir = get_default_target_dir()

    if not manifest.scripts:
        console.print("[dim]No scripts installed by shell-configs[/dim]")
        return

    names = list(manifest.scripts.keys())

    if not dry_run and not yes:
        console.print(
            f"[bold]Will uninstall {len(names)} script(s) from {target_dir}[/bold]\n"
        )
        for name in names:
            console.print(f"  {name}")
        console.print()
        if not click.confirm("Proceed?", default=True):
            print_info("Cancelled")
            return

    for name in names:
        result, message = uninstall_script(
            name, target_dir, manifest, force=force, dry_run=dry_run
        )
        if result == UninstallResult.REMOVED:
            console.print(f"[green]✓[/green] {message}")
        elif result == UninstallResult.WOULD_REMOVE:
            console.print(f"[dim]→[/dim] {message}")
        elif result == UninstallResult.MODIFIED:
            console.print(f"[yellow]⚠[/yellow] {message}")
        elif result == UninstallResult.NOT_FOUND:
            console.print(f"[dim]-[/dim] {message}")
        else:
            console.print(f"[red]✗[/red] {message}")


@scripts.command(name="status")
def scripts_status() -> None:
    """Show installation status of managed scripts."""
    from rich.table import Table

    from shell_configs.display import console
    from shell_configs.script_manager import (
        ScriptManifest,
        ScriptStatus,
        discover_scripts,
        get_default_manifest_path,
        get_default_target_dir,
        get_script_status,
    )

    target_dir = get_default_target_dir()
    manifest = ScriptManifest(get_default_manifest_path())

    table = Table(show_header=True, header_style="bold")
    table.add_column("Script")
    table.add_column("Status")

    status_icons = {
        ScriptStatus.INSTALLED: "[green]✓[/green]",
        ScriptStatus.OUTDATED: "[yellow]↑[/yellow]",
        ScriptStatus.MODIFIED: "[yellow]✎[/yellow]",
        ScriptStatus.MISSING: "[red]✗[/red]",
        ScriptStatus.COLLISION: "[yellow]⚠[/yellow]",
        ScriptStatus.SKIPPED_PLATFORM: "[dim]-[/dim]",
    }

    for entry in discover_scripts(include_all=True):
        status = get_script_status(entry, target_dir, manifest)
        icon = status_icons.get(status, "?")
        label = status.value
        if status == ScriptStatus.COLLISION:
            label = "exists (not ours)"
        elif status == ScriptStatus.SKIPPED_PLATFORM:
            label = "other platform"
        table.add_row(entry.name, f"{icon} {label}")

    console.print("[bold cyan]Script Status[/bold cyan]\n")
    console.print(table)
    console.print(f"\n[dim]Target directory: {target_dir}[/dim]")


@scripts.command(name="list")
@click.option(
    "--all", "include_all", is_flag=True, help="Show scripts for all platforms"
)
def scripts_list(include_all: bool) -> None:
    """List available scripts."""
    from rich.table import Table

    from shell_configs.display import console
    from shell_configs.platform import detect_platform
    from shell_configs.script_manager import discover_scripts

    current = detect_platform()
    entries = discover_scripts(include_all=include_all)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Script")
    table.add_column("Platforms")

    for entry in entries:
        platforms = ", ".join(
            p.display_name for p in sorted(entry.platforms, key=lambda p: p.value)
        )
        table.add_row(entry.name, platforms)

    console.print("[bold cyan]Available Scripts[/bold cyan]\n")
    console.print(table)
    if not include_all:
        console.print(
            f"\n[dim]Showing scripts for {current.display_name}. Use --all to see all.[/dim]"
        )
