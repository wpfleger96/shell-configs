"""Command-line interface for shell-configs."""

import difflib
import sys

import click
from rich.syntax import Syntax

from shell_configs.config import ConfigReader, find_repo_root
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
from shell_configs.shells.registry import ShellRegistry


def parse_shell_filter(ctx, param, value):
    """Parse shell filter from comma-separated string."""
    if not value:
        return None
    return [s.strip() for s in value.split(",")]


def _get_selected_shells(registry, shells_filter=None, config_reader=None, use_all=False):
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


@click.group()
@click.version_option()
def cli():
    """Manage shell configuration files across machines."""


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to install (e.g., bash,zsh,git)",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
def install(shells, dry_run, force):
    """Install or update managed configuration sections."""
    repo_root = find_repo_root()
    if not repo_root:
        print_error("Not in a shell-configs repository. Run from the repository directory.")
        sys.exit(1)

    config_reader = ConfigReader(repo_root)
    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(registry, shells, config_reader=config_reader)

    if not selected_shells:
        print_warning("No shells to install")
        return

    if not force and not dry_run:
        shell_names = ", ".join([s.display_name for s in selected_shells])
        if not click.confirm(f"Install configurations for {shell_names}?"):
            print_info("Installation cancelled")
            return

    results = {}
    additional_file_results = {}

    for shell in selected_shells:
        for config_file in shell.get_config_files():
            if config_file.repo_config_name is None:
                content = None
            else:
                content = config_reader.get_config_content(shell.name, config_file.repo_config_name)
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
                config_file.path, content, dry_run=dry_run, shared_content=shared_content
            )
            print_operation_result(result, message)
            results[shell.name] = result

    for shell in selected_shells:
        additional_files = shell.get_additional_files(repo_root)
        for additional_file in additional_files:
            result, message = manager.install_additional_file(
                additional_file.source_path, additional_file.target_path, dry_run=dry_run
            )
            print_operation_result(result, message)
            additional_file_results[str(additional_file.target_path)] = result

    if dry_run:
        print_info("Dry run complete. Use without --dry-run to apply changes.")

    success_count = sum(
        1 for r in results.values() if r in [OperationResult.CREATED, OperationResult.UPDATED]
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
def uninstall(shells, force):
    """Remove managed configuration sections."""
    repo_root = find_repo_root()
    if not repo_root:
        print_error("Not in a shell-configs repository. Run from the repository directory.")
        sys.exit(1)

    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(registry, shells, use_all=True)

    if not selected_shells:
        print_warning("No shells to uninstall")
        return

    if not force:
        shell_names = ", ".join([s.display_name for s in selected_shells])
        if not click.confirm(f"Remove managed sections from {shell_names} configurations?"):
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
        additional_files = shell.get_additional_files(repo_root)
        for additional_file in additional_files:
            result, message = manager.uninstall_additional_file(additional_file.target_path)
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
def status(shells):
    """Show the status of managed configurations."""
    repo_root = find_repo_root()
    if not repo_root:
        print_error("Not in a shell-configs repository. Run from the repository directory.")
        sys.exit(1)

    config_reader = ConfigReader(repo_root)
    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(registry, shells, config_reader=config_reader)

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
                (exists and section.content.strip() == repo_content.strip()) if section else False
            )

            status_str = get_status_indicator(synced, exists)
            add_status_row(table, shell.display_name, config_file.path, status_str)

        additional_files = shell.get_additional_files(repo_root)
        for additional_file in additional_files:
            exists = additional_file.target_path.exists()
            synced = manager.files_match(additional_file.source_path, additional_file.target_path)
            status_str = get_status_indicator(synced, exists)
            add_additional_file_row(table, additional_file.target_path, status_str)

    console.print(table)


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to diff",
)
def diff(shells):
    """Show differences between repository and installed configurations."""
    repo_root = find_repo_root()
    if not repo_root:
        print_error("Not in a shell-configs repository. Run from the repository directory.")
        sys.exit(1)

    config_reader = ConfigReader(repo_root)
    manager = ConfigManager()
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(registry, shells, config_reader=config_reader)

    if not selected_shells:
        print_warning("No shell configurations found")
        return

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
                console.print(f"\n[bold cyan]{shell.display_name}[/bold cyan]: {config_file.path}")
                console.print("[yellow]Not installed[/yellow]")
                found_diffs = True
                continue

            if section.content.strip() == repo_content.strip():
                continue

            found_diffs = True
            console.print(f"\n[bold cyan]{shell.display_name}[/bold cyan]: {config_file.path}")

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

        additional_files = shell.get_additional_files(repo_root)
        for additional_file in additional_files:
            if not additional_file.target_path.exists():
                console.print(
                    f"\n[bold cyan]{shell.display_name}[/bold cyan]: {additional_file.target_path}"
                )
                console.print("[yellow]Not installed[/yellow]")
                found_diffs = True
                continue

            if manager.files_match(additional_file.source_path, additional_file.target_path):
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

    if not found_diffs:
        print_info("All configurations are in sync")


@cli.command()
@click.option(
    "--shells",
    callback=parse_shell_filter,
    help="Comma-separated list of shells to validate",
)
def validate(shells):
    """Validate configuration file syntax."""
    repo_root = find_repo_root()
    if not repo_root:
        print_error("Not in a shell-configs repository. Run from the repository directory.")
        sys.exit(1)

    config_reader = ConfigReader(repo_root)
    registry = ShellRegistry()

    selected_shells = _get_selected_shells(registry, shells, config_reader=config_reader)

    if not selected_shells:
        print_warning("No shell configurations found")
        return

    table = create_validation_table()
    all_valid = True

    for shell in selected_shells:
        for config_file in shell.get_config_files():
            content = config_reader.get_config_content(shell.name, config_file.repo_config_name)
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
def list_shells():
    """List all available shell configurations."""
    repo_root = find_repo_root()

    registry = ShellRegistry()
    all_shells = registry.get_all()

    if repo_root:
        config_reader = ConfigReader(repo_root)
        available = config_reader.get_available_shells()
    else:
        available = []

    console.print("[bold]Available Shells:[/bold]")
    for shell in all_shells:
        has_config = shell.name in available
        status = "[green]✓[/green]" if has_config else "[dim]○[/dim]"
        console.print(f"  {status} {shell.display_name} ({shell.name})")

    if not repo_root:
        print_info("Not in a shell-configs repository. Showing all registered shells.")
    elif not available:
        print_warning(
            "No shell configurations found in repository. "
            "Add config files to the config/ directory."
        )


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
