"""Extensions subcommand group."""

from __future__ import annotations

import click

from shell_configs.cli.helpers import (
    _get_extension_shells,
    _print_extension_result,
    _print_ignored_builtin_extensions,
    load_profile_context,
)
from shell_configs.cli.options import profile_option, shells_option, yes_option


@click.group()
def extensions() -> None:
    """Manage IDE extensions for VSCode and Cursor."""
    pass


@extensions.command(name="status")
@shells_option("Comma-separated list of IDEs (e.g., vscode,cursor)")
@profile_option
def extensions_status(shells: list[str] | None, profile_name: str | None) -> None:
    """Show extension sync status for each IDE."""
    from rich.table import Table

    from shell_configs.display import (
        ICON_SUCCESS,
        ICON_WARNING,
        console,
        print_builtin,
        print_warning,
    )
    from shell_configs.extensions import compute_extension_states

    _, registry, active_profile = load_profile_context(profile_name)

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        print_warning("No IDEs with extension management found")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("IDE", style="cyan")
    table.add_column("Desired")
    table.add_column("Installed")
    table.add_column("Missing")
    table.add_column("Extra")
    table.add_column("Status")
    ignored_by_shell: list[tuple[str, frozenset[str]]] = []

    for st in compute_extension_states(ide_shells, active_profile):
        shell, invoker, cli_cmd = st.shell, st.invoker, st.cli_cmd
        desired, installed, diff = st.desired, st.installed, st.diff
        if diff.ignored:
            ignored_by_shell.append((shell.display_name, diff.ignored))

        if diff.missing or diff.extra:
            status_str = f"{ICON_WARNING} out of sync"
        elif diff.ignored:
            status_str = f"{ICON_WARNING} built-ins ignored"
        else:
            status_str = f"{ICON_SUCCESS} synced"

        table.add_row(
            shell.display_name,
            str(len(desired)),
            str(len(installed)),
            str(len(diff.missing)) if diff.missing else "[green]0[/green]",
            str(len(diff.extra)) if diff.extra else "[green]0[/green]",
            status_str,
        )

    console.print(table)
    if ignored_by_shell:
        for shell_display_name, ignored in ignored_by_shell:
            ignored_list = ", ".join(sorted(ignored))
            print_builtin(
                f"{shell_display_name}: ignoring built-in extensions from config: {ignored_list}"
            )


@extensions.command(name="diff")
@shells_option("Comma-separated list of IDEs (e.g., vscode,cursor)")
@profile_option
def extensions_diff(shells: list[str] | None, profile_name: str | None) -> None:
    """Show differences between desired and installed extensions."""
    from shell_configs.display import (
        console,
        print_add,
        print_builtin,
        print_dim,
        print_error,
        print_info,
        print_section,
        print_warning,
    )
    from shell_configs.extensions import compute_extension_states

    _, registry, active_profile = load_profile_context(profile_name)

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        print_warning("No IDEs with extension management found")
        return

    found_diffs = False
    for st in compute_extension_states(ide_shells, active_profile):
        shell, invoker, cli_cmd = st.shell, st.invoker, st.cli_cmd
        desired, installed, diff = st.desired, st.installed, st.diff

        if not diff.missing and not diff.extra and not diff.ignored:
            continue

        found_diffs = True
        print_section(shell.display_name)

        if diff.ignored:
            console.print(
                f"  [yellow]Ignored built-ins in config ({len(diff.ignored)}):[/yellow]"
            )
            for ext_id in sorted(diff.ignored):
                print_builtin(ext_id, indent=4)

        if diff.missing:
            console.print(f"  [yellow]Missing ({len(diff.missing)}):[/yellow]")
            for ext_id in sorted(diff.missing):
                print_error(ext_id, indent=4)

        if diff.extra:
            print_dim(f"Extra ({len(diff.extra)}):", indent=2)
            for ext_id in sorted(diff.extra):
                print_add(ext_id, indent=4)

    if not found_diffs:
        print_info("All IDE extensions are in sync")


