"""GhExtensionsComponent — gh CLI extension installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    Context,
    GhExtensionsPlan,
    expect_plan,
)


class GhExtensionsComponent(Component):
    label = "gh-extensions"
    display_name = "gh CLI Extensions"
    apply_stage = "post"

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
        plan = expect_plan(plan, GhExtensionsPlan)
        if not plan.has_changes:
            return

        from shell_configs.display import (
            print_add,
            print_dim,
            print_error,
            print_section,
        )

        print_section(self.display_name)

        if not plan.gh_available:
            print_dim(
                "gh not installed — will be installed by required packages first",
                indent=2,
            )
            return

        for ext in plan.missing:
            print_error(f"{ext.repo} (not installed)", indent=2)
        for ext_name in sorted(plan.extra):
            print_add(f"{ext_name} (not in manifest)", indent=2)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, GhExtensionsPlan)
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

    def uninstall(self, ctx: Context) -> None:
        from shell_configs.bootstrap import is_command_available
        from shell_configs.display import print_success, print_warning
        from shell_configs.gh_extensions import (
            _remove_extension,
            command_name,
            list_installed,
            load_extensions,
        )

        if not is_command_available("gh"):
            print_warning("gh CLI not available, skipping extension removal")
            return

        desired = load_extensions()
        installed = list_installed()
        desired_repos = {ext.repo for ext in desired}
        desired_cmd_names = {command_name(ext.repo) for ext in desired}

        for key in sorted(installed):
            if key in desired_repos or key in desired_cmd_names:
                cmd = command_name(key) if "/" in key else key
                if _remove_extension(cmd):
                    print_success(f"Removed gh extension: {cmd}")
                else:
                    print_warning(f"Failed to remove gh extension: {cmd}")
