"""Upgrade command — upgrades shell-configs to the latest version."""

from __future__ import annotations

import subprocess
import sys

import click


@click.command()
@click.option("--check", is_flag=True, help="Check for updates without installing")
@click.option("--force", is_flag=True, help="Force reinstall even if up to date")
@click.option(
    "-y", "--yes", is_flag=True, help="Auto-confirm installation without prompting"
)
@click.pass_context
def upgrade(ctx: click.Context, check: bool, force: bool, yes: bool) -> None:
    """Upgrade shell-configs to the latest version from GitHub.

    Examples:
        shell-configs upgrade             # Check and install updates
        shell-configs upgrade --check     # Only check for updates
        shell-configs upgrade -y          # Auto-confirm installation
    """
    from shell_configs.bootstrap import (
        UPDATABLE_TOOLS,
        check_tool_updates,
        perform_github_update,
    )
    from shell_configs.bootstrap.installer import make_github_install_url
    from shell_configs.display import (
        console,
        print_done,
        print_error,
        print_hint,
        print_info,
        print_success,
        print_warning,
    )

    tools = [t for t in UPDATABLE_TOOLS if t.is_installed()]

    if not tools:
        print_warning("No tools are installed")
        sys.exit(1)

    tool_updates = []
    for tool in tools:
        try:
            current = tool.get_version()
            if current:
                console.print(
                    f"[dim]{tool.display_name} current version: {current}[/dim]"
                )
        except Exception as e:
            print_error(f"Could not get {tool.display_name} version: {e}")
            continue

        with console.status(f"Checking {tool.display_name} for updates..."):
            try:
                update_info = check_tool_updates(tool)
            except Exception as e:
                print_error(f"Failed to check {tool.display_name} updates: {e}")
                continue

        if update_info and (update_info.has_update or force):
            tool_updates.append((tool, update_info))
        elif update_info and not update_info.has_update:
            print_success(f"{tool.display_name} is already up to date!")

    console.print()

    if not tool_updates and not force:
        print_success("All tools are up to date!")
        return

    if not check:
        for tool, update_info in tool_updates:
            if update_info.has_update:
                console.print(
                    f"[cyan]Update available for {tool.display_name}:[/cyan] "
                    f"{update_info.current_version} → {update_info.latest_version}"
                )

                if update_info.changelog_entries:
                    console.print()
                    for version, notes in update_info.changelog_entries:
                        console.print(f"  [bold]v{version}[/bold]")
                        for line in notes.strip().split("\n"):
                            if line.strip():
                                console.print(f"    {line.strip()}")
                    console.print()

    if check:
        if tool_updates:
            print_hint("Run 'shell-configs upgrade' to install")
        return

    if not force and not yes:
        if len(tool_updates) == 1:
            prompt = f"\nInstall {tool_updates[0][0].display_name} update?"
        else:
            prompt = f"\nInstall {len(tool_updates)} updates?"
        if not click.confirm(prompt, default=True):
            print_info("Cancelled")
            return

    upgraded_tools = []
    for tool, _ in tool_updates:
        with console.status(f"Upgrading {tool.display_name}..."):
            try:
                success, msg, was_upgraded = perform_github_update(
                    make_github_install_url(tool.github_repo)
                )
            except Exception as e:
                print_error(f"{tool.display_name} upgrade failed: {e}")
                continue

        if success:
            if was_upgraded:
                upgraded_tools.append(tool)
                print_success(f"{tool.display_name} upgraded successfully!")
            else:
                print_done(f"{tool.display_name} is already up to date")
        else:
            print_error(f"{tool.display_name} upgrade failed: {msg}")

    if upgraded_tools:
        console.print()
        console.print("[cyan]Installing updated configurations...[/cyan]")
        import shutil

        shell_configs_bin = shutil.which("shell-configs")
        if shell_configs_bin:
            subprocess.run([shell_configs_bin, "install", "--yes"])
        else:
            from shell_configs.cli.commands.install import install

            ctx.invoke(install, yes=True)
