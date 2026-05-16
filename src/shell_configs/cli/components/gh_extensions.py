"""GhExtensionsComponent — gh CLI extension installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    Context,
    GhExtensionsPlan,
)


class GhExtensionsComponent(Component):
    label = "gh-extensions"
    display_name = "gh CLI Extensions"

    def plan(self, ctx: Context) -> GhExtensionsPlan:
        from shell_configs.bootstrap import is_command_available
        from shell_configs.gh_extensions import command_name, load_extensions

        desired = load_extensions()

        if not is_command_available("gh"):
            return GhExtensionsPlan(
                has_changes=True,
                gh_available=False,
                desired=desired,
            )

        from shell_configs.gh_extensions import list_installed

        installed = list_installed()
        missing = [
            ext
            for ext in desired
            if ext.repo not in installed and command_name(ext.repo) not in installed
        ]
        desired_keys = {ext.repo for ext in desired}
        desired_cmd_names = {command_name(ext.repo) for ext in desired}
        extra = {
            k for k in installed if k not in desired_keys and k not in desired_cmd_names
        }

        return GhExtensionsPlan(
            has_changes=bool(missing) or bool(extra),
            desired=desired,
            installed=installed,
            missing=missing,
            extra=extra,
        )

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, GhExtensionsPlan):
            raise TypeError(f"expected GhExtensionsPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return

        from shell_configs.display import console, print_error

        console.print(f"\n[bold cyan]{self.display_name}[/bold cyan]\n")

        if not plan.gh_available:
            console.print(
                "  [dim]gh not installed — will be installed by required packages first[/dim]"
            )
            return

        for ext in plan.missing:
            print_error(f"{ext.repo} (not installed)", indent=2)
        for ext_name in sorted(plan.extra):
            console.print(f"  [dim]+[/dim] {ext_name} (not in manifest)")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, GhExtensionsPlan):
            raise TypeError(f"expected GhExtensionsPlan, got {type(plan).__name__}")
        if not plan.missing:
            return True

        from shell_configs.display import (
            print_error,
            print_success,
            print_would,
        )
        from shell_configs.gh_extensions import install_extension

        all_ok = True
        for ext in plan.missing:
            success, msg = install_extension(
                ext.repo, pin=ext.pin, dry_run=ctx.dry_run, build_path=ext.build_path
            )
            if ctx.dry_run:
                print_would(msg)
            elif success:
                print_success(msg)
            else:
                print_error(msg)
                all_ok = False
        return all_ok

    def install(self, ctx: Context) -> bool:
        from shell_configs.display import console, print_done, print_progress

        console.print()
        print_progress("Installing gh CLI extensions...")

        plan = self.plan(ctx)

        if not plan.missing:
            print_done("All gh extensions already installed")
            return True

        return self.apply(ctx, plan)

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console, print_warning

        plan = self.plan(ctx)

        if not plan.missing and not plan.extra:
            from shell_configs.display import print_success

            print_success(
                f"{len(plan.desired)}/{len(plan.desired)} extensions installed",
                indent=2,
            )
        else:
            parts = []
            if plan.missing:
                parts.append(f"{len(plan.missing)} missing")
            if plan.extra:
                parts.append(f"{len(plan.extra)} unmanaged")
            print_warning(
                f"{len(plan.desired) - len(plan.missing)}/{len(plan.desired)} extensions installed "
                f"({', '.join(parts)})",
                indent=2,
            )

        console.print()

    def diff(self, ctx: Context) -> bool:
        plan = self.plan(ctx)

        if not plan.has_changes:
            return False

        self.display_plan(plan)
        return True
