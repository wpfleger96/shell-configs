"""Install command — loops over INSTALL_COMPONENTS calling install()."""

from __future__ import annotations

from pathlib import Path

import click

from shell_configs.cli.helpers import build_context, parse_shell_filter


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
    from shell_configs.display import print_warning

    ctx = build_context(
        profile_name, shells, config_dir=config_dir, dry_run=dry_run, yes=yes
    )
    if ctx is None:
        print_warning("No shells to install")
        return

    for component in INSTALL_COMPONENTS:
        if not component.install(ctx):
            break
