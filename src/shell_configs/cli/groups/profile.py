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
    from shell_configs.display import ICON_DASH, console, print_dim
    from shell_configs.profiles import ProfileLoader

    config_reader = ConfigReader()
    loader = ProfileLoader(config_reader.config_dir)
    auto_config = load_auto_update_config()
    active_name = auto_config.active_profile or "default"

    table = Table(show_header=True, header_style="bold")
    table.add_column("Profile")
    table.add_column("Description")
    table.add_column("Extends")

    for name in loader.list_profiles():
        try:
            p = loader.load_profile(name)
            active_marker = " [green]*[/green]" if name == active_name else ""
            table.add_row(
                f"{p.name}{active_marker}",
                p.description or ICON_DASH,
                p.extends or ICON_DASH,
            )
        except Exception as e:
            table.add_row(name, f"[red]Error: {e}[/red]", ICON_DASH)

    console.print(table)
    print_dim("* = active profile")


@profile.command(name="show")
@click.argument("name")
@click.option("--resolved", is_flag=True, help="Show fully inherited result")
def profile_show(name: str, resolved: bool) -> None:
    """Show profile YAML. Use --resolved to see fully inherited values."""
    import yaml

    from shell_configs.display import console, print_error
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
                print_error(f"Profile '{name}' not found")
                return
            data = yaml.safe_load(profile_path.read_text()) or {}

        console.print(
            yaml.dump(data, default_flow_style=False, sort_keys=False).rstrip()
        )
    except Exception as e:
        print_error(str(e))


@profile.command(name="current")
def profile_current() -> None:
    """Show the currently active profile."""
    from shell_configs.bootstrap.config import load_auto_update_config
    from shell_configs.display import console, print_dim, print_error, print_label
    from shell_configs.profiles import ProfileLoader

    config_reader = ConfigReader()
    loader = ProfileLoader(config_reader.config_dir)
    auto_config = load_auto_update_config()
    active_name = auto_config.active_profile or "default"

    try:
        p = loader.load_profile(active_name)
        console.print(f"[bold]{p.name}[/bold]")
        if p.description:
            print_dim(p.description)
        if p.extends:
            print_label("Extends", p.extends)
    except Exception as e:
        print_error(str(e))


@profile.command(name="switch")
@click.argument("name")
def profile_switch(name: str) -> None:
    """Switch the active profile."""
    from shell_configs.bootstrap.config import (
        load_auto_update_config,
        save_auto_update_config,
    )
    from shell_configs.display import print_error, print_hint, print_success
    from shell_configs.profiles import ProfileLoader

    config_reader = ConfigReader()
    loader = ProfileLoader(config_reader.config_dir)

    try:
        loader.load_profile(name)
    except Exception as e:
        print_error(str(e))
        return

    auto_config = load_auto_update_config()
    save_auto_update_config(
        auto_config.__class__(
            backup_retention=auto_config.backup_retention,
            active_profile=name,
        )
    )
    print_success(f"Switched to profile '{name}'")
    print_hint("Run 'shell-configs install' to apply.")
