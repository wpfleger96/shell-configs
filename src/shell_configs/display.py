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


# ─── Icon constants ──────────────────────────────────────────────────────────

ICON_SUCCESS = "[green]✓[/green]"
ICON_DONE = "[dim]✓[/dim]"
ICON_UNCHANGED = "[dim]•[/dim]"
ICON_SKIPPED = "[dim]○[/dim]"
ICON_ABSENT = "[yellow]○[/yellow]"
ICON_UPDATE = "[yellow]↻[/yellow]"
ICON_ERROR = "[red]✗[/red]"
ICON_WARNING = "[yellow]⚠[/yellow]"
ICON_INFO = "[blue]ℹ[/blue]"
ICON_HINT = "[yellow]💡[/yellow]"
ICON_WOULD = "[dim]→[/dim]"
ICON_ADD = "[green]+[/green]"
ICON_NONE = "[dim]-[/dim]"


# ─── Markup builder ──────────────────────────────────────────────────────────


def dim(text: str) -> str:
    return f"[dim]{text}[/dim]"


# ─── Print helpers ───────────────────────────────────────────────────────────


def print_error(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_ERROR} {message}")


def print_warning(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_WARNING} {message}")


def print_info(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_INFO} {message}")


def print_hint(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_HINT} {message}")


def print_success(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_SUCCESS} {message}")


def print_done(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_DONE} {message}")


def print_unchanged(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_UNCHANGED} {message}")


def print_skipped(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_SKIPPED} {message}")


def print_absent(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_ABSENT} {message}")


def print_update(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_UPDATE} {message}")


def print_would(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_WOULD} {message}")


def print_add(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{ICON_ADD} {message}")


def print_progress(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}[yellow]{message}[/yellow]")


def print_dim(message: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{dim(message)}")


def print_label(key: str, value: str, *, indent: int = 0) -> None:
    get_console().print(f"{' ' * indent}{dim(key + ':')} {value}")


# ─── Shell-configs-specific helpers ──────────────────────────────────────────


def print_operation_result(result: OperationResult, message: str) -> None:
    """Print an operation result with appropriate formatting."""
    if result in (
        OperationResult.CREATED,
        OperationResult.UPDATED,
        OperationResult.REMOVED,
    ):
        print_success(message)
    elif result == OperationResult.ALREADY_SYNCED:
        print_unchanged(message)
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
        return f"{ICON_ERROR} Not installed"
    if synced:
        return f"{ICON_SUCCESS} Synced"
    return f"{ICON_WARNING} Outdated"


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
    status = ICON_SUCCESS if valid else ICON_ERROR
    table.add_row(shell_name, status, message if message else "-")


def print_diff(diff_text: str | None) -> None:
    """Print a unified diff with syntax highlighting."""
    if not diff_text or not diff_text.strip():
        return

    from rich.syntax import Syntax

    syntax = Syntax(diff_text, "diff", theme="monokai")
    get_console().print(syntax)
