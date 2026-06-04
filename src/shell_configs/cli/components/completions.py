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
        from shell_configs.display import (
            console,
            print_dim,
            print_skipped,
            print_success,
        )

        detected_shell = detect_shell()
        if detected_shell:
            config_path = find_config_file(detected_shell)
            if config_path and is_completion_installed(config_path):
                print_success(
                    f"{detected_shell} completion installed ({config_path})", indent=2
                )
            else:
                print_skipped(
                    f"{detected_shell} completion not installed "
                    "(run: shell-configs completions install)",
                    indent=2,
                )
        else:
            supported = ", ".join(get_supported_shells())
            print_dim(
                f"Shell completion not available for your shell (only {supported} supported)",
                indent=2,
            )

        console.print()

    def uninstall(self, ctx: Context) -> None:
        from shell_configs.completions import (
            detect_shell,
            find_config_file,
            uninstall_completion,
        )
        from shell_configs.display import print_success, print_warning

        detected_shell = detect_shell()
        if not detected_shell:
            return

        config_path = find_config_file(detected_shell)
        if not config_path:
            return

        success, msg = uninstall_completion(config_path)
        if success:
            print_success(msg)
        else:
            print_warning(msg)
