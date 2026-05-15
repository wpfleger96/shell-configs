"""Status command — parallel status across STATUS_COMPONENTS."""

from __future__ import annotations

import click

from shell_configs.cli.helpers import (
    build_context,
    parse_shell_filter,
    run_components_parallel,
)


@click.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to check",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def status(shells: list[str] | None, profile_name: str | None) -> None:
    """Show the status of managed configurations."""
    from shell_configs.cli.components import STATUS_COMPONENTS
    from shell_configs.display import console, print_warning
    from shell_configs.platform import detect_platform

    ctx = build_context(profile_name, shells)
    if ctx is None:
        print_warning("No shell configurations found")
        return

    console.print(f"[bold]Platform:[/bold] {detect_platform().display_name}\n")

    run_components_parallel(STATUS_COMPONENTS, "status", ctx)

    console.print()
