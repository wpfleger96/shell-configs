"""Cleanup command — removes old backup files."""

from __future__ import annotations

from pathlib import Path

import click


@click.command()
@click.option(
    "--dry-run", is_flag=True, help="Show what would be deleted without deleting"
)
@click.option("--keep", type=int, help="Number of backups to keep per config file")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def cleanup(dry_run: bool, keep: int | None, yes: bool) -> None:
    """Clean up old backup files created by shell-configs."""
    from collections import defaultdict

    from rich.table import Table

    from shell_configs.bootstrap import load_auto_update_config
    from shell_configs.display import console, print_info
    from shell_configs.manager import ConfigManager
    from shell_configs.shells.registry import ShellRegistry

    config = load_auto_update_config()
    retention = keep if keep is not None else config.backup_retention

    manager = ConfigManager(backup_retention=config.backup_retention)
    registry = ShellRegistry()
    all_shells = registry.get_all()

    console.print("[bold cyan]Scanning for shell-configs backup files...[/bold cyan]\n")

    backup_by_config: dict[Path, list[Path]] = defaultdict(list)
    backup_dir_map: dict[Path, Path] = {}

    for shell in all_shells:
        for config_file in shell.get_config_files():
            if config_file.path.exists():
                backups = manager.find_backup_files(config_file.path)
                if backups:
                    backup_by_config[config_file.path].extend(backups)

        for additional_file in shell.get_additional_files():
            should_scan = (
                additional_file.target_path.exists() or additional_file.backup_dir
            )
            if should_scan:
                backups = manager.find_backup_files(
                    additional_file.target_path,
                    backup_dir=additional_file.backup_dir,
                )
                if backups:
                    backup_by_config[additional_file.target_path].extend(backups)
                    if additional_file.backup_dir:
                        backup_dir_map[additional_file.target_path] = (
                            additional_file.backup_dir
                        )

    if not backup_by_config:
        print_info("No backup files found")
        return

    total_backups = sum(len(backups) for backups in backup_by_config.values())
    to_keep_count = 0
    to_remove_count = 0

    table = Table(show_header=True, header_style="bold")
    table.add_column("Config File", style="cyan")
    table.add_column("Backup File", style="white")
    table.add_column("Action", style="white")

    home = str(Path.home())

    for config_path in sorted(backup_by_config.keys()):
        backups = sorted(backup_by_config[config_path], reverse=True)
        config_display = str(config_path).replace(home, "~")

        for i, backup in enumerate(backups):
            action = "keep" if i < retention else "remove"
            if action == "keep":
                to_keep_count += 1
                action_display = "[green]keep[/green]"
            else:
                to_remove_count += 1
                action_display = "[yellow]remove[/yellow]"

            backup_display = backup.name
            table.add_row(
                config_display if i == 0 else "", backup_display, action_display
            )

    console.print(table)
    console.print()

    if to_remove_count == 0:
        print_info(
            f"All {total_backups} backup files are within retention ({retention})"
        )
        return

    console.print(
        f"Found {total_backups} backup files: "
        f"[green]{to_keep_count} to keep[/green], "
        f"[yellow]{to_remove_count} to remove[/yellow]"
    )
    console.print()

    if dry_run:
        print_info(f"Dry run: would remove {to_remove_count} backup files")
        return

    if not yes:
        if not click.confirm(
            f"Remove {to_remove_count} old backup files?", default=True
        ):
            print_info("Cleanup cancelled")
            return

    removed_count = 0
    for config_path in backup_by_config:
        removed = manager.cleanup_old_backups(
            config_path,
            keep=retention,
            backup_dir=backup_dir_map.get(config_path),
        )
        removed_count += len(removed)

    console.print(
        f"[green]✓[/green] Removed {removed_count} backup files "
        f"(kept {retention} most recent per config)"
    )
