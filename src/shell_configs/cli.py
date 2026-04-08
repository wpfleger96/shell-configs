"""Command-line interface for shell-configs."""

import difflib
import logging
import subprocess
import sys

from pathlib import Path
from typing import TYPE_CHECKING

import click

from shell_configs import __version__
from shell_configs.config import ConfigReader
from shell_configs.shells.base import merge_json_files

if TYPE_CHECKING:
    from shell_configs.manager import ConfigManager
    from shell_configs.shells.base import Shell
    from shell_configs.shells.registry import ShellRegistry

logger = logging.getLogger(__name__)


def version_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Custom version callback that also checks for updates."""
    if not value or ctx.resilient_parsing:
        return

    from shell_configs.display import console

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
    registry: "ShellRegistry",
    shells_filter: list[str] | None = None,
    config_reader: ConfigReader | None = None,
    use_all: bool = False,
) -> list["Shell"]:
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
    from shell_configs.display import print_error, print_info

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
    selected_shells: list["Shell"],
    config_reader: ConfigReader,
    manager: "ConfigManager",
) -> bool:
    """Display diffs for selected shells before install.

    Returns:
        True if diffs were found and displayed, False otherwise
    """
    from rich.syntax import Syntax

    from shell_configs.display import console

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

            if additional_file.base_source_path:
                repo_content = merge_json_files(
                    additional_file.base_source_path,
                    additional_file.source_path,
                )
            else:
                repo_content = additional_file.source_path.read_text()

            if additional_file.comment_prefix:
                section = manager.extract_managed_section(
                    additional_file.target_path,
                    comment_prefix=additional_file.comment_prefix,
                )
                if section is None:
                    console.print(
                        f"\n[bold cyan]{shell.display_name}[/bold cyan]: {additional_file.target_path}"
                    )
                    console.print("[yellow]Not installed[/yellow]")
                    found_diffs = True
                    continue

                if manager.managed_content_matches(section.content, repo_content):
                    continue

                installed_content = section.content
                repo_content = manager._strip_json_outer_brackets(repo_content)
            else:
                if additional_file.base_source_path:
                    if manager.content_matches(
                        repo_content, additional_file.target_path
                    ):
                        continue
                else:
                    if manager.files_match(
                        additional_file.source_path, additional_file.target_path
                    ):
                        continue
                installed_content = additional_file.target_path.read_text()

            found_diffs = True
            console.print(
                f"\n[bold cyan]{shell.display_name}[/bold cyan]: {additional_file.target_path}"
            )

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

        preferences_files = shell.get_preferences_files()
        for pref_file in preferences_files:
            pref_diff = manager.diff_preferences_file(
                pref_file.source_path, pref_file.domain
            )
            if pref_diff:
                found_diffs = True
                console.print(
                    f"\n[bold cyan]{shell.display_name}[/bold cyan]: "
                    f"{pref_file.domain} (preferences)"
                )
                console.print(pref_diff)

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
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option(
    "--config-dir",
    type=click.Path(exists=True, path_type=Path),
    hidden=True,
    help="Override config directory path (for setup command)",
)
def install(
    shells: list[str] | None, dry_run: bool, yes: bool, config_dir: Path | None
) -> None:
    """Install or update managed configuration sections."""
    from rich.prompt import Confirm

    from shell_configs.bootstrap import load_auto_update_config
    from shell_configs.display import (
        console,
        print_info,
        print_operation_result,
        print_warning,
    )
    from shell_configs.manager import ConfigManager, OperationResult
    from shell_configs.packages import get_package_manager, load_packages
    from shell_configs.shells.registry import ShellRegistry

    auto_update_config = load_auto_update_config()
    config_reader = ConfigReader(config_dir=config_dir)
    manager = ConfigManager(backup_retention=auto_update_config.backup_retention)
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(
        registry, shells, config_reader=config_reader
    )

    if not selected_shells:
        print_warning("No shells to install")
        return

    if not dry_run:
        pkg_manager = get_package_manager()
        if pkg_manager:
            try:
                packages = load_packages()
                required = [pkg for pkg in packages if pkg.required]
                missing_required = [
                    pkg for pkg in required if not pkg_manager.is_installed(pkg)
                ]

                if missing_required:
                    console.print(
                        f"[yellow]Installing {len(missing_required)} required package(s)...[/yellow]"
                    )
                    for pkg in missing_required:
                        console.print(f"  Installing {pkg.name}...")
                        success, message = pkg_manager.install(pkg, dry_run=False)
                        if success:
                            console.print(f"  [green]✓[/green] {pkg.name}")
                        else:
                            console.print(f"  [red]✗[/red] {pkg.name}: {message}")
                    console.print()
            except Exception as e:
                print_warning(f"Error installing required packages: {e}")

    has_diffs = False
    if not yes and not dry_run:
        has_diffs = _display_diffs_for_shells(selected_shells, config_reader, manager)

        if has_diffs:
            console.print()
            if not click.confirm("Apply these changes?"):
                print_info("Installation cancelled")
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

            result, message, diff_text = manager.install_section(
                config_file.path,
                content,
                dry_run=dry_run,
                shared_content=shared_content,
            )
            print_operation_result(result, message)
            if diff_text and result == OperationResult.UPDATED:
                from shell_configs.display import print_diff

                print_diff(diff_text)
            results[shell.name] = result

    for shell in selected_shells:
        additional_files = shell.get_additional_files()
        for additional_file in additional_files:
            if additional_file.comment_prefix:
                content = additional_file.source_path.read_text()
                result, message, diff_text = manager.install_section(
                    additional_file.target_path,
                    content,
                    dry_run=dry_run,
                    comment_prefix=additional_file.comment_prefix,
                )
            elif additional_file.base_source_path:
                merged_content = merge_json_files(
                    additional_file.base_source_path,
                    additional_file.source_path,
                )
                result, message, diff_text = (
                    manager.install_additional_file_from_content(
                        merged_content,
                        additional_file.target_path,
                        dry_run=dry_run,
                        backup_dir=additional_file.backup_dir,
                    )
                )
            else:
                result, message, diff_text = manager.install_additional_file(
                    additional_file.source_path,
                    additional_file.target_path,
                    dry_run=dry_run,
                    backup_dir=additional_file.backup_dir,
                )
            print_operation_result(result, message)
            if diff_text and result == OperationResult.UPDATED:
                from shell_configs.display import print_diff

                print_diff(diff_text)
            additional_file_results[str(additional_file.target_path)] = result

    preferences_results: dict[str, OperationResult] = {}
    for shell in selected_shells:
        preferences_files = shell.get_preferences_files()
        for pref_file in preferences_files:
            result, message, diff_text = manager.install_preferences_file(
                pref_file.source_path,
                pref_file.domain,
                dry_run=dry_run,
                app_name=pref_file.app_name,
            )
            print_operation_result(result, message)
            if diff_text and result == OperationResult.UPDATED:
                from shell_configs.display import print_diff

                print_diff(diff_text)
            preferences_results[pref_file.name] = result

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
    preferences_success_count = sum(
        1
        for r in preferences_results.values()
        if r in [OperationResult.CREATED, OperationResult.UPDATED]
    )
    total_success = success_count + additional_success_count + preferences_success_count

    if total_success > 0 and not dry_run:
        print_info(f"Successfully installed/updated {total_success} file(s)")
    elif not has_diffs and not dry_run:
        print_info("All configurations already in sync")

    if not dry_run:
        pkg_manager = get_package_manager()
        if pkg_manager:
            try:
                packages = load_packages()
                missing = [pkg for pkg in packages if not pkg_manager.is_installed(pkg)]

                if missing:
                    console.print()
                    console.print(
                        f"[yellow]⚠[/yellow] {len(missing)}/{len(packages)} packages missing"
                    )

                    if yes or Confirm.ask("Install missing packages?", default=True):
                        console.print()
                        total = len(missing)
                        for i, pkg in enumerate(missing, start=1):
                            console.print(
                                f"[dim][{i}/{total}] Installing {pkg.name}...[/dim]"
                            )
                            success, message = pkg_manager.install(pkg, dry_run=False)

                            if success:
                                console.print(f"[green]✓[/green] {pkg.name}")
                            else:
                                console.print(f"[red]✗[/red] {pkg.name}: {message}")

                            if i < total:
                                console.print()

                        console.print(
                            f"\n[green]✓[/green] Package installation complete ({total} packages)"
                        )
                    else:
                        print_info(
                            "Skipping package installation. Run 'shell-configs packages install' later."
                        )
                elif not has_diffs:
                    console.print()
                    console.print(
                        f"[green]✓[/green] All {len(packages)} packages already installed"
                    )
            except Exception as e:
                console.print(f"\n[red]Error checking packages:[/red] {e}")

        from shell_configs.signing import (
            generate_allowed_signers_file,
            validate_signing_setup,
        )

        console.print()
        console.print("[yellow]Validating SSH signing setup...[/yellow]")
        success, message = validate_signing_setup(auto_fix=False)
        if success:
            console.print(f"[green]✓[/green] {message}")
        elif "not registered" in message:
            console.print(f"[yellow]⚠[/yellow] {message}")
            if yes or Confirm.ask(
                "Register SSH key for commit signing with GitHub?", default=True
            ):
                success, message = validate_signing_setup(auto_fix=True)
                if success:
                    console.print(f"[green]✓[/green] {message}")
                else:
                    console.print(f"[red]✗[/red] {message}")
            else:
                console.print(
                    "[dim]Skipped. Run 'shell-configs signing --fix' later.[/dim]"
                )
        else:
            console.print(f"[yellow]⚠[/yellow] {message}")

        if success or "not registered" in message:
            allowed_signers_path = Path.home() / ".config" / "git" / "allowed_signers"
            signers_success, signers_msg = generate_allowed_signers_file(
                allowed_signers_path
            )
            if signers_success:
                console.print(f"[green]✓[/green] {signers_msg}")
            else:
                console.print(f"[yellow]⚠[/yellow] {signers_msg}")


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to uninstall",
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def uninstall(shells: list[str] | None, yes: bool) -> None:
    """Remove managed configuration sections."""
    from shell_configs.bootstrap import load_auto_update_config
    from shell_configs.display import print_info, print_operation_result, print_warning
    from shell_configs.manager import ConfigManager, OperationResult
    from shell_configs.shells.registry import ShellRegistry

    auto_update_config = load_auto_update_config()
    manager = ConfigManager(backup_retention=auto_update_config.backup_retention)
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(registry, shells, use_all=True)

    if not selected_shells:
        print_warning("No shells to uninstall")
        return

    if not yes:
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
            if additional_file.comment_prefix:
                result, message = manager.uninstall_section(
                    additional_file.target_path,
                    comment_prefix=additional_file.comment_prefix,
                )
            else:
                result, message = manager.uninstall_additional_file(
                    additional_file.target_path,
                    backup_dir=additional_file.backup_dir,
                )
            if result != OperationResult.NOT_FOUND:
                print_operation_result(result, message)
            additional_file_results[str(additional_file.target_path)] = result

    preferences_results: dict[str, OperationResult] = {}
    for shell in selected_shells:
        preferences_files = shell.get_preferences_files()
        for pref_file in preferences_files:
            result, message = manager.uninstall_preferences_file(
                pref_file.source_path,
                pref_file.domain,
                app_name=pref_file.app_name,
            )
            if result != OperationResult.NOT_FOUND:
                print_operation_result(result, message)
            preferences_results[pref_file.name] = result

    success_count = sum(1 for r in results.values() if r == OperationResult.REMOVED)
    additional_success_count = sum(
        1 for r in additional_file_results.values() if r == OperationResult.REMOVED
    )
    preferences_success_count = sum(
        1 for r in preferences_results.values() if r == OperationResult.REMOVED
    )
    total_success = success_count + additional_success_count + preferences_success_count

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
    from shell_configs.bootstrap import load_auto_update_config
    from shell_configs.display import (
        add_additional_file_row,
        add_status_row,
        console,
        create_status_table,
        get_status_indicator,
        print_warning,
    )
    from shell_configs.manager import ConfigManager
    from shell_configs.packages import get_package_manager, load_packages
    from shell_configs.platform import detect_platform
    from shell_configs.shells.registry import ShellRegistry

    auto_update_config = load_auto_update_config()
    config_reader = ConfigReader()
    manager = ConfigManager(backup_retention=auto_update_config.backup_retention)
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(
        registry, shells, config_reader=config_reader
    )

    if not selected_shells:
        print_warning("No shell configurations found")
        return

    console.print(f"[bold]Platform:[/bold] {detect_platform().display_name}\n")

    table = create_status_table()
    home = str(Path.home())

    for shell in selected_shells:
        has_shown_name = False

        for config_file in shell.get_config_files():
            repo_content = config_reader.get_config_content(
                shell.name, config_file.repo_config_name
            )
            shared_content = None
            if shell.supports_shared_config():
                shared_content = config_reader.get_shared_config_content(shell.name)

            if repo_content is None and shared_content is not None:
                repo_content = ""
            elif repo_content is None:
                continue

            repo_content = manager.combine_content(shared_content, repo_content)

            section = manager.extract_managed_section(config_file.path)
            exists = section is not None
            synced = (
                (exists and section.content.strip() == repo_content.strip())
                if section
                else False
            )

            status_str = get_status_indicator(synced, exists)
            path_display = str(config_file.path).replace(home, "~")
            add_status_row(table, shell.display_name, path_display, status_str)
            has_shown_name = True

        additional_files = shell.get_additional_files()
        for i, additional_file in enumerate(additional_files):
            if additional_file.comment_prefix:
                source_content = (
                    additional_file.source_path.read_text()
                    if additional_file.source_path.exists()
                    else None
                )
                section = manager.extract_managed_section(
                    additional_file.target_path,
                    comment_prefix=additional_file.comment_prefix,
                )
                exists = section is not None
                synced = (
                    manager.managed_content_matches(section.content, source_content)
                    if section and source_content
                    else False
                )
            else:
                exists = additional_file.target_path.exists()
                if additional_file.base_source_path:
                    merged_content = merge_json_files(
                        additional_file.base_source_path,
                        additional_file.source_path,
                    )
                    synced = manager.content_matches(
                        merged_content, additional_file.target_path
                    )
                else:
                    synced = manager.files_match(
                        additional_file.source_path, additional_file.target_path
                    )
            status_str = get_status_indicator(synced, exists)
            path_display = str(additional_file.target_path).replace(home, "~")

            if i == 0 and not has_shown_name:
                add_status_row(table, shell.display_name, path_display, status_str)
                has_shown_name = True
            else:
                add_additional_file_row(table, path_display, status_str)

        preferences_files = shell.get_preferences_files()
        for i, pref_file in enumerate(preferences_files):
            exists, synced = manager.check_preferences_file_status(
                pref_file.source_path, pref_file.domain
            )
            status_str = get_status_indicator(synced, exists)
            path_display = f"{pref_file.domain} (preferences)"

            if i == 0 and not has_shown_name:
                add_status_row(table, shell.display_name, path_display, status_str)
                has_shown_name = True
            else:
                add_additional_file_row(table, path_display, status_str)

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

    console.print("[bold cyan]Packages[/bold cyan]\n")

    pkg_manager = get_package_manager()
    if pkg_manager:
        try:
            packages = load_packages()
            installed = []
            missing = []
            for pkg in packages:
                if pkg_manager.is_installed(pkg):
                    installed.append(pkg)
                else:
                    missing.append(pkg)

            if not missing:
                console.print(
                    f"  [green]✓[/green] {len(installed)}/{len(packages)} packages installed ({pkg_manager.display_name})"
                )
            else:
                console.print(
                    f"  [yellow]⚠[/yellow] {len(installed)}/{len(packages)} packages installed ({pkg_manager.display_name})"
                )
                console.print(
                    "  [dim]Run 'shell-configs packages status' for details[/dim]"
                )
        except Exception as e:
            console.print(f"  [red]✗[/red] Error checking packages: {e}")
    else:
        console.print("  [dim]No package manager available[/dim]")

    console.print()

    console.print("[bold cyan]SSH Signing[/bold cyan]\n")

    from shell_configs.signing import validate_signing_setup

    success, message = validate_signing_setup(auto_fix=False)
    if success:
        console.print(f"  [green]✓[/green] {message}")
    else:
        console.print(f"  [yellow]⚠[/yellow] {message}")

    console.print()


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to diff",
)
def diff(shells: list[str] | None) -> None:
    """Show differences between repository and installed configurations."""
    from shell_configs.bootstrap import load_auto_update_config
    from shell_configs.display import print_info, print_warning
    from shell_configs.manager import ConfigManager
    from shell_configs.shells.registry import ShellRegistry

    auto_update_config = load_auto_update_config()
    config_reader = ConfigReader()
    manager = ConfigManager(backup_retention=auto_update_config.backup_retention)
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
    from shell_configs.display import (
        add_validation_row,
        console,
        create_validation_table,
        print_error,
        print_info,
        print_warning,
    )
    from shell_configs.shells.registry import ShellRegistry

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
    from shell_configs.display import console, print_warning
    from shell_configs.shells.registry import ShellRegistry

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
@click.option(
    "--fix",
    is_flag=True,
    help="Auto-register SSH key if not registered for signing",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed key information")
def signing(fix: bool, verbose: bool) -> None:
    """Validate SSH signing key is registered with GitHub."""
    from shell_configs.display import console
    from shell_configs.signing import get_signing_key_info, validate_signing_setup

    success, message = validate_signing_setup(auto_fix=fix)
    if success:
        console.print(f"[green]✓[/green] {message}")

        if verbose:
            info = get_signing_key_info()
            if info:
                console.print()
                console.print("[bold cyan]Signing Key Details[/bold cyan]")
                console.print(f"  Key type:      {info['key_type']}")
                console.print(f"  Fingerprint:   {info['fingerprint']}")
                console.print(f"  GitHub title:  {info['github_title'] or 'N/A'}")
                console.print(f"  Git name:      {info['git_name']}")
                console.print(f"  Git email:     {info['git_email']}")
                if info["comment"]:
                    console.print(f"  Key comment:   {info['comment']}")
    else:
        console.print(f"[red]✗[/red] {message}")
        sys.exit(1)


@cli.command()
@click.option(
    "--dry-run", is_flag=True, help="Show what would be deleted without deleting"
)
@click.option("--keep", type=int, help="Number of backups to keep per config file")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def cleanup(dry_run: bool, keep: int | None, yes: bool) -> None:
    """Clean up old backup files created by shell-configs."""
    from collections import defaultdict

    from rich.prompt import Confirm
    from rich.table import Table

    from shell_configs.bootstrap import load_auto_update_config
    from shell_configs.display import console, print_info
    from shell_configs.manager import ConfigManager
    from shell_configs.shells.registry import ShellRegistry

    config = load_auto_update_config()
    retention = keep if keep is not None else config.backup_retention

    manager = ConfigManager(backup_retention=config.backup_retention)
    registry = ShellRegistry()
    all_shells = registry.get_all()

    console.print("[cyan]Scanning for shell-configs backup files...[/cyan]\n")

    backup_by_config = defaultdict(list)
    backup_dir_map: dict[Path, Path] = {}

    for shell in all_shells:
        for config_file in shell.get_config_files():
            if config_file.path.exists():
                backups = manager.find_backup_files(config_file.path)
                if backups:
                    backup_by_config[config_file.path].extend(backups)

        for additional_file in shell.get_additional_files():
            should_scan = (
                additional_file.target_path.exists() or additional_file.backup_dir
            )
            if should_scan:
                backups = manager.find_backup_files(
                    additional_file.target_path,
                    backup_dir=additional_file.backup_dir,
                )
                if backups:
                    backup_by_config[additional_file.target_path].extend(backups)
                    if additional_file.backup_dir:
                        backup_dir_map[additional_file.target_path] = (
                            additional_file.backup_dir
                        )

    if not backup_by_config:
        print_info("No backup files found")
        return

    total_backups = sum(len(backups) for backups in backup_by_config.values())
    to_keep_count = 0
    to_remove_count = 0

    table = Table(show_header=True, header_style="bold")
    table.add_column("Config File", style="cyan")
    table.add_column("Backup File", style="white")
    table.add_column("Action", style="white")

    home = str(Path.home())

    for config_path in sorted(backup_by_config.keys()):
        backups = sorted(backup_by_config[config_path], reverse=True)
        config_display = str(config_path).replace(home, "~")

        for i, backup in enumerate(backups):
            action = "keep" if i < retention else "remove"
            if action == "keep":
                to_keep_count += 1
                action_display = "[green]keep[/green]"
            else:
                to_remove_count += 1
                action_display = "[yellow]remove[/yellow]"

            backup_display = backup.name
            table.add_row(
                config_display if i == 0 else "", backup_display, action_display
            )

    console.print(table)
    console.print()

    if to_remove_count == 0:
        print_info(
            f"All {total_backups} backup files are within retention ({retention})"
        )
        return

    console.print(
        f"Found {total_backups} backup files: "
        f"[green]{to_keep_count} to keep[/green], "
        f"[yellow]{to_remove_count} to remove[/yellow]"
    )
    console.print()

    if dry_run:
        print_info(f"Dry run: would remove {to_remove_count} backup files")
        return

    if not yes:
        if not Confirm.ask(f"Remove {to_remove_count} old backup files?", default=True):
            print_info("Cleanup cancelled")
            return

    removed_count = 0
    for config_path in backup_by_config:
        removed = manager.cleanup_old_backups(
            config_path,
            keep=retention,
            backup_dir=backup_dir_map.get(config_path),
        )
        removed_count += len(removed)

    console.print(
        f"[green]✓[/green] Removed {removed_count} backup files "
        f"(kept {retention} most recent per config)"
    )


@cli.command()
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
    from rich.prompt import Confirm

    from shell_configs.bootstrap import (
        UPDATABLE_TOOLS,
        check_tool_updates,
        perform_github_update,
    )
    from shell_configs.bootstrap.installer import GITHUB_REPO_URL
    from shell_configs.display import console

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
            console.print("\nRun [bold]shell-configs upgrade[/bold] to install")
        return

    if not force and not yes:
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
        # Run install in a new process so the upgraded code handles it.
        # ctx.invoke would use stale in-memory modules from the pre-upgrade
        # version, which may be incompatible with the new on-disk config files.
        import shutil

        shell_configs_bin = shutil.which("shell-configs")
        if shell_configs_bin:
            subprocess.run([shell_configs_bin, "install", "--yes"])
        else:
            ctx.invoke(install, yes=True)


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
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated shells to install",
)
@click.option("--skip-completions", is_flag=True, help="Skip shell completion setup")
@click.option("--skip-packages", is_flag=True, help="Skip package installation")
@click.pass_context
def setup(
    ctx: click.Context,
    yes: bool,
    dry_run: bool,
    shells: list[str] | None,
    skip_completions: bool,
    skip_packages: bool,
) -> None:
    """One-command setup for shell-configs.

    Installs shell-configs globally via uv tool install, sets up shell
    configurations, and optionally installs tab completions.

    Run this after installing with uvx: uvx shell-configs setup
    """
    from rich.prompt import Confirm

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
    from shell_configs.display import console

    if not skip_packages:
        console.print("\n[bold cyan]Step 1/4: Install required packages[/bold cyan]")
        console.print(
            "[dim]Installing system packages needed by shell configurations.[/dim]\n"
        )
        ctx.invoke(packages_install, dry_run=dry_run, yes=yes)

    console.print(
        "\n[bold cyan]Step 2/4: Install shell-configs system-wide[/bold cyan]"
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
                    if not yes and not Confirm.ask(
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
        if not yes and not dry_run:
            if not Confirm.ask("Install shell-configs permanently?", default=True):
                console.print("[yellow]Setup cancelled[/yellow]")
                sys.exit(0)

        success, message = install_tool(force=yes, dry_run=dry_run)

        if not success:
            console.print(f"[red]Error:[/red] {message}")
            sys.exit(1)

        console.print(f"[green]✓[/green] {message}")
        tool_install_success = True

    if not tool_install_success:
        sys.exit(1)

    # Check if ~/.local/bin is in PATH
    if not dry_run:
        import os

        local_bin = os.path.expanduser("~/.local/bin")
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        if local_bin not in path_dirs:
            console.print(
                f"\n[yellow]⚠[/yellow] {local_bin} is not in your PATH. "
                "Add it to use shell-configs from anywhere:"
            )
            console.print('  export PATH="$HOME/.local/bin:$PATH"\n')

    config_dir = get_tool_config_dir("shell-configs") if not dry_run else None

    console.print(
        "\n[bold cyan]Step 3/4: Installing shell configurations[/bold cyan]\n"
    )

    ctx.invoke(
        install,
        shells=shells,
        dry_run=dry_run,
        yes=yes,
        config_dir=config_dir,
    )

    if not skip_completions:
        console.print("\n[bold cyan]Step 4/4: Shell completion setup[/bold cyan]\n")

        shell = detect_shell()
        if shell is None:
            supported = ", ".join(get_supported_shells())
            console.print(
                f"[yellow]⚠[/yellow] Could not detect shell. Supported: {supported}"
            )
            console.print("[dim]Skipping completion installation[/dim]")
        else:
            if not yes and not dry_run:
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
def packages() -> None:
    """Manage system packages required by shell-configs."""
    pass


@packages.command(name="install")
@click.option("--dry-run", is_flag=True, help="Show what would be installed")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def packages_install(dry_run: bool, yes: bool) -> None:
    """Install required system packages."""
    from rich.prompt import Confirm

    from shell_configs.display import console, print_error, print_info
    from shell_configs.packages import (
        get_package_manager,
        load_packages,
        sort_packages_for_install,
    )
    from shell_configs.platform import detect_platform

    platform_name = detect_platform().display_name
    console.print(f"[dim]Platform:[/dim] {platform_name}")

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available for this platform")
        print_info("Install Homebrew: https://brew.sh (macOS) or use apt (Linux/WSL)")
        sys.exit(1)

    console.print(f"[dim]Package manager:[/dim] {manager.display_name}\n")

    try:
        packages = load_packages()
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    if not packages:
        print_info("No packages to install for this platform")
        return

    to_install = []
    already_installed = []

    for pkg in packages:
        if manager.is_installed(pkg):
            already_installed.append(pkg)
        else:
            to_install.append(pkg)

    to_install = sort_packages_for_install(to_install)

    if already_installed:
        console.print(f"[green]Already installed ({len(already_installed)}):[/green]")
        for pkg in already_installed:
            console.print(f"  [dim]{pkg.name}[/dim]")

    if not to_install:
        console.print("\n[green]✓[/green] All required packages are already installed")
        return

    console.print(f"\n[cyan]Packages to install ({len(to_install)}):[/cyan]")
    for pkg in to_install:
        desc = f" - {pkg.description}" if pkg.description else ""
        console.print(f"  {pkg.name}{desc}")

    if not yes and not dry_run:
        if not Confirm.ask("\nInstall these packages?", default=True):
            print_info("Installation cancelled")
            return

    console.print()
    total = len(to_install)
    for i, pkg in enumerate(to_install, start=1):
        if not dry_run:
            console.print(f"[dim][{i}/{total}] Installing {pkg.name}...[/dim]")

        success, message = manager.install(pkg, dry_run=dry_run)

        if success:
            if "already installed" in message:
                console.print(
                    f"[green]✓[/green] {pkg.name} [dim](already installed)[/dim]"
                )
            elif dry_run:
                console.print(f"[dim]  Would install {pkg.name}[/dim]")
            else:
                console.print(f"[green]✓[/green] {pkg.name}")
        else:
            console.print(f"[red]✗[/red] {pkg.name}: {message}")

        if not dry_run and i < total:
            console.print()

    if dry_run:
        print_info("\nDry run complete. Use without --dry-run to install.")
    else:
        console.print(
            f"\n[green]✓[/green] Package installation complete ({total} packages)"
        )


@packages.command(name="status")
def packages_status() -> None:
    """Show status of required packages."""
    from shell_configs.display import console, print_error, print_info
    from shell_configs.packages import get_package_manager, load_packages
    from shell_configs.platform import detect_platform

    platform_name = detect_platform().display_name
    console.print(f"[dim]Platform:[/dim] {platform_name}\n")

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available")
        return

    console.print(f"[dim]Package manager:[/dim] {manager.display_name}\n")

    try:
        packages = load_packages()
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    if not packages:
        print_info("No packages configured for this platform")
        return

    installed = []
    missing = []

    for pkg in packages:
        if manager.is_installed(pkg):
            installed.append(pkg)
        else:
            missing.append(pkg)

    if installed:
        console.print(f"[green]Installed ({len(installed)}):[/green]")
        for pkg in installed:
            console.print(f"  [green]✓[/green] {pkg.name}")

    if missing:
        console.print(f"\n[yellow]Missing ({len(missing)}):[/yellow]")
        for pkg in missing:
            console.print(f"  [yellow]✗[/yellow] {pkg.name}")
        console.print(
            "\n[dim]Run 'shell-configs packages install' to install missing packages[/dim]"
        )
    else:
        console.print("\n[green]✓[/green] All required packages are installed")


@packages.command(name="uninstall")
@click.option("--dry-run", is_flag=True, help="Show what would be uninstalled")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
def packages_uninstall(dry_run: bool, yes: bool) -> None:
    """Uninstall managed system packages."""
    from rich.prompt import Confirm

    from shell_configs.display import console, print_error, print_info
    from shell_configs.packages import (
        get_package_manager,
        load_packages,
        sort_packages_for_uninstall,
    )
    from shell_configs.platform import detect_platform

    platform_name = detect_platform().display_name
    console.print(f"[dim]Platform:[/dim] {platform_name}")

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available for this platform")
        sys.exit(1)

    console.print(f"[dim]Package manager:[/dim] {manager.display_name}\n")

    try:
        packages = load_packages()
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    if not packages:
        print_info("No packages configured for this platform")
        return

    to_uninstall = []
    managed_externally = []
    not_installed = []

    for pkg in packages:
        if manager.can_uninstall(pkg):
            to_uninstall.append(pkg)
        elif manager.is_installed(pkg):
            managed_externally.append(pkg)
        else:
            not_installed.append(pkg)

    to_uninstall = sort_packages_for_uninstall(to_uninstall)

    if managed_externally:
        console.print(f"[dim]Managed externally ({len(managed_externally)}):[/dim]")
        for pkg in managed_externally:
            console.print(f"  [dim]{pkg.name} (not via {manager.display_name})[/dim]")

    if not_installed:
        console.print(f"[dim]Not installed ({len(not_installed)}):[/dim]")
        for pkg in not_installed:
            console.print(f"  [dim]{pkg.name}[/dim]")

    if not to_uninstall:
        console.print("\n[green]✓[/green] No packages to uninstall")
        return

    console.print(f"\n[cyan]Packages to uninstall ({len(to_uninstall)}):[/cyan]")
    for pkg in to_uninstall:
        desc = f" - {pkg.description}" if pkg.description else ""
        console.print(f"  {pkg.name}{desc}")

    if not yes and not dry_run:
        if not Confirm.ask("\nUninstall these packages?", default=False):
            print_info("Uninstall cancelled")
            return

    console.print()
    total = len(to_uninstall)
    success_count = 0
    fail_count = 0

    for i, pkg in enumerate(to_uninstall, start=1):
        if not dry_run:
            console.print(f"[dim][{i}/{total}] Uninstalling {pkg.name}...[/dim]")

        success, message = manager.uninstall(pkg, dry_run=dry_run)

        if success:
            if "not installed" in message or "skipping" in message:
                console.print(f"[dim]  {pkg.name} ({message})[/dim]")
            elif dry_run:
                console.print(f"[dim]  Would uninstall {pkg.name}[/dim]")
            else:
                console.print(f"[green]✓[/green] {pkg.name}")
                success_count += 1
        else:
            console.print(f"[red]✗[/red] {pkg.name}: {message}")
            fail_count += 1

        if not dry_run and i < total:
            console.print()

    if dry_run:
        print_info("\nDry run complete. Use without --dry-run to uninstall.")
    else:
        if fail_count > 0:
            console.print(
                f"\n[yellow]⚠[/yellow] {success_count} uninstalled, {fail_count} failed"
            )
        else:
            console.print(
                f"\n[green]✓[/green] Package uninstall complete ({success_count} packages)"
            )


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
    from shell_configs.display import console

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
    from shell_configs.display import console

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
    from shell_configs.display import console

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
    from shell_configs.display import console

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
    from rich.table import Table

    from shell_configs.completions import (
        detect_shell,
        find_config_file,
        get_supported_shells,
        is_completion_installed,
    )
    from shell_configs.display import console

    detected_shell = detect_shell()
    console.print("[bold cyan]Shell Completions Status[/bold cyan]\n")

    if detected_shell:
        console.print(f"Detected shell: [cyan]{detected_shell}[/cyan]\n")
    else:
        console.print("[yellow]No supported shell detected[/yellow]\n")

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
