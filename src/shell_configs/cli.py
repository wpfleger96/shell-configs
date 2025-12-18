"""Command-line interface for shell-configs."""

import difflib
import logging
import sys

from pathlib import Path

import click

from rich.prompt import Confirm
from rich.syntax import Syntax

from shell_configs import __version__
from shell_configs.config import ConfigReader
from shell_configs.display import (
    add_additional_file_row,
    add_status_row,
    add_validation_row,
    console,
    create_status_table,
    create_validation_table,
    get_status_indicator,
    print_error,
    print_info,
    print_operation_result,
    print_warning,
)
from shell_configs.manager import ConfigManager, OperationResult
from shell_configs.shells.base import Shell
from shell_configs.shells.registry import ShellRegistry

logger = logging.getLogger(__name__)


def _background_update_check() -> None:
    """Run update check in background thread for all registered tools.

    This runs silently and saves results for display on next CLI invocation.
    """
    from datetime import datetime

    from shell_configs.bootstrap import (
        UPDATABLE_TOOLS,
        check_tool_updates,
        load_auto_update_config,
        save_auto_update_config,
        save_pending_update,
    )

    try:
        for tool in UPDATABLE_TOOLS:
            update_info = check_tool_updates(tool)
            if update_info and update_info.has_update:
                save_pending_update(update_info, tool.tool_id)

        config = load_auto_update_config()
        config.last_check = datetime.now().isoformat()
        save_auto_update_config(config)
    except Exception as e:
        logger.debug(f"Background update check failed: {e}")


def _check_pending_updates() -> None:
    """Check for and display pending update notifications."""
    from shell_configs.bootstrap import (
        clear_all_pending_updates,
        get_tool_by_id,
        load_all_pending_updates,
    )

    try:
        pending = load_all_pending_updates()
        if not pending:
            return

        updates = []
        for tid, info in pending.items():
            tool = get_tool_by_id(tid)
            if tool:
                updates.append(
                    f"{tool.display_name} {info.current_version} → {info.latest_version}"
                )

        if not updates:
            return

        update_label = "Update available" if len(updates) == 1 else "Updates available"
        console.print(f"\n[cyan]{update_label}:[/cyan] {', '.join(updates)}")

        if sys.stdin.isatty() and sys.stdout.isatty():
            prompt = "Install now?" if len(updates) == 1 else "Install all updates?"
            if Confirm.ask(prompt, default=False):
                ctx = click.get_current_context()
                ctx.invoke(upgrade, check=False, force=False)
            else:
                console.print("[dim]Run 'shell-configs upgrade' when ready[/dim]")
        else:
            console.print("[dim]Run 'shell-configs upgrade' to install[/dim]")

        clear_all_pending_updates()
    except Exception as e:
        logger.debug(f"Failed to check pending updates: {e}")


