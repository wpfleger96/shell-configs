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
