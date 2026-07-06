"""Package components — required and optional package management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    Context,
    OptionalPackagesPlan,
    RequiredPackagesPlan,
    expect_plan,
)

if TYPE_CHECKING:
    from shell_configs.packages.packages import Package


def _any_pkg_needs_sudo(packages: list[Package]) -> bool:
    """True when any package in the list would invoke sudo on the current platform."""
    from shell_configs.platform import Platform, is_platform

    if not (is_platform(Platform.LINUX) or is_platform(Platform.WSL)):
        return False
    from shell_configs.packages.packages import _linux_needs_sudo

    return any(_linux_needs_sudo(p) for p in packages)


class RequiredPackagesComponent(Component):
    label = "required-packages"
    display_name = "Required Packages"
    apply_stage = "pre"

    def plan(self, ctx: Context) -> RequiredPackagesPlan:
        from shell_configs.packages import (
            get_package_manager,
            load_packages_for_profile,
        )

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return RequiredPackagesPlan(has_changes=False)

        try:
            packages = load_packages_for_profile(ctx.profile)
            required = [pkg for pkg in packages if pkg.required]
            missing = [pkg for pkg in required if not pkg_manager.is_installed(pkg)]
        except Exception:
            return RequiredPackagesPlan(has_changes=False)

        return RequiredPackagesPlan(has_changes=bool(missing), missing=missing)

    def needs_sudo(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, RequiredPackagesPlan)
        return bool(plan.missing) and _any_pkg_needs_sudo(plan.missing)

    def display_plan(self, plan: ComponentPlan) -> None:
        plan = expect_plan(plan, RequiredPackagesPlan)
        if not plan.has_changes:
            return

        from shell_configs.display import console, print_progress, print_section

        print_section(self.display_name)
        print_progress(f"Installing {len(plan.missing)} required package(s)...")
        for pkg in plan.missing:
            console.print(f"  {pkg.name}")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, RequiredPackagesPlan)
        if not plan.missing:
            return True

        from shell_configs.display import (
            console,
            print_error,
            print_success,
            print_warning,
        )
        from shell_configs.packages import get_package_manager

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return True

        try:
            for pkg in plan.missing:
                console.print(f"  Installing {pkg.name}...")
                success, message = pkg_manager.install(pkg, dry_run=False)
                if success:
                    print_success(pkg.name, indent=2)
                else:
                    print_error(f"{pkg.name}: {message}", indent=2)
            console.print()
        except Exception as e:
            print_warning(f"Error installing required packages: {e}")

        return True


class OptionalPackagesComponent(Component):
    label = "optional-packages"
    display_name = "Packages"

    def plan(self, ctx: Context) -> OptionalPackagesPlan:
        from shell_configs.packages import (
            get_package_manager,
            load_packages_for_profile,
        )

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return OptionalPackagesPlan(has_changes=False)

        try:
            packages = load_packages_for_profile(ctx.profile)
            missing = [pkg for pkg in packages if not pkg_manager.is_installed(pkg)]
        except Exception:
            return OptionalPackagesPlan(has_changes=False)

        return OptionalPackagesPlan(
            has_changes=bool(missing), total=packages, missing=missing
        )

    def needs_sudo(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, OptionalPackagesPlan)
        return bool(plan.missing) and _any_pkg_needs_sudo(plan.missing)

    def display_plan(self, plan: ComponentPlan) -> None:
        plan = expect_plan(plan, OptionalPackagesPlan)
        if not plan.has_changes:
            return

        from shell_configs.display import (
            print_error,
            print_section,
            print_warning,
        )

        print_section(self.display_name)
        print_warning(f"{len(plan.missing)}/{len(plan.total)} packages missing")
        for pkg in plan.missing:
            print_error(pkg.name, indent=2)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        plan = expect_plan(plan, OptionalPackagesPlan)
        if not plan.missing:
            return True

        from shell_configs.display import console, print_dim, print_error, print_success
        from shell_configs.packages import get_package_manager

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return True

        try:
            total = len(plan.missing)
            for i, pkg in enumerate(plan.missing, start=1):
                print_dim(f"[{i}/{total}] Installing {pkg.name}...")
                success, message = pkg_manager.install(pkg, dry_run=False)

                if success:
                    print_success(pkg.name)
                else:
                    print_error(f"{pkg.name}: {message}")

                if i < total:
                    console.print()

            console.print()
            print_success(f"Package installation complete ({total} packages)")
        except Exception as e:
            print_error(f"Error installing packages: {e}")

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import (
            console,
            print_dim,
            print_hint,
            print_success,
            print_warning,
        )
        from shell_configs.packages import get_package_manager

        pkg_manager = get_package_manager()
        if not pkg_manager:
            print_dim("No package manager available", indent=2)
            console.print()
            return

        plan = self.plan(ctx)
        installed_count = len(plan.total) - len(plan.missing)
        total_count = len(plan.total)
        display_name = pkg_manager.display_name

        if not plan.missing:
            print_success(
                f"{installed_count}/{total_count} packages installed ({display_name})",
                indent=2,
            )
        else:
            print_warning(
                f"{installed_count}/{total_count} packages installed ({display_name})",
                indent=2,
            )
            print_hint("Run 'shell-configs packages status' for details", indent=2)

        console.print()
