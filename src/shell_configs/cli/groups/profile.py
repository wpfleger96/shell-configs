"""Profile subcommand group."""

from __future__ import annotations

import click

from shell_configs.config import ConfigReader


@click.group()
def profile() -> None:
    """Manage configuration profiles."""
    pass


@profile.command(name="list")
def profile_list() -> None:
    """List all available profiles."""
    from rich.table import Table

    from shell_configs.bootstrap.config import load_auto_update_config
    from shell_configs.display import console
    from shell_configs.profiles import ProfileLoader

    config_reader = ConfigReader()
    loader = ProfileLoader(config_reader.config_dir)
    auto_config = load_auto_update_config()
    active_name = auto_config.active_profile or "default"

    table = Table(show_header=True)
    table.add_column("Profile")
    table.add_column("Description")
    table.add_column("Extends")

    for name in loader.list_profiles():
        try:
            p = loader.load_profile(name)
            active_marker = " [green]*[/green]" if name == active_name else ""
            table.add_row(
                f"{p.name}{active_marker}",
                p.description or "[dim]-[/dim]",
                p.extends or "[dim]-[/dim]",
            )
        except Exception as e:
            table.add_row(name, f"[red]Error: {e}[/red]", "[dim]-[/dim]")

    console.print(table)
    console.print("\n[dim]* = active profile[/dim]")


@profile.command(name="show")
@click.argument("name")
@click.option("--resolved", is_flag=True, help="Show fully inherited result")
def profile_show(name: str, resolved: bool) -> None:
    """Show profile YAML. Use --resolved to see fully inherited values."""
    import yaml

    from shell_configs.display import console
    from shell_configs.profiles import ProfileLoader

    config_reader = ConfigReader()
    loader = ProfileLoader(config_reader.config_dir)

    try:
        if resolved:
            p = loader.resolve_profile(name)
            import dataclasses

            data = dataclasses.asdict(p)
        else:
            profile_path = loader.get_profile_path(name)
            if profile_path is None:
                if name == "default":
                    console.print(
                        "name: default\ndescription: Default profile (no overrides)"
                    )
                    return
                console.print(f"[red]Error:[/red] Profile '{name}' not found")
                return
            data = yaml.safe_load(profile_path.read_text()) or {}

        console.print(
            yaml.dump(data, default_flow_style=False, sort_keys=False).rstrip()
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@profile.command(name="current")
def profile_current() -> None:
    """Show the currently active profile."""
    from shell_configs.bootstrap.config import load_auto_update_config
    from shell_configs.display import console
    from shell_configs.profiles import ProfileLoader

    config_reader = ConfigReader()
    loader = ProfileLoader(config_reader.config_dir)
    auto_config = load_auto_update_config()
    active_name = auto_config.active_profile or "default"

    try:
        p = loader.load_profile(active_name)
        console.print(f"[bold]{p.name}[/bold]")
        if p.description:
            console.print(f"[dim]{p.description}[/dim]")
        if p.extends:
            console.print(f"[dim]Extends: {p.extends}[/dim]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@profile.command(name="switch")
@click.argument("name")
def profile_switch(name: str) -> None:
    """Switch the active profile."""
    from shell_configs.bootstrap.config import (
        load_auto_update_config,
        save_auto_update_config,
    )
    from shell_configs.display import console
    from shell_configs.profiles import ProfileLoader

    config_reader = ConfigReader()
    loader = ProfileLoader(config_reader.config_dir)

    try:
        loader.load_profile(name)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return

    auto_config = load_auto_update_config()
    save_auto_update_config(
        auto_config.__class__(
            backup_retention=auto_config.backup_retention,
            active_profile=name,
        )
    )
    console.print(f"[green]✓[/green] Switched to profile '{name}'")
    console.print("[dim]Run 'shell-configs install' to apply.[/dim]")
