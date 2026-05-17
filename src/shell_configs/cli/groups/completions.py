"""Completions subcommand group."""

from __future__ import annotations

import sys

import click

from shell_configs.completions import get_supported_shells

_SUPPORTED_SHELLS = list(get_supported_shells())


@click.group()
def completions() -> None:
    """Manage shell tab completion."""
    pass


@completions.command(name="bash")
def completions_bash() -> None:
    """Output bash completion script for manual installation."""
    from shell_configs.completions import generate_completion_script
    from shell_configs.display import console, print_error, print_hint

    try:
        script = generate_completion_script("bash")
        console.print(script)
        print_hint(
            "Add the above to your ~/.bashrc or run: shell-configs completions install"
        )
    except Exception as e:
        print_error(f"Error generating completion script: {e}")
        sys.exit(1)


@completions.command(name="zsh")
def completions_zsh() -> None:
    """Output zsh completion script for manual installation."""
    from shell_configs.completions import generate_completion_script
    from shell_configs.display import console, print_error, print_hint

    try:
        script = generate_completion_script("zsh")
        console.print(script)
        print_hint(
            "Add the above to your ~/.zshrc or run: shell-configs completions install"
        )
    except Exception as e:
        print_error(f"Error generating completion script: {e}")
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
    from shell_configs.display import print_error, print_label, print_success

    if shell is None:
        shell = detect_shell()
        if shell is None:
            print_error("Could not detect shell. Please specify with --shell")
            sys.exit(1)
        print_label("Detected shell", shell)

    success, message = install_completion(shell, dry_run=False)

    if success:
        print_success(message)
    else:
        print_error(message)
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
    from shell_configs.display import print_error, print_success

    if shell is None:
        shell = detect_shell()
        if shell is None:
            print_error("Could not detect shell. Please specify with --shell")
            sys.exit(1)

    config_path = find_config_file(shell)
    if config_path is None:
        print_error(f"No {shell} config file found")
        sys.exit(1)

    success, message = uninstall_completion(config_path)

    if success:
        print_success(message)
    else:
        print_error(message)
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
    from shell_configs.display import (
        ICON_ABSENT,
        ICON_DASH,
        ICON_SUCCESS,
        console,
        dim,
        print_hint,
        print_section,
        print_warning,
    )

    detected_shell = detect_shell()
    print_section("Shell Completions Status")

    if detected_shell:
        console.print(f"Detected shell: [cyan]{detected_shell}[/cyan]\n")
    else:
        print_warning("No supported shell detected")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Shell")
    table.add_column("Status")
    table.add_column("Config File")

    for shell in get_supported_shells():
        config_path = find_config_file(shell)

        if config_path is None:
            status = ICON_DASH
            config_str = dim("No config file found")
        elif is_completion_installed(config_path):
            status = ICON_SUCCESS
            config_str = str(config_path)
        else:
            status = ICON_ABSENT
            config_str = f"{config_path} {dim('(not installed)')}"

        shell_name = f"[bold]{shell}[/bold]" if shell == detected_shell else shell
        table.add_row(shell_name, status, config_str)

    console.print(table)
    print_hint("To install: shell-configs completions install")
