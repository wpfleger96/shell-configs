"""ExtensionsComponent — IDE extension installation, status, and diff."""

from __future__ import annotations

from typing import Any

from shell_configs.cli.context import Component, ComponentPlan, Context, ExtensionsPlan


class ExtensionsComponent(Component):
    label = "extensions"
    display_name = "Extensions"

    def plan(self, ctx: Context) -> ExtensionsPlan:
        from shell_configs.cli.helpers import _get_extension_shells
        from shell_configs.extensions import ExtensionManager

        ext_manager = ExtensionManager()
        ide_shells = _get_extension_shells(ctx.registry)
        per_shell: dict[str, Any] = {}
        ignored_per_shell: dict[str, frozenset[str]] = {}

        for shell in ide_shells:
            invoker = shell.get_extension_invoker()
            cli_cmd = shell.get_extension_cli()
            if invoker is None and cli_cmd is None:
                continue

            desired = ext_manager.load_desired_extensions(
                shell.name,
                shell.get_extension_list_paths(),
                profile=ctx.profile,
            )
            installed = ext_manager.get_installed_extensions(cli_cmd, invoker=invoker)
            if installed is None:
                continue

            diff = ext_manager.compute_diff(desired, installed, shell_name=shell.name)
            per_shell[shell.name] = diff
            ignored_per_shell[shell.name] = diff.ignored

        has_changes = any(d.missing for d in per_shell.values())
        return ExtensionsPlan(
            has_changes=has_changes,
            per_shell=per_shell,
            ignored_per_shell=ignored_per_shell,
        )

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, ExtensionsPlan):
            raise TypeError(f"expected ExtensionsPlan, got {type(plan).__name__}")
        from shell_configs.display import (
            console,
            print_add,
            print_builtin,
            print_dim,
            print_error,
            print_section,
        )

        found_diffs = False
        for shell_name, diff in plan.per_shell.items():
            if not diff.missing and not diff.extra and not diff.ignored:
                continue

            if not found_diffs:
                print_section(self.display_name)
            found_diffs = True
            console.print(f"\n  [bold]{shell_name}[/bold]")

            if diff.ignored:
                console.print(
                    f"    [yellow]Ignored built-ins in config ({len(diff.ignored)}):[/yellow]"
                )
                for ext_id in sorted(diff.ignored):
                    print_builtin(ext_id, indent=6)

            if diff.missing:
                console.print(f"    [yellow]Missing ({len(diff.missing)}):[/yellow]")
                for ext_id in sorted(diff.missing):
                    print_error(ext_id, indent=6)

            if diff.extra:
                print_dim(f"Unmanaged ({len(diff.extra)}):", indent=4)
                for ext_id in sorted(diff.extra):
                    print_add(ext_id, indent=6)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, ExtensionsPlan):
            raise TypeError(f"expected ExtensionsPlan, got {type(plan).__name__}")
        if ctx.dry_run:
            return True

        from shell_configs.cli.helpers import (
            _get_extension_shells,
            _print_extension_result,
            _print_ignored_builtin_extensions,
        )
        from shell_configs.display import console, print_done, print_progress
        from shell_configs.extensions import ExtensionManager

        ext_manager = ExtensionManager()
        ide_shells = _get_extension_shells(ctx.registry)
        # Index shells by name for O(1) invoker lookup
        shell_by_name = {s.name: s for s in ide_shells}

        any_ext_activity = False
        for shell_name, diff in plan.per_shell.items():
            shell = shell_by_name.get(shell_name)
            if shell is None:
                continue

            invoker = shell.get_extension_invoker()
            cli_cmd = shell.get_extension_cli()
            printed_header = False

            if diff.ignored:
                if not any_ext_activity:
                    console.print()
                    print_progress("Installing IDE extensions...")
                any_ext_activity = True
                console.print(f"  [bold cyan]{shell.display_name}[/bold cyan]")
                printed_header = _print_ignored_builtin_extensions(
                    console,
                    shell.display_name,
                    diff.ignored,
                    header_printed=True,
                )

            if not diff.missing:
                continue

            if not any_ext_activity:
                console.print()
                print_progress("Installing IDE extensions...")
            any_ext_activity = True

            if not printed_header:
                console.print(
                    f"  [bold cyan]{shell.display_name}[/bold cyan]: "
                    f"{len(diff.missing)} missing"
                )
            else:
                print_progress(
                    f"Installing {len(diff.missing)} missing extension(s)...", indent=2
                )

            ext_results = ext_manager.install_extensions(
                cli_cmd, set(diff.missing), dry_run=ctx.dry_run, invoker=invoker
            )
            for ext_r in ext_results:
                _print_extension_result(ext_r)

        if not any_ext_activity:
            console.print()
            print_done("All IDE extensions already in sync")

        return True

    def install(self, ctx: Context) -> bool:
        p = self.plan(ctx)
        self.display_plan(p)
        return self.apply(ctx, p)

    def status(self, ctx: Context) -> None:
        from shell_configs.cli.helpers import _get_extension_shells
        from shell_configs.display import (
            console,
            print_hint,
            print_success,
            print_warning,
        )
        from shell_configs.extensions import ExtensionManager

        ext_manager = ExtensionManager()
        ide_shells = _get_extension_shells(ctx.registry)
        for shell in ide_shells:
            invoker = shell.get_extension_invoker()
            cli_cmd = shell.get_extension_cli()
            if invoker is None and cli_cmd is None:
                continue

            ext_desired = ext_manager.load_desired_extensions(
                shell.name, shell.get_extension_list_paths(), profile=ctx.profile
            )
            ext_installed = ext_manager.get_installed_extensions(
                cli_cmd, invoker=invoker
            )
            if ext_installed is None:
                continue
            ext_diff = ext_manager.compute_diff(
                ext_desired, ext_installed, shell_name=shell.name
            )

            if not ext_diff.missing and not ext_diff.extra:
                print_success(
                    f"{shell.display_name}: "
                    f"{len(ext_diff.matched)}/{len(ext_desired)} extensions synced",
                    indent=2,
                )
            else:
                parts = []
                if ext_diff.missing:
                    parts.append(f"{len(ext_diff.missing)} missing")
                if ext_diff.extra:
                    parts.append(f"{len(ext_diff.extra)} unmanaged")
                print_warning(
                    f"{shell.display_name}: "
                    f"{len(ext_diff.matched)}/{len(ext_desired)} synced ({', '.join(parts)})",
                    indent=2,
                )
                print_hint("Run 'shell-configs extensions diff' for details", indent=2)

        console.print()

    def diff(self, ctx: Context) -> bool:
        p = self.plan(ctx)
        self.display_plan(p)
        return any(d.missing or d.extra or d.ignored for d in p.per_shell.values())
