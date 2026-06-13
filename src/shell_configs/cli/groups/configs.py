"""Configs subcommand group.

Mirrors the ``scripts``/``packages`` groups: a focused entry point that drives
*only* the ``ConfigsComponent`` (shell config files, additional files,
preferences, state-db entries). Unlike the top-level ``install`` command it does
not touch the package/language/agent/gh/signing components, so it never performs
network or sudo operations — making it a safe, hermetic configs-only path.
"""

from __future__ import annotations

from pathlib import Path

import click

from shell_configs.cli.helpers import build_context, parse_shell_filter


@click.group()
def configs() -> None:
    """Manage shell configuration files (bash, zsh, git, editors)."""
    pass


@configs.command(name="install")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to install (e.g., bash,zsh,git)",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it"
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option("--force", is_flag=True, help="Force apply even if already in sync")
@click.option(
    "--config-dir",
    type=click.Path(exists=True, path_type=Path),
    hidden=True,
    help="Override config directory path",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def configs_install(
    shells: list[str] | None,
    dry_run: bool,
    yes: bool,
    force: bool,
    config_dir: Path | None,
    profile_name: str | None,
) -> None:
    """Install or update managed shell configuration sections."""
    from shell_configs.cli.components.configs import ConfigsComponent
    from shell_configs.display import console, print_info, print_warning

    ctx = build_context(
        profile_name,
        shells,
        config_dir=config_dir,
        dry_run=dry_run,
        yes=yes,
        force=force,
    )
    if ctx is None:
        print_warning("No shell configurations found")
        return

    component = ConfigsComponent()
    plan = component.plan(ctx)

    if plan.has_changes:
        component.display_plan(plan)

    if not plan.has_changes and not force:
        print_info("Everything is already in sync")
        return

    if plan.has_changes and not ctx.yes and not ctx.dry_run:
        console.print()
        if not click.confirm("Apply these changes?"):
            print_info("Installation cancelled")
            return

    component.apply(ctx, plan)


@configs.command(name="uninstall")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to uninstall",
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def configs_uninstall(shells: list[str] | None, yes: bool) -> None:
    """Remove managed shell configuration sections."""
    from shell_configs.cli.components.configs import ConfigsComponent
    from shell_configs.cli.context import Context
    from shell_configs.cli.helpers import _get_selected_shells
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
        if not click.confirm(f"Remove managed config sections ({shell_names})?"):
            print_info("Uninstallation cancelled")
            return

    ctx = Context(
        dry_run=False,
        yes=yes,
        force=False,
        profile_name=None,
        profile=None,
        selected_shells=tuple(selected_shells),
        config_reader=config_reader,
        registry=registry,
    )

    ConfigsComponent().uninstall(ctx)


@configs.command(name="status")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to check",
)
@click.option(
    "--config-dir",
    type=click.Path(exists=True, path_type=Path),
    hidden=True,
    help="Override config directory path",
)
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def configs_status(
    shells: list[str] | None,
    config_dir: Path | None,
    profile_name: str | None,
) -> None:
    """Show installation status of managed shell configurations."""
    from shell_configs.cli.components.configs import ConfigsComponent
    from shell_configs.display import print_warning

    ctx = build_context(profile_name, shells, config_dir=config_dir)
    if ctx is None:
        print_warning("No shell configurations found")
        return

    ConfigsComponent().status(ctx)
