"""Command-line interface for shell-configs."""

from __future__ import annotations

import logging

import click

from shell_configs import __version__

logger = logging.getLogger(__name__)


def version_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Custom version callback that also checks for updates."""
    if not value or ctx.resilient_parsing:
        return

    from shell_configs.display import console, print_hint

    console.print(f"shell-configs, version {__version__}")

    try:
        from shell_configs.bootstrap import check_tool_updates, get_tool_by_id

        tool = get_tool_by_id("shell-configs")
        if tool:
            update_info = check_tool_updates(tool, timeout=3)
            if update_info and update_info.has_update:
                console.print(
                    f"\n[cyan]Update available:[/cyan] {update_info.current_version} → {update_info.latest_version}"
                )
                print_hint("Run 'shell-configs upgrade' to install")
    except Exception as e:
        logger.debug(f"Failed to check for updates in version callback: {e}")

    ctx.exit()


@click.group()
@click.option(
    "--version",
    is_flag=True,
    callback=version_callback,
    expose_value=False,
    is_eager=True,
    help="Show version and check for updates",
)
def cli() -> None:
    """Manage shell configuration files across machines."""
    pass


from shell_configs.cli.commands.cleanup import cleanup
from shell_configs.cli.commands.diff import diff
from shell_configs.cli.commands.info import info
from shell_configs.cli.commands.install import install
from shell_configs.cli.commands.list_shells import list_shells
from shell_configs.cli.commands.setup import setup
from shell_configs.cli.commands.signing import signing
from shell_configs.cli.commands.status import status
from shell_configs.cli.commands.uninstall import uninstall
from shell_configs.cli.commands.upgrade import upgrade
from shell_configs.cli.commands.validate import validate
from shell_configs.cli.groups.completions import completions
from shell_configs.cli.groups.extensions import extensions
from shell_configs.cli.groups.packages import packages
from shell_configs.cli.groups.profile import profile
from shell_configs.cli.groups.scripts import scripts

cli.add_command(install)
cli.add_command(uninstall)
cli.add_command(status)
cli.add_command(diff)
cli.add_command(validate)
cli.add_command(list_shells)
cli.add_command(cleanup)
cli.add_command(upgrade)
cli.add_command(info)
cli.add_command(setup)
cli.add_command(signing)
cli.add_command(packages)
cli.add_command(profile)
cli.add_command(completions)
cli.add_command(scripts)
cli.add_command(extensions)


def main() -> None:
    """Entry point for the CLI."""
    cli()
