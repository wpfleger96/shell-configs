"""List shells command — shows all available shell configurations."""

from __future__ import annotations

import click

from shell_configs.config import ConfigReader


@click.command("list-shells")
def list_shells() -> None:
    """List all available shell configurations."""
    from shell_configs.display import console, print_warning
    from shell_configs.shells.registry import ShellRegistry

    config_reader = ConfigReader()
    registry = ShellRegistry()
    all_shells = registry.get_all()
    available = config_reader.get_available_shells()

    console.print("[bold cyan]Available Shells:[/bold cyan]")
    for shell in all_shells:
        has_config = shell.name in available
        status = "[green]✓[/green]" if has_config else "[dim]○[/dim]"
        console.print(f"  {status} {shell.display_name} ({shell.name})")

    if not available:
        print_warning(
            "No shell configurations found. Add config files to the config/ directory."
        )
