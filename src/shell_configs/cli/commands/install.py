"""Install command — parallel plan/apply flow over INSTALL_COMPONENTS."""

from __future__ import annotations

from pathlib import Path

import click

from shell_configs.cli.helpers import (
    build_context,
    run_components_parallel,
)
from shell_configs.cli.options import profile_option, shells_option, yes_option


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
    from shell_configs.display import print_info, print_warning

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

    plans = run_components_parallel(INSTALL_COMPONENTS, "plan", ctx)

    has_changes = False
    for component in INSTALL_COMPONENTS:
        plan = plans[component]
        if plan.has_changes:
            has_changes = True
            component.display_plan(plan)

    if not has_changes and not force:
        print_info("Everything is already in sync")
        return

    if not has_changes and force:
        print_info("Force mode: re-applying all components")

    if not ctx.yes and not ctx.dry_run:
        if not click.confirm("Apply all changes?"):
            return

    if ctx.dry_run:
        return

    if any(
        comp.needs_sudo(ctx, plans[comp])
        for comp in INSTALL_COMPONENTS
        if plans[comp].has_changes or force
    ):
        from shell_configs.packages import ensure_sudo_auth

        ok, msg = ensure_sudo_auth()
        if not ok:
            print_warning(f"{msg} — installs requiring sudo will fail fast")

    def _apply_sequential(stage: str) -> None:
        for comp in INSTALL_COMPONENTS:
            if comp.apply_stage == stage and (plans[comp].has_changes or force):
                comp.apply(ctx, plans[comp])

    # Pre-stage components install tools the rest depend on.
    _apply_sequential("pre")

    parallel_comps = [c for c in INSTALL_COMPONENTS if c.apply_stage == "parallel"]
    parallel_plans = {
        c: plans[c] for c in parallel_comps if plans[c].has_changes or force
    }
    if parallel_plans:
        run_components_parallel(
            list(parallel_plans.keys()), "apply", ctx, plans=parallel_plans
        )

    # gh auth state is mutated by these components; run sequentially to avoid races
    _apply_sequential("post")