@extensions.command(name="install")
@shells_option("Comma-separated list of IDEs (e.g., vscode,cursor)")
@click.option(
    "--prune", is_flag=True, help="Uninstall extensions not in the desired list"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it"
)
@yes_option
@profile_option
def extensions_install(
    shells: list[str] | None,
    prune: bool,
    dry_run: bool,
    yes: bool,
    profile_name: str | None,
) -> None:
    """Install (and optionally prune) extensions for each IDE."""
    from shell_configs.display import (
        console,
        print_hint,
        print_info,
        print_progress,
        print_section,
        print_warning,
    )
    from shell_configs.extensions import ExtensionManager, compute_extension_states

    _, registry, active_profile = load_profile_context(profile_name)
    ext_manager = ExtensionManager()

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        print_warning("No IDEs with extension management found")
        return

    any_activity = False
    for st in compute_extension_states(ide_shells, active_profile):
        shell, invoker, cli_cmd = st.shell, st.invoker, st.cli_cmd
        desired, installed, diff = st.desired, st.installed, st.diff

        to_install = diff.missing
        to_uninstall = diff.extra if prune else frozenset()
        printed_header = False

        if diff.ignored:
            any_activity = True
            printed_header = _print_ignored_builtin_extensions(
                console,
                shell.display_name,
                diff.ignored,
                header_printed=printed_header,
            )

        if not to_install and not to_uninstall:
            continue

        any_activity = True
        if not printed_header:
            print_section(shell.display_name)
            printed_header = True

        if to_install:
            print_progress(f"Installing {len(to_install)} extension(s)...", indent=2)
            if not dry_run and not yes:
                if not click.confirm("  Proceed?", default=True):
                    print_info(f"Skipping {shell.display_name} installs", indent=2)
                    to_install = frozenset()

            if to_install:
                results = ext_manager.install_extensions(
                    cli_cmd, set(to_install), dry_run=dry_run, invoker=invoker
                )
                for r in results:
                    _print_extension_result(r)

        if to_uninstall:
            print_progress(
                f"Pruning {len(to_uninstall)} extra extension(s)...", indent=2
            )
            if not dry_run and not yes:
                if not click.confirm("  Proceed with pruning?", default=False):
                    print_info(f"Skipping {shell.display_name} prune", indent=2)
                    to_uninstall = frozenset()

            if to_uninstall:
                results = ext_manager.uninstall_extensions(
                    cli_cmd, set(to_uninstall), dry_run=dry_run, invoker=invoker
                )
                for r in results:
                    _print_extension_result(r)

    if not any_activity:
        print_info("All IDE extensions are already in sync")

    if dry_run and any_activity:
        print_hint("Use without --dry-run to apply changes.")


@extensions.command(name="list")
@shells_option("Comma-separated list of IDEs (e.g., vscode,cursor)")
@profile_option
def extensions_list(shells: list[str] | None, profile_name: str | None) -> None:
    """List all extensions for each IDE with their install status."""
    from rich.table import Table

    from shell_configs.display import (
        ICON_ERROR,
        ICON_SUCCESS,
        console,
        dim,
        print_info,
        print_warning,
    )
    from shell_configs.extensions import compute_extension_states

    _, registry, active_profile = load_profile_context(profile_name)

    ide_shells = _get_extension_shells(registry, shells)
    if not ide_shells:
        print_warning("No IDEs with extension management found")
        return

    any_output = False
    for st in compute_extension_states(ide_shells, active_profile):
        shell, invoker, cli_cmd = st.shell, st.invoker, st.cli_cmd
        desired, installed, diff = st.desired, st.installed, st.diff

        rows: list[tuple[str, str]] = []
        for ext_id in diff.matched:
            rows.append((ext_id, f"{ICON_SUCCESS} installed"))
        for ext_id in diff.missing:
            rows.append((ext_id, f"{ICON_ERROR} missing"))
        for ext_id in diff.extra:
            rows.append((ext_id, dim("+ extra")))
        for ext_id in diff.ignored:
            rows.append((ext_id, dim("~ builtin")))

        if not rows:
            continue

        any_output = True
        table = Table(
            title=shell.display_name,
            show_header=True,
            header_style="bold",
            title_style="bold cyan",
            title_justify="left",
        )
        table.add_column("Extension")
        table.add_column("Status")

        for ext_id, status in sorted(rows, key=lambda r: r[0]):
            table.add_row(ext_id, status)

        console.print(table)

    if not any_output:
        print_info("No extension data available")
