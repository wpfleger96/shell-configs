"""Diff command — parallel plan, sequential display."""

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
    help="Comma-separated list of shells to diff",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def diff(shells: list[str] | None, profile_name: str | None) -> None:
    """Show differences between repository and installed configurations."""
    from shell_configs.cli.components import DIFF_COMPONENTS
    from shell_configs.display import print_info, print_warning

    ctx = build_context(profile_name, shells)
    if ctx is None:
        print_warning("No shell configurations found")
        return

    plans = run_components_parallel(DIFF_COMPONENTS, "plan", ctx)

    found_diffs = False
    for component in DIFF_COMPONENTS:
        plan = plans[component]
        if plan.has_changes:
            found_diffs = True
            component.display_plan(plan)

    if not found_diffs:
        print_info("All configurations are in sync")
