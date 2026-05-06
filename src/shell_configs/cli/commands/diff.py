"""Diff command — loops over COMPONENTS calling diff()."""

from __future__ import annotations

import click

from shell_configs.cli.helpers import build_context, parse_shell_filter


@click.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to diff",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def diff(shells: list[str] | None, profile_name: str | None) -> None:
    """Show differences between repository and installed configurations."""
    from shell_configs.cli.components import COMPONENTS
    from shell_configs.display import print_info, print_warning

    ctx = build_context(profile_name, shells)
    if ctx is None:
        print_warning("No shell configurations found")
        return

    found_diffs = False
    for component in COMPONENTS:
        if component.diff(ctx):
            found_diffs = True

    if not found_diffs:
        print_info("All configurations are in sync")