def version_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Custom version callback that also checks for updates."""
    if not value or ctx.resilient_parsing:
        return

    console.print(f"shell-configs, version {__version__}")

    try:
        from shell_configs.bootstrap import check_tool_updates, get_tool_by_id

        tool = get_tool_by_id("shell-configs")
        if tool:
            update_info = check_tool_updates(tool, timeout=3)
            if update_info and update_info.has_update:
                console.print(
                    f"\n[cyan]Update available:[/cyan] {update_info.current_version} → {update_info.latest_version}"
                )
                console.print("[dim]Run 'shell-configs upgrade' to install[/dim]")
    except Exception as e:
        logger.debug(f"Failed to check for updates in version callback: {e}")

    ctx.exit()


def parse_shell_filter(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> list[str] | None:
    """Parse shell filter from comma-separated string."""
    if not value:
        return None
    return [s.strip() for s in value.split(",")]


def _get_selected_shells(
    registry: ShellRegistry,
    shells_filter: list[str] | None = None,
    config_reader: ConfigReader | None = None,
    use_all: bool = False,
) -> list[Shell]:
    """Get selected shells based on filter or available configs.

    Args:
        registry: ShellRegistry instance
        shells_filter: Optional list of shell names to filter
        config_reader: Optional ConfigReader for auto-detecting available shells
        use_all: If True and no filter, return all registered shells

    Returns:
        List of selected Shell instances, or exits on error

    Raises:
        SystemExit: If invalid shell names provided
    """
    if shells_filter:
        selected_shells, invalid = registry.filter_by_names(shells_filter)
        if invalid:
            print_error(f"Unknown shells: {', '.join(invalid)}")
            print_info(f"Available shells: {', '.join(registry.get_names())}")
            sys.exit(1)
    elif use_all:
        selected_shells = registry.get_all()
    elif config_reader:
        available = config_reader.get_available_shells()
        selected_shells, _ = registry.filter_by_names(available)
    else:
        selected_shells = []

    return selected_shells


def _display_diffs_for_shells(
    selected_shells: list[Shell],
    config_reader: ConfigReader,
    manager: ConfigManager,
) -> bool:
    """Display diffs for selected shells before install.

    Returns:
        True if diffs were found and displayed, False otherwise
    """
    found_diffs = False

    for shell in selected_shells:
        for config_file in shell.get_config_files():
            repo_content = config_reader.get_config_content(
                shell.name, config_file.repo_config_name
            )
            if repo_content is None:
                continue

            shared_content = None
            if shell.supports_shared_config():
                shared_content = config_reader.get_shared_config_content(shell.name)

            repo_content = manager.combine_content(shared_content, repo_content)

            section = manager.extract_managed_section(config_file.path)

            if section is None:
                console.print(
                    f"\n[bold cyan]{shell.display_name}[/bold cyan]: {config_file.path}"
                )
                console.print("[yellow]Not installed[/yellow]")
                found_diffs = True
                continue

            if section.content.strip() == repo_content.strip():
                continue

            found_diffs = True
            console.print(
                f"\n[bold cyan]{shell.display_name}[/bold cyan]: {config_file.path}"
            )

            installed_lines = section.content.splitlines(keepends=True)
            repo_lines = repo_content.splitlines(keepends=True)

            diff_lines = difflib.unified_diff(
                installed_lines,
                repo_lines,
                fromfile="Installed",
                tofile="Repository",
                lineterm="",
            )

            diff_text = "\n".join(diff_lines)
            if diff_text:
                syntax = Syntax(diff_text, "diff", theme="monokai")
                console.print(syntax)

        additional_files = shell.get_additional_files()
        for additional_file in additional_files:
            if not additional_file.target_path.exists():
                console.print(
                    f"\n[bold cyan]{shell.display_name}[/bold cyan]: {additional_file.target_path}"
                )
                console.print("[yellow]Not installed[/yellow]")
                found_diffs = True
                continue

            if manager.files_match(
                additional_file.source_path, additional_file.target_path
            ):
                continue

            found_diffs = True
            console.print(
                f"\n[bold cyan]{shell.display_name}[/bold cyan]: {additional_file.target_path}"
            )

            installed_content = additional_file.target_path.read_text()
            repo_content = additional_file.source_path.read_text()

            installed_lines = installed_content.splitlines(keepends=True)
            repo_lines = repo_content.splitlines(keepends=True)

            diff_lines = difflib.unified_diff(
                installed_lines,
                repo_lines,
                fromfile="Installed",
                tofile="Repository",
                lineterm="",
            )

            diff_text = "\n".join(diff_lines)
            if diff_text:
                syntax = Syntax(diff_text, "diff", theme="monokai")
                console.print(syntax)

    return found_diffs


@click.group()
@click.option(
    "--version",
    is_flag=True,
    callback=version_callback,
    expose_value=False,
    is_eager=True,
    help="Show version and check for updates",
)
def cli() -> None:
    """Manage shell configuration files across machines."""
    import os
    import threading

    from shell_configs.bootstrap import load_auto_update_config, should_check_now

    _check_pending_updates()

    try:
        if "PYTEST_CURRENT_TEST" not in os.environ:
            config = load_auto_update_config()
            if config.enabled and should_check_now(config):
                thread = threading.Thread(target=_background_update_check, daemon=True)
                thread.start()
    except Exception:
        pass


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to install (e.g., bash,zsh,git)",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it"
)
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--config-dir",
    type=click.Path(exists=True, path_type=Path),
    hidden=True,
    help="Override config directory path (for setup command)",
)
def install(
    shells: list[str] | None, dry_run: bool, force: bool, config_dir: Path | None
) -> None:
    """Install or update managed configuration sections."""
    config_reader = ConfigReader(config_dir=config_dir)
    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(
        registry, shells, config_reader=config_reader
    )

    if not selected_shells:
        print_warning("No shells to install")
        return

    if not force and not dry_run:
        has_diffs = _display_diffs_for_shells(selected_shells, config_reader, manager)

        if has_diffs:
            console.print()
            if not click.confirm("Apply these changes?"):
                print_info("Installation cancelled")
                return
        else:
            print_info("All configurations already in sync")
            return

    results = {}
    additional_file_results = {}

    for shell in selected_shells:
        for config_file in shell.get_config_files():
            if config_file.repo_config_name is None:
                content = None
            else:
                content = config_reader.get_config_content(
                    shell.name, config_file.repo_config_name
                )
                if content is None:
                    print_warning(
                        f"No configuration found for {shell.name}/{config_file.repo_config_name}"
                    )
                    continue

            shared_content = None
            if shell.supports_shared_config():
                shared_content = config_reader.get_shared_config_content(shell.name)

            if content is None and shared_content is None:
                continue

            result, message = manager.install_section(
                config_file.path,
                content,
                dry_run=dry_run,
                shared_content=shared_content,
            )
            print_operation_result(result, message)
            results[shell.name] = result

    for shell in selected_shells:
        additional_files = shell.get_additional_files()
        for additional_file in additional_files:
            result, message = manager.install_additional_file(
                additional_file.source_path,
                additional_file.target_path,
                dry_run=dry_run,
            )
            print_operation_result(result, message)
            additional_file_results[str(additional_file.target_path)] = result

    if dry_run:
        print_info("Dry run complete. Use without --dry-run to apply changes.")

    success_count = sum(
        1
        for r in results.values()
        if r in [OperationResult.CREATED, OperationResult.UPDATED]
    )
    additional_success_count = sum(
        1
        for r in additional_file_results.values()
        if r in [OperationResult.CREATED, OperationResult.UPDATED]
    )
    total_success = success_count + additional_success_count

    if total_success > 0 and not dry_run:
        print_info(f"Successfully installed/updated {total_success} file(s)")


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to uninstall",
)
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
def uninstall(shells: list[str] | None, force: bool) -> None:
    """Remove managed configuration sections."""
    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(registry, shells, use_all=True)

    if not selected_shells:
        print_warning("No shells to uninstall")
        return

    if not force:
        shell_names = ", ".join([s.display_name for s in selected_shells])
        if not click.confirm(
            f"Remove managed sections from {shell_names} configurations?"
        ):
            print_info("Uninstallation cancelled")
            return

    results = {}
    additional_file_results = {}

    for shell in selected_shells:
        for config_file in shell.get_config_files():
            result, message = manager.uninstall_section(config_file.path)
            if result != OperationResult.NOT_FOUND:
                print_operation_result(result, message)
            results[shell.name] = result

    for shell in selected_shells:
        additional_files = shell.get_additional_files()
        for additional_file in additional_files:
            result, message = manager.uninstall_additional_file(
                additional_file.target_path
            )
            if result != OperationResult.NOT_FOUND:
                print_operation_result(result, message)
            additional_file_results[str(additional_file.target_path)] = result

    success_count = sum(1 for r in results.values() if r == OperationResult.REMOVED)
    additional_success_count = sum(
        1 for r in additional_file_results.values() if r == OperationResult.REMOVED
    )
    total_success = success_count + additional_success_count

    if total_success > 0:
        print_info(f"Successfully removed {total_success} file(s)")


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to check",
)
def status(shells: list[str] | None) -> None:
    """Show the status of managed configurations."""
    config_reader = ConfigReader()
    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(
        registry, shells, config_reader=config_reader
    )

    if not selected_shells:
        print_warning("No shell configurations found")
        return

    table = create_status_table()

    for shell in selected_shells:
        for config_file in shell.get_config_files():
            repo_content = config_reader.get_config_content(
                shell.name, config_file.repo_config_name
            )
            if repo_content is None:
                continue

            shared_content = None
            if shell.supports_shared_config():
                shared_content = config_reader.get_shared_config_content(shell.name)

            repo_content = manager.combine_content(shared_content, repo_content)

            section = manager.extract_managed_section(config_file.path)
            exists = section is not None
            synced = (
                (exists and section.content.strip() == repo_content.strip())
                if section
                else False
            )

            status_str = get_status_indicator(synced, exists)
            add_status_row(table, shell.display_name, config_file.path, status_str)

        additional_files = shell.get_additional_files()
        for additional_file in additional_files:
            exists = additional_file.target_path.exists()
            synced = manager.files_match(
                additional_file.source_path, additional_file.target_path
            )
            status_str = get_status_indicator(synced, exists)
            add_additional_file_row(table, additional_file.target_path, status_str)

    console.print(table)

    console.print()

    console.print("[bold cyan]Shell Completions[/bold cyan]\n")
    from shell_configs.completions import (
        detect_shell,
        find_config_file,
        get_supported_shells,
        is_completion_installed,
    )

    detected_shell = detect_shell()
    if detected_shell:
        config_path = find_config_file(detected_shell)
        if config_path and is_completion_installed(config_path):
            console.print(
                f"  [green]✓[/green] {detected_shell} completion installed ({config_path})"
            )
        else:
            console.print(
                f"  [yellow]○[/yellow] {detected_shell} completion not installed "
                "(run: shell-configs completions install)"
            )
    else:
        supported = ", ".join(get_supported_shells())
        console.print(
            f"  [dim]Shell completion not available for your shell (only {supported} supported)[/dim]"
        )

    console.print()


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to diff",
)
def diff(shells: list[str] | None) -> None:
    """Show differences between repository and installed configurations."""
    config_reader = ConfigReader()
    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(
        registry, shells, config_reader=config_reader
    )

    if not selected_shells:
        print_warning("No shell configurations found")
        return

    found_diffs = _display_diffs_for_shells(selected_shells, config_reader, manager)

    if not found_diffs:
        print_info("All configurations are in sync")


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to validate",
)
def validate(shells: list[str] | None) -> None:
    """Validate configuration file syntax."""
    config_reader = ConfigReader()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(
        registry, shells, config_reader=config_reader
    )

    if not selected_shells:
        print_warning("No shell configurations found")
        return

    table = create_validation_table()
    all_valid = True

    for shell in selected_shells:
        for config_file in shell.get_config_files():
            content = config_reader.get_config_content(
                shell.name, config_file.repo_config_name
            )
            if content is None:
                continue

            valid, message = shell.validate_syntax(content)
            add_validation_row(table, shell.display_name, valid, message)

            if not valid:
                all_valid = False

    console.print(table)

    if not all_valid:
        print_error("Some configurations have syntax errors")
        sys.exit(1)
    else:
        print_info("All configurations are valid")


@cli.command("list-shells")
def list_shells() -> None:
    """List all available shell configurations."""
    config_reader = ConfigReader()
    registry = ShellRegistry()
    all_shells = registry.get_all()
    available = config_reader.get_available_shells()

    console.print("[bold]Available Shells:[/bold]")
    for shell in all_shells:
        has_config = shell.name in available
        status = "[green]✓[/green]" if has_config else "[dim]○[/dim]"
        console.print(f"  {status} {shell.display_name} ({shell.name})")

    if not available:
        print_warning(
            "No shell configurations found. Add config files to the config/ directory."
        )


@cli.command()
@click.option("--check", is_flag=True, help="Check for updates without installing")
@click.option("--force", is_flag=True, help="Force reinstall even if up to date")
@click.pass_context
def upgrade(ctx: click.Context, check: bool, force: bool) -> None:
    """Upgrade shell-configs to the latest version from GitHub.

    Examples:
        shell-configs upgrade             # Check and install updates
        shell-configs upgrade --check     # Only check for updates
    """
    from shell_configs.bootstrap import (
        UPDATABLE_TOOLS,
        check_tool_updates,
        perform_github_update,
    )
    from shell_configs.bootstrap.installer import GITHUB_REPO_URL

    tools = [t for t in UPDATABLE_TOOLS if t.is_installed()]

    if not tools:
        console.print("[yellow]⚠[/yellow] No tools are installed")
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
            console.print(
                f"[red]Error:[/red] Could not get {tool.display_name} version: {e}"
            )
            continue

        with console.status(f"Checking {tool.display_name} for updates..."):
            try:
                update_info = check_tool_updates(tool)
            except Exception as e:
                console.print(
                    f"[red]Error:[/red] Failed to check {tool.display_name} updates: {e}"
                )
                continue

        if update_info and (update_info.has_update or force):
            tool_updates.append((tool, update_info))
        elif update_info and not update_info.has_update:
            console.print(
                f"[green]✓[/green] {tool.display_name} is already up to date!"
            )

    console.print()

    if not tool_updates and not force:
        console.print("[green]✓[/green] All tools are up to date!")
        return

    if not check:
        for tool, update_info in tool_updates:
            if update_info.has_update:
                console.print(
                    f"[cyan]Update available for {tool.display_name}:[/cyan] "
                    f"{update_info.current_version} → {update_info.latest_version}"
                )

    if check:
        if tool_updates:
            console.print("\nRun [bold]shell-configs upgrade[/bold] to install")
        return

    if not force:
        if len(tool_updates) == 1:
            prompt = f"\nInstall {tool_updates[0][0].display_name} update?"
        else:
            prompt = f"\nInstall {len(tool_updates)} updates?"
        if not Confirm.ask(prompt, default=True):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    upgraded_tools = []
    for tool, _ in tool_updates:
        with console.status(f"Upgrading {tool.display_name}..."):
            try:
                success, msg, was_upgraded = perform_github_update(GITHUB_REPO_URL)
            except Exception as e:
                console.print(
                    f"\n[red]Error:[/red] {tool.display_name} upgrade failed: {e}"
                )
                continue

        if success:
            if was_upgraded:
                upgraded_tools.append(tool)
                console.print(
                    f"[green]✓[/green] {tool.display_name} upgraded successfully!"
                )
            else:
                console.print(
                    f"[green]✓[/green] {tool.display_name} is already up to date"
                )
        else:
            console.print(
                f"[red]Error:[/red] {tool.display_name} upgrade failed: {msg}"
            )

    if upgraded_tools:
        console.print()
        console.print("[cyan]Installing updated configurations...[/cyan]")
        ctx.invoke(install, force=True)


@cli.command()
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
        source_display = source if source else "[dim]unknown[/dim]"

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


@cli.command()
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated shells to install",
)
@click.option("--skip-completions", is_flag=True, help="Skip shell completion setup")
@click.pass_context
def setup(
    ctx: click.Context,
    force: bool,
    dry_run: bool,
    shells: list[str] | None,
    skip_completions: bool,
) -> None:
    """One-command setup for shell-configs.

    Installs shell-configs globally via uv tool install, sets up shell
    configurations, and optionally installs tab completions.

    Run this after installing with uvx: uvx shell-configs setup
    """
    from shell_configs.bootstrap.installer import (
        get_tool_config_dir,
        install_tool,
    )
    from shell_configs.bootstrap.updater import (
        check_tool_updates,
        get_tool_by_id,
        perform_github_update,
    )
    from shell_configs.completions import (
        detect_shell,
        get_supported_shells,
        install_completion,
    )

    console.print(
        "\n[bold cyan]Step 1/3: Install shell-configs system-wide[/bold cyan]"
    )
    console.print(
        "[dim]This allows you to run 'shell-configs' from any directory.[/dim]\n"
    )

    shell_configs_tool = get_tool_by_id("shell-configs")
    tool_install_success = False

    if shell_configs_tool and shell_configs_tool.is_installed():
        try:
            update_info = check_tool_updates(shell_configs_tool, timeout=10)
            if update_info and update_info.has_update:
                if dry_run:
                    console.print(
                        f"[dim]Would upgrade shell-configs {update_info.current_version} → {update_info.latest_version}[/dim]"
                    )
                    tool_install_success = True
                else:
                    if not force and not Confirm.ask(
                        f"Upgrade shell-configs {update_info.current_version} → {update_info.latest_version}?",
                        default=True,
                    ):
                        console.print("[yellow]Skipped shell-configs upgrade[/yellow]")
                        tool_install_success = True
                    else:
                        from shell_configs.bootstrap.installer import GITHUB_REPO_URL

                        success, msg, _ = perform_github_update(GITHUB_REPO_URL)
                        if success:
                            console.print(
                                f"[green]✓[/green] Upgraded shell-configs ({update_info.current_version} → {update_info.latest_version})"
                            )
                            tool_install_success = True
                        else:
                            console.print(
                                f"[red]Error:[/red] Failed to upgrade shell-configs: {msg}"
                            )
            else:
                console.print("[green]✓[/green] shell-configs is already up to date")
                tool_install_success = True
        except Exception as e:
            logger.debug(f"Failed to check for updates: {e}")
            tool_install_success = False

    if not tool_install_success:
        if not force and not dry_run:
            if not Confirm.ask("Install shell-configs permanently?", default=True):
                console.print("[yellow]Setup cancelled[/yellow]")
                sys.exit(0)

        success, message = install_tool(force=force, dry_run=dry_run)

        if not success:
            console.print(f"[red]Error:[/red] {message}")
            sys.exit(1)

        console.print(f"[green]✓[/green] {message}")
        tool_install_success = True

    if not tool_install_success:
        sys.exit(1)

    config_dir = get_tool_config_dir("shell-configs") if not dry_run else None

    console.print(
        "\n[bold cyan]Step 2/3: Installing shell configurations[/bold cyan]\n"
    )

    ctx.invoke(
        install,
        shells=shells,
        dry_run=dry_run,
        force=force,
        config_dir=config_dir,
    )

    if not skip_completions:
        console.print("\n[bold cyan]Step 3/3: Shell completion setup[/bold cyan]\n")

        shell = detect_shell()
        if shell is None:
            supported = ", ".join(get_supported_shells())
            console.print(
                f"[yellow]⚠[/yellow] Could not detect shell. Supported: {supported}"
            )
            console.print("[dim]Skipping completion installation[/dim]")
        else:
            if not force and not dry_run:
                if not Confirm.ask(f"Install {shell} tab completion?", default=True):
                    console.print("[dim]Skipping completion installation[/dim]")
                else:
                    success, message = install_completion(shell, dry_run=dry_run)
                    if success:
                        console.print(f"[green]✓[/green] {message}")
                    else:
                        console.print(f"[yellow]⚠[/yellow] {message}")
            else:
                success, message = install_completion(shell, dry_run=dry_run)
                if success:
                    console.print(f"[green]✓[/green] {message}")
                else:
                    console.print(f"[yellow]⚠[/yellow] {message}")

    if dry_run:
        console.print("\n[dim]Dry run complete - no changes were made.[/dim]")
    else:
        console.print("\n[green bold]✓ Setup complete![/green bold]")
        console.print("You can now run shell-configs from anywhere.")


@cli.group()
def completions() -> None:
    """Manage shell tab completion."""
    pass


from shell_configs.completions import get_supported_shells

_SUPPORTED_SHELLS = list(get_supported_shells())


@completions.command(name="bash")
def completions_bash() -> None:
    """Output bash completion script for manual installation."""
    from shell_configs.completions import generate_completion_script

    try:
        script = generate_completion_script("bash")
        console.print(script)
        console.print(
            "\n[dim]To install: Add the above to your ~/.bashrc or run:[/dim]"
        )
        console.print("[dim]  shell-configs completions install[/dim]")
    except Exception as e:
        console.print(f"[red]Error generating completion script:[/red] {e}")
        sys.exit(1)


@completions.command(name="zsh")
def completions_zsh() -> None:
    """Output zsh completion script for manual installation."""
    from shell_configs.completions import generate_completion_script

    try:
        script = generate_completion_script("zsh")
        console.print(script)
        console.print("\n[dim]To install: Add the above to your ~/.zshrc or run:[/dim]")
        console.print("[dim]  shell-configs completions install[/dim]")
    except Exception as e:
        console.print(f"[red]Error generating completion script:[/red] {e}")
        sys.exit(1)


@completions.command(name="install")
@click.option(
    "--shell",
    type=click.Choice(_SUPPORTED_SHELLS, case_sensitive=False),
    help="Shell type (auto-detected if not specified)",
)
def completions_install(shell: str | None) -> None:
    """Install shell completion to config file."""
    from shell_configs.completions import detect_shell, install_completion

    if shell is None:
        shell = detect_shell()
        if shell is None:
            console.print(
                "[red]Error:[/red] Could not detect shell. Please specify with --shell"
            )
            sys.exit(1)
        console.print(f"[dim]Detected shell:[/dim] {shell}")

    success, message = install_completion(shell, dry_run=False)

    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]Error:[/red] {message}")
        sys.exit(1)


@completions.command(name="uninstall")
@click.option(
    "--shell",
    type=click.Choice(_SUPPORTED_SHELLS, case_sensitive=False),
    help="Shell type (auto-detected if not specified)",
)
def completions_uninstall(shell: str | None) -> None:
    """Remove shell completion from config file."""
    from shell_configs.completions import (
        detect_shell,
        find_config_file,
        uninstall_completion,
    )

    if shell is None:
        shell = detect_shell()
        if shell is None:
            console.print(
                "[red]Error:[/red] Could not detect shell. Please specify with --shell"
            )
            sys.exit(1)

    config_path = find_config_file(shell)
    if config_path is None:
        console.print(f"[red]Error:[/red] No {shell} config file found")
        sys.exit(1)

    success, message = uninstall_completion(config_path)

    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]Error:[/red] {message}")
        sys.exit(1)


@completions.command(name="status")
def completions_status() -> None:
    """Show shell completion installation status."""
    from shell_configs.completions import (
        detect_shell,
        find_config_file,
        get_supported_shells,
        is_completion_installed,
    )

    detected_shell = detect_shell()
    console.print("[bold cyan]Shell Completions Status[/bold cyan]\n")

    if detected_shell:
        console.print(f"Detected shell: [cyan]{detected_shell}[/cyan]\n")
    else:
        console.print("[yellow]No supported shell detected[/yellow]\n")

    from rich.table import Table

    table = Table(show_header=True)
    table.add_column("Shell")
    table.add_column("Status")
    table.add_column("Config File")

    for shell in get_supported_shells():
        config_path = find_config_file(shell)

        if config_path is None:
            status = "[dim]-[/dim]"
            config_str = "[dim]No config file found[/dim]"
        elif is_completion_installed(config_path):
            status = "[green]✓[/green]"
            config_str = str(config_path)
        else:
            status = "[yellow]○[/yellow]"
            config_str = f"{config_path} [dim](not installed)[/dim]"

        shell_name = f"[bold]{shell}[/bold]" if shell == detected_shell else shell
        table.add_row(shell_name, status, config_str)

    console.print(table)
    console.print("\n[dim]To install: shell-configs completions install[/dim]")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
