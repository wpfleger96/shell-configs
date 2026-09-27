"""Install command — parallel plan/apply flow over INSTALL_COMPONENTS."""

from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

import click

from shell_configs.cli.helpers import (
    build_context,
    run_components_parallel,
)
from shell_configs.cli.options import profile_option, shells_option, yes_option

if TYPE_CHECKING:
    from shell_configs.cli.context import Component, Context


def run_install(ctx: Context, components: list[Component]) -> bool:
    """Plan, confirm, and apply *components*.

    Returns False when any component failed to apply (failures are reported as
    they happen); True on success, no-op, dry run, or when the user declines.
    """
    from shell_configs.display import print_error, print_info, print_warning

    plans = run_components_parallel(components, "plan", ctx)

    has_changes = False
    for component in components:
        plan = plans[component]
        if plan.has_changes:
            has_changes = True
            component.display_plan(plan)

    if not has_changes and not ctx.force:
        print_info("Everything is already in sync")
        return True

    if not has_changes and ctx.force:
        print_info("Force mode: re-applying all components")

    if not ctx.yes and not ctx.dry_run:
        if not click.confirm("Apply all changes?"):
            return True

    if ctx.dry_run:
        return True

    to_apply = [c for c in components if plans[c].has_changes or ctx.force]

    if any(comp.needs_sudo(ctx, plans[comp]) for comp in to_apply):
        from shell_configs.packages import ensure_sudo_auth

        ok, msg = ensure_sudo_auth()
        if not ok:
            print_warning(f"{msg} — installs requiring sudo will fail fast")

    failed = False

    def _apply_sequential(stage: str) -> None:
        nonlocal failed
        for comp in to_apply:
            if comp.apply_stage != stage:
                continue
            try:
                ok = comp.apply(ctx, plans[comp])
            except Exception as e:
                print_error(f"{comp.display_name}: {type(e).__name__}: {e}")
                ok = False
            if not ok:
                failed = True

    # Pre-stage components install tools the rest depend on.
    _apply_sequential("pre")

    parallel_plans = {c: plans[c] for c in to_apply if c.apply_stage == "parallel"}
    if parallel_plans:
        results = run_components_parallel(
            list(parallel_plans), "apply", ctx, plans=parallel_plans
        )
        # Components that raised are absent from results; their errors were
        # already printed by run_components_parallel.
        if not all(results.get(c) for c in parallel_plans):
            failed = True

    # gh auth state is mutated by these components; run sequentially to avoid races
    _apply_sequential("post")

    return not failed


@click.command()
@shells_option("Comma-separated list of shells to install (e.g., bash,zsh,git)")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it"
)
@yes_option
@click.option(
    "--force", is_flag=True, help="Force apply all components even if already in sync"
)
@click.option(
    "--config-dir",
    type=click.Path(exists=True, path_type=Path),
    hidden=True,
    help="Override config directory path (for setup command)",
)
@profile_option
def install(
    shells: list[str] | None,
    dry_run: bool,
    yes: bool,
    force: bool,
    config_dir: Path | None,
    profile_name: str | None,
) -> None:
    """Install or update managed configuration sections."""
    from shell_configs.cli.components import INSTALL_COMPONENTS
    from shell_configs.display import print_warning

    ctx = build_context(
        profile_name,
        shells,
        config_dir=config_dir,
        dry_run=dry_run,
        yes=yes,
        force=force,
    )
    if ctx is None:
        print_warning("No shells to install")
        return

    if not run_install(ctx, INSTALL_COMPONENTS):
        print_warning("Install completed with errors")
        sys.exit(1)
