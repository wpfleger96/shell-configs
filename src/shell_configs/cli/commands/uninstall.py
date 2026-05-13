"""Uninstall command — parallel component uninstall."""

from __future__ import annotations

import click

from shell_configs.cli.helpers import (
    _get_selected_shells,
    parse_shell_filter,
    run_components_parallel,
)


@click.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to uninstall",
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def uninstall(shells: list[str] | None, yes: bool) -> None:
    """Remove managed configuration sections."""
    from shell_configs.cli.components import COMPONENTS
    from shell_configs.cli.context import Context
    from shell_configs.config import ConfigReader
    from shell_configs.display import print_info, print_warning
    from shell_configs.shells.registry import ShellRegistry

    registry = ShellRegistry()
    config_reader = ConfigReader()

    # use_all=True so uninstall works even for shells without config files
    selected_shells = _get_selected_shells(registry, shells, use_all=True)

    if not selected_shells:
        print_warning("No shells to uninstall")
        return

    if not yes:
        shell_names = ", ".join([s.display_name for s in selected_shells])
        if not click.confirm(
            f"Remove managed sections from {shell_names} configurations?"
        ):
            print_info("Uninstallation cancelled")
            return

    ctx = Context(
        dry_run=False,
        yes=yes,
        profile_name=None,
        profile=None,
        selected_shells=selected_shells,
        config_reader=config_reader,
        registry=registry,
    )

    run_components_parallel(COMPONENTS, "uninstall", ctx)
