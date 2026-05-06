"""Info command — shows installation source and version info."""

from __future__ import annotations

import click


@click.command()
def info() -> None:
    """Show installation source and version info for shell-configs.

    Displays how shell-configs was installed (GitHub) along with current
    version and update availability.
    """
    from rich.table import Table

    from shell_configs.bootstrap import (
        UPDATABLE_TOOLS,
        check_tool_updates,
    )
    from shell_configs.bootstrap.installer import get_tool_source
    from shell_configs.display import console

    table = Table(title="shell-configs Installation Info", show_header=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Source", style="bold")
    table.add_column("Version")
    table.add_column("Update")

    has_updates = False

    for tool in UPDATABLE_TOOLS:
        tool_name = tool.display_name

        if not tool.is_installed():
            table.add_row(tool_name, "-", "-", "[dim](not installed)[/dim]")
            continue

        source = get_tool_source(tool.package_name)
        source_display = source.name.lower() if source else "[dim]unknown[/dim]"

        version = tool.get_version()
        version_display = version if version else "[dim]unknown[/dim]"

        update_display = "-"
        try:
            update_info = check_tool_updates(tool, timeout=5)
            if update_info and update_info.has_update:
                update_display = f"[cyan]{update_info.latest_version} available[/cyan]"
                has_updates = True
        except Exception:
            update_display = "[dim](check failed)[/dim]"

        table.add_row(tool_name, source_display, version_display, update_display)

    console.print(table)

    if has_updates:
        console.print("\n[dim]Run 'shell-configs upgrade' to install updates.[/dim]")
