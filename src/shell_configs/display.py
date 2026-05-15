"""Display utilities using Rich."""

from __future__ import annotations

import contextvars

from typing import Any

from rich.console import Console
from rich.table import Table

from shell_configs.manager import OperationResult

_console_override: contextvars.ContextVar[Console | None] = contextvars.ContextVar(
    "_console_override", default=None
)

_real_console = Console()


class _ConsoleProxy:
    """Proxy that routes console calls through a ContextVar override.

    Components import ``console`` from this module and call ``console.print()``.
    When ``_console_override`` is set (e.g. by a worker thread), all calls are
    routed to that override console (typically backed by a StringIO buffer).
    Otherwise they fall through to ``_real_console``.
    """

    def __init__(self, real: Console) -> None:
        self._real = real

    def _active(self) -> Console:
        return _console_override.get() or self._real

    def print(self, *args: Any, **kwargs: Any) -> None:
        self._active().print(*args, **kwargs)

    def print_exception(self, *args: Any, **kwargs: Any) -> None:
        self._active().print_exception(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._active(), name)


console: Any = _ConsoleProxy(_real_console)


def get_console() -> Console:
    """Return the active console for the current execution context."""
    return _console_override.get() or _real_console


def print_warning(message: str, *, indent: int = 0) -> None:
    """Print a warning message."""
    get_console().print(f"{' ' * indent}[yellow]⚠[/yellow] {message}")


def print_error(message: str, *, indent: int = 0) -> None:
    """Print an error message."""
    get_console().print(f"{' ' * indent}[red]✗[/red] {message}")


def print_info(message: str, *, indent: int = 0) -> None:
    """Print an info message."""
    get_console().print(f"{' ' * indent}[blue]ℹ[/blue] {message}")


def print_hint(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}[yellow]💡[/yellow] {message}")


def print_operation_result(result: OperationResult, message: str) -> None:
    """Print an operation result with appropriate formatting."""
    cons = get_console()
    if result in (
        OperationResult.CREATED,
        OperationResult.UPDATED,
        OperationResult.REMOVED,
    ):
        cons.print(f"[green]✓[/green] {message}")
    elif result == OperationResult.ALREADY_SYNCED:
        cons.print(f"[dim]•[/dim] {message}")
    elif result == OperationResult.NOT_FOUND:
        print_warning(message)
    elif result == OperationResult.ERROR:
        print_error(message)


def create_status_table() -> Table:
    """Create a status table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Config", style="cyan", no_wrap=True)
    table.add_column("File", style="white")
    table.add_column("Status", style="white", no_wrap=True)
    return table


def add_status_row(
    table: Table, shell_name: str, config_file: str, status: str
) -> None:
    """Add a row to a status table."""
    table.add_row(shell_name, config_file, status)


def add_additional_file_row(table: Table, file_path: str, status: str) -> None:
    """Add a row for an additional file to a status table."""
    table.add_row("", file_path, status)


def get_status_indicator(synced: bool, exists: bool) -> str:
    """Get a status indicator string."""
    if not exists:
        return "[red]✗ Not installed[/red]"
    if synced:
        return "[green]✓ Synced[/green]"
    return "[yellow]⚠ Outdated[/yellow]"


def create_validation_table() -> Table:
    """Create a validation results table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Shell", style="cyan", no_wrap=True)
    table.add_column("Valid", style="white", no_wrap=True)
    table.add_column("Message", style="white")
    return table


def add_validation_row(
    table: Table, shell_name: str, valid: bool, message: str
) -> None:
    """Add a row to a validation table."""
    status = "[green]✓[/green]" if valid else "[red]✗[/red]"
    table.add_row(shell_name, status, message if message else "-")


def print_diff(diff_text: str | None) -> None:
    """Print a unified diff with syntax highlighting."""
    if not diff_text or not diff_text.strip():
        return

    from rich.syntax import Syntax

    syntax = Syntax(diff_text, "diff", theme="monokai")
    get_console().print(syntax)
