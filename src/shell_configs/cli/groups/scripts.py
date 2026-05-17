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
    from shell_configs.display import (
        console,
        print_done,
        print_error,
        print_info,
        print_success,
        print_warning,
        print_would,
    )
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
            print_warning(message)
            collisions.append(entry.name)
        elif result == InstallResult.ALREADY_SYNCED:
            print_done(message)
        elif result in (InstallResult.INSTALLED, InstallResult.UPDATED):
            print_success(message)
        elif result in (InstallResult.WOULD_INSTALL, InstallResult.WOULD_UPDATE):
            print_would(message)
        elif result == InstallResult.SKIPPED_PLATFORM:
            pass
        else:
            print_error(message)

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
    from shell_configs.display import (
        console,
        print_dim,
        print_error,
        print_info,
        print_success,
        print_unchanged,
        print_warning,
        print_would,
    )
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
        print_dim("No scripts installed by shell-configs")
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
            print_success(message)
        elif result == UninstallResult.WOULD_REMOVE:
            print_would(message)
        elif result == UninstallResult.MODIFIED:
            print_warning(message)
        elif result == UninstallResult.NOT_FOUND:
            print_unchanged(message)
        else:
            print_error(message)


@scripts.command(name="status")
def scripts_status() -> None:
    """Show installation status of managed scripts."""
    from rich.table import Table

    from shell_configs.display import (
        ICON_ERROR,
        ICON_SKIPPED,
        ICON_SUCCESS,
        ICON_WARNING,
        console,
        print_dim,
        print_section,
    )
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
        ScriptStatus.INSTALLED: ICON_SUCCESS,
        ScriptStatus.OUTDATED: "[yellow]↑[/yellow]",
        ScriptStatus.MODIFIED: "[yellow]✎[/yellow]",
        ScriptStatus.MISSING: ICON_ERROR,
        ScriptStatus.COLLISION: ICON_WARNING,
        ScriptStatus.SKIPPED_PLATFORM: ICON_SKIPPED,
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

    print_section("Script Status")
    console.print(table)
    console.print()
    print_dim(f"Target directory: {target_dir}")


@scripts.command(name="list")
@click.option(
    "--all", "include_all", is_flag=True, help="Show scripts for all platforms"
)
def scripts_list(include_all: bool) -> None:
    """List available scripts."""
    from rich.table import Table

    from shell_configs.display import console, print_dim, print_section
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

    print_section("Available Scripts")
    console.print(table)
    if not include_all:
        console.print()
        print_dim(f"Showing scripts for {current.display_name}. Use --all to see all.")
