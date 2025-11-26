"""Display utilities using Rich."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from shell_configs.manager import OperationResult

console = Console()


def print_warning(message: str) -> None:
    """Print a warning message.

    Args:
        message: Message to print
    """
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_error(message: str) -> None:
    """Print an error message.

    Args:
        message: Message to print
    """
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print an info message.

    Args:
        message: Message to print
    """
    console.print(f"[blue]ℹ[/blue] {message}")


def print_operation_result(result: OperationResult, message: str) -> None:
    """Print an operation result with appropriate formatting.

    Args:
        result: Operation result
        message: Message to print
    """
    if result in (
        OperationResult.CREATED,
        OperationResult.UPDATED,
        OperationResult.REMOVED,
    ):
        console.print(f"[green]✓[/green] {message}")
    elif result == OperationResult.ALREADY_SYNCED:
        console.print(f"[dim]•[/dim] {message}")
    elif result == OperationResult.NOT_FOUND:
        print_warning(message)
    elif result == OperationResult.ERROR:
        print_error(message)


def create_status_table() -> Table:
    """Create a status table.

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold")
    table.add_column("Shell", style="cyan", no_wrap=True)
    table.add_column("Config File", style="white")
    table.add_column("Status", style="white")
    return table


def add_status_row(
    table: Table, shell_name: str, config_file: Path, status: str
) -> None:
    """Add a row to a status table.

    Args:
        table: Table to add row to
        shell_name: Name of the shell
        config_file: Path to the config file
        status: Status string
    """
    table.add_row(shell_name, str(config_file), status)


def add_additional_file_row(table: Table, file_path: Path, status: str) -> None:
    """Add a row for an additional file to a status table.

    Args:
        table: Table to add row to
        file_path: Path to the additional file
        status: Status string
    """
    table.add_row("", f"  └─ {file_path}", status)


def get_status_indicator(synced: bool, exists: bool) -> str:
    """Get a status indicator string.

    Args:
        synced: Whether the config is synced
        exists: Whether the managed section exists

    Returns:
        Formatted status string
    """
    if not exists:
        return "[red]✗ Not installed[/red]"
    if synced:
        return "[green]✓ Synced[/green]"
    return "[yellow]⚠ Outdated[/yellow]"


def create_validation_table() -> Table:
    """Create a validation results table.

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold")
    table.add_column("Shell", style="cyan", no_wrap=True)
    table.add_column("Valid", style="white", no_wrap=True)
    table.add_column("Message", style="white")
    return table


def add_validation_row(
    table: Table, shell_name: str, valid: bool, message: str
) -> None:
    """Add a row to a validation table.

    Args:
        table: Table to add row to
        shell_name: Name of the shell
        valid: Whether validation passed
        message: Validation message
    """
    status = "[green]✓[/green]" if valid else "[red]✗[/red]"
    table.add_row(shell_name, status, message if message else "-")
