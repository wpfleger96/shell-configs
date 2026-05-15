"""Package components — required and optional package management."""

from __future__ import annotations

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    Context,
    OptionalPackagesPlan,
    RequiredPackagesPlan,
)


class RequiredPackagesComponent(Component):
    label = "required-packages"
    display_name = "Required Packages"

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

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, RequiredPackagesPlan):
            raise TypeError(f"expected RequiredPackagesPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return

        from shell_configs.display import console

        console.print(f"\n[bold cyan]{self.display_name}[/bold cyan]\n")
        console.print(
            f"[yellow]Installing {len(plan.missing)} required package(s)...[/yellow]"
        )
        for pkg in plan.missing:
            console.print(f"  {pkg.name}")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, RequiredPackagesPlan):
            raise TypeError(f"expected RequiredPackagesPlan, got {type(plan).__name__}")
        if not plan.missing:
            return True

        from shell_configs.display import console, print_warning
        from shell_configs.packages import get_package_manager

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return True

        try:
            for pkg in plan.missing:
                console.print(f"  Installing {pkg.name}...")
                success, message = pkg_manager.install(pkg, dry_run=False)
                if success:
                    console.print(f"  [green]✓[/green] {pkg.name}")
                else:
                    console.print(f"  [red]✗[/red] {pkg.name}: {message}")
            console.print()
        except Exception as e:
            print_warning(f"Error installing required packages: {e}")

        return True

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        plan = self.plan(ctx)
        self.display_plan(plan)
        return self.apply(ctx, plan)


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

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, OptionalPackagesPlan):
            raise TypeError(f"expected OptionalPackagesPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return

        from shell_configs.display import console

        console.print(f"\n[bold cyan]{self.display_name}[/bold cyan]\n")
        console.print(
            f"[yellow]⚠[/yellow] {len(plan.missing)}/{len(plan.total)} packages missing"
        )
        for pkg in plan.missing:
            console.print(f"  [red]✗[/red] {pkg.name}")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, OptionalPackagesPlan):
            raise TypeError(f"expected OptionalPackagesPlan, got {type(plan).__name__}")
        if not plan.missing:
            return True

        from shell_configs.display import console
        from shell_configs.packages import get_package_manager

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return True

        try:
            total = len(plan.missing)
            for i, pkg in enumerate(plan.missing, start=1):
                console.print(f"[dim][{i}/{total}] Installing {pkg.name}...[/dim]")
                success, message = pkg_manager.install(pkg, dry_run=False)

                if success:
                    console.print(f"[green]✓[/green] {pkg.name}")
                else:
                    console.print(f"[red]✗[/red] {pkg.name}: {message}")

                if i < total:
                    console.print()

            console.print(
                f"\n[green]✓[/green] Package installation complete ({total} packages)"
            )
        except Exception as e:
            console.print(f"\n[red]Error installing packages:[/red] {e}")

        return True

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        import click

        from shell_configs.display import print_info

        plan = self.plan(ctx)

        if not plan.has_changes:
            from shell_configs.display import console

            console.print()
            console.print(
                f"[green]✓[/green] All {len(plan.total)} packages already installed"
            )
            return True

        self.display_plan(plan)

        if ctx.yes or click.confirm("Install missing packages?", default=True):
            from shell_configs.display import console

            console.print()
            return self.apply(ctx, plan)
        else:
            print_info(
                "Skipping package installation. Run 'shell-configs packages install' later."
            )
            return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.packages import get_package_manager

        pkg_manager = get_package_manager()
        if not pkg_manager:
            console.print("  [dim]No package manager available[/dim]")
            console.print()
            return

        plan = self.plan(ctx)
        installed_count = len(plan.total) - len(plan.missing)
        total_count = len(plan.total)
        display_name = pkg_manager.display_name

        if not plan.missing:
            console.print(
                f"  [green]✓[/green] {installed_count}/{total_count} packages installed ({display_name})"
            )
        else:
            console.print(
                f"  [yellow]⚠[/yellow] {installed_count}/{total_count} packages installed ({display_name})"
            )
            console.print(
                "  [dim]Run 'shell-configs packages status' for details[/dim]"
            )

        console.print()

    def diff(self, ctx: Context) -> bool:
        from shell_configs.display import console

        plan = self.plan(ctx)
        if not plan.has_changes:
            return False

        console.print(f"\n[bold cyan]{self.display_name}[/bold cyan]\n")
        for pkg in plan.missing:
            console.print(f"  [red]✗[/red] {pkg.name} (not installed)")
        return True
