"""Shared Click option decorators for commands and groups."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import click

from shell_configs.cli.helpers import parse_shell_filter

_Decorator = Callable[[Callable[..., Any]], Callable[..., Any]]

profile_option: _Decorator = click.option(
    "--profile", "profile_name", default=None, help="Profile to use"
)

yes_option: _Decorator = click.option(
    "-y", "--yes", is_flag=True, help="Auto-confirm without prompting"
)


def shells_option(help: str) -> _Decorator:
    """--shells filter option; help text varies per command."""
    return click.option("--shells", callback=parse_shell_filter, help=help)


def dry_run_option(help: str) -> _Decorator:
    """--dry-run flag; help text varies per command."""
    return click.option("--dry-run", is_flag=True, help=help)
