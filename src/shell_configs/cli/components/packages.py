"""Package components — required and optional package management."""

from __future__ import annotations

from shell_configs.cli.context import Component, Context


class RequiredPackagesComponent(Component):
    label = "required-packages"

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        from shell_configs.display import console, print_warning
        from shell_configs.packages import (
            get_package_manager,
            load_packages_for_profile,
        )

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return True

        try:
            packages = load_packages_for_profile(ctx.profile)
            required = [pkg for pkg in packages if pkg.required]
            missing_required = [
                pkg for pkg in required if not pkg_manager.is_installed(pkg)
            ]

            if missing_required:
                console.print(
                    f"[yellow]Installing {len(missing_required)} required package(s)...[/yellow]"
                )
                for pkg in missing_required:
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


class OptionalPackagesComponent(Component):
    label = "optional-packages"

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        from rich.prompt import Confirm

        from shell_configs.display import console, print_info
        from shell_configs.packages import (
            get_package_manager,
            load_packages_for_profile,
        )

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return True

        try:
            packages = load_packages_for_profile(ctx.profile)
            missing = [pkg for pkg in packages if not pkg_manager.is_installed(pkg)]

            if missing:
                console.print()
                console.print(
                    f"[yellow]⚠[/yellow] {len(missing)}/{len(packages)} packages missing"
                )

                if ctx.yes or Confirm.ask("Install missing packages?", default=True):
                    console.print()
                    total = len(missing)
                    for i, pkg in enumerate(missing, start=1):
                        console.print(
                            f"[dim][{i}/{total}] Installing {pkg.name}...[/dim]"
                        )
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
                else:
                    print_info(
                        "Skipping package installation. Run 'shell-configs packages install' later."
                    )
            else:
                console.print()
                console.print(
                    f"[green]✓[/green] All {len(packages)} packages already installed"
                )
        except Exception as e:
            console.print(f"\n[red]Error checking packages:[/red] {e}")

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.packages import (
            get_package_manager,
            load_packages_for_profile,
        )

        console.print("[bold cyan]Packages[/bold cyan]\n")

        pkg_manager = get_package_manager()
        if pkg_manager:
            try:
                packages = load_packages_for_profile(ctx.profile)
                installed = []
                missing = []
                for pkg in packages:
                    if pkg_manager.is_installed(pkg):
                        installed.append(pkg)
                    else:
                        missing.append(pkg)

                if not missing:
                    console.print(
                        f"  [green]✓[/green] {len(installed)}/{len(packages)} packages installed ({pkg_manager.display_name})"
                    )
                else:
                    console.print(
                        f"  [yellow]⚠[/yellow] {len(installed)}/{len(packages)} packages installed ({pkg_manager.display_name})"
                    )
                    console.print(
                        "  [dim]Run 'shell-configs packages status' for details[/dim]"
                    )
            except Exception as e:
                console.print(f"  [red]✗[/red] Error checking packages: {e}")
        else:
            console.print("  [dim]No package manager available[/dim]")

        console.print()

    def diff(self, ctx: Context) -> bool:
        from shell_configs.display import console
        from shell_configs.packages import (
            get_package_manager,
            load_packages_for_profile,
        )

        pkg_manager = get_package_manager()
        if not pkg_manager:
            return False

        try:
            packages = load_packages_for_profile(ctx.profile)
            missing = [pkg for pkg in packages if not pkg_manager.is_installed(pkg)]
        except Exception:
            return False

        if not missing:
            return False

        console.print("\n[bold cyan]Packages[/bold cyan]\n")
        for pkg in missing:
            console.print(f"  [yellow]✗[/yellow] {pkg.name} (not installed)")
        return True
