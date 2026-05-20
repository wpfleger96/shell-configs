"""Install command — parallel plan/apply flow over INSTALL_COMPONENTS."""

from __future__ import annotations

from pathlib import Path

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
    help="Comma-separated list of shells to install (e.g., bash,zsh,git)",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it"
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option(
    "--config-dir",
    type=click.Path(exists=True, path_type=Path),
    hidden=True,
    help="Override config directory path (for setup command)",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def install(
    shells: list[str] | None,
    dry_run: bool,
    yes: bool,
    config_dir: Path | None,
    profile_name: str | None,
) -> None:
    """Install or update managed configuration sections."""
    from shell_configs.cli.components import INSTALL_COMPONENTS
    from shell_configs.display import print_info, print_warning

    ctx = build_context(
        profile_name, shells, config_dir=config_dir, dry_run=dry_run, yes=yes
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

    if not has_changes:
        print_info("Everything is already in sync")
        return

    if not ctx.yes and not ctx.dry_run:
        if not click.confirm("Apply all changes?"):
            return

    if ctx.dry_run:
        return

    from shell_configs.cli.components.gh_auth import GhAuthComponent
    from shell_configs.cli.components.gh_extensions import GhExtensionsComponent
    from shell_configs.cli.components.languages import LanguagesComponent
    from shell_configs.cli.components.packages import RequiredPackagesComponent
    from shell_configs.cli.components.signing import SigningComponent

    # RequiredPackages and Languages install infrastructure that later components depend on
    gh_auth_comp = None
    signing_comp = None
    gh_ext_comp = None
    required_pkg = None
    languages_comp = None
    parallel_comps = []
    for comp in INSTALL_COMPONENTS:
        if isinstance(comp, RequiredPackagesComponent):
            required_pkg = comp
        elif isinstance(comp, LanguagesComponent):
            languages_comp = comp
        elif isinstance(comp, GhAuthComponent):
            gh_auth_comp = comp
        elif isinstance(comp, SigningComponent):
            signing_comp = comp
        elif isinstance(comp, GhExtensionsComponent):
            gh_ext_comp = comp
        else:
            parallel_comps.append(comp)

    if required_pkg and plans[required_pkg].has_changes:
        required_pkg.apply(ctx, plans[required_pkg])

    if languages_comp and plans[languages_comp].has_changes:
        languages_comp.apply(ctx, plans[languages_comp])

    parallel_plans = {c: plans[c] for c in parallel_comps if plans[c].has_changes}
    if parallel_plans:
        run_components_parallel(
            list(parallel_plans.keys()), "apply", ctx, plans=parallel_plans
        )

    # gh auth state is mutated by these components; run sequentially to avoid races
    if gh_auth_comp and plans[gh_auth_comp].has_changes:
        gh_auth_comp.apply(ctx, plans[gh_auth_comp])
    if signing_comp and plans[signing_comp].has_changes:
        signing_comp.apply(ctx, plans[signing_comp])
    if gh_ext_comp and plans[gh_ext_comp].has_changes:
        gh_ext_comp.apply(ctx, plans[gh_ext_comp])
