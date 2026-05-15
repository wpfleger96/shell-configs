"""CompletionsComponent — shell completion installation status."""

from __future__ import annotations

from shell_configs.cli.context import Component, Context


class CompletionsComponent(Component):
    label = "completions"
    display_name = "Shell Completions"

    def status(self, ctx: Context) -> None:
        from shell_configs.completions import (
            detect_shell,
            find_config_file,
            get_supported_shells,
            is_completion_installed,
        )
        from shell_configs.display import console

        console.print(f"[bold cyan]{self.display_name}[/bold cyan]\n")

        detected_shell = detect_shell()
        if detected_shell:
            config_path = find_config_file(detected_shell)
            if config_path and is_completion_installed(config_path):
                console.print(
                    f"  [green]✓[/green] {detected_shell} completion installed ({config_path})"
                )
            else:
                console.print(
                    f"  [yellow]⚠[/yellow] {detected_shell} completion not installed "
                    "(run: shell-configs completions install)"
                )
        else:
            supported = ", ".join(get_supported_shells())
            console.print(
                f"  [dim]Shell completion not available for your shell (only {supported} supported)[/dim]"
            )

        console.print()
