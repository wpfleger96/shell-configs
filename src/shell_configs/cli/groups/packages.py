"""Packages subcommand group."""

from __future__ import annotations

import sys

import click

from shell_configs.config import ConfigReader


@click.group()
def packages() -> None:
    """Manage system packages required by shell-configs."""
    pass


@packages.command(name="install")
@click.option("--dry-run", is_flag=True, help="Show what would be installed")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def packages_install(dry_run: bool, yes: bool, profile_name: str | None) -> None:
    """Install required system packages."""
    from shell_configs.display import (
        console,
        print_error,
        print_hint,
        print_info,
    )
    from shell_configs.packages import (
        get_package_manager,
        load_packages_for_profile,
        sort_packages_for_install,
    )
    from shell_configs.platform import detect_platform
    from shell_configs.profiles import ProfileLoader, resolve_active_profile

    config_reader = ConfigReader()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)

    platform_name = detect_platform().display_name
    console.print(f"[dim]Platform:[/dim] {platform_name}")

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available for this platform")
        print_hint("Install Homebrew: https://brew.sh (macOS) or use apt (Linux/WSL)")
        sys.exit(1)

    console.print(f"[dim]Package manager:[/dim] {manager.display_name}\n")

    try:
        packages = load_packages_for_profile(active_profile)
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    if not packages:
        print_info("No packages to install for this platform")
        return

    to_install = []
    already_installed = []

    for pkg in packages:
        if manager.is_installed(pkg):
            already_installed.append(pkg)
        else:
            to_install.append(pkg)

    to_install = sort_packages_for_install(to_install)

    if already_installed:
        console.print(f"[green]Already installed ({len(already_installed)}):[/green]")
        for pkg in already_installed:
            console.print(f"  [dim]{pkg.name}[/dim]")

    if not to_install:
        console.print("\n[green]✓[/green] All required packages are already installed")
        return

    console.print(f"\n[cyan]Packages to install ({len(to_install)}):[/cyan]")
    for pkg in to_install:
        desc = f" - {pkg.description}" if pkg.description else ""
        console.print(f"  {pkg.name}{desc}")

    if not yes and not dry_run:
        if not click.confirm("\nInstall these packages?", default=True):
            print_info("Installation cancelled")
            return

    console.print()
    total = len(to_install)
    for i, pkg in enumerate(to_install, start=1):
        if not dry_run:
            console.print(f"[dim][{i}/{total}] Installing {pkg.name}...[/dim]")

        success, message = manager.install(pkg, dry_run=dry_run)

        if success:
            if "already installed" in message:
                console.print(f"[dim]✓[/dim] {pkg.name} [dim](already installed)[/dim]")
            elif dry_run:
                console.print(f"[dim]  Would install {pkg.name}[/dim]")
            else:
                console.print(f"[green]✓[/green] {pkg.name}")
        else:
            print_error(f"{pkg.name}: {message}")

        if not dry_run and i < total:
            console.print()

    if dry_run:
        print_hint("Use without --dry-run to install.")
    else:
        console.print(
            f"\n[green]✓[/green] Package installation complete ({total} packages)"
        )


@packages.command(name="status")
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def packages_status(profile_name: str | None) -> None:
    """Show status of required packages."""
    from shell_configs.display import (
        console,
        print_error,
        print_hint,
        print_info,
    )
    from shell_configs.packages import get_package_manager, load_packages_for_profile
    from shell_configs.platform import detect_platform
    from shell_configs.profiles import ProfileLoader, resolve_active_profile

    config_reader = ConfigReader()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)

    platform_name = detect_platform().display_name
    console.print(f"[dim]Platform:[/dim] {platform_name}\n")

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available")
        return

    console.print(f"[dim]Package manager:[/dim] {manager.display_name}\n")

    try:
        packages = load_packages_for_profile(active_profile)
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    if not packages:
        print_info("No packages configured for this platform")
        return

    installed = []
    missing = []

    for pkg in packages:
        if manager.is_installed(pkg):
            installed.append(pkg)
        else:
            missing.append(pkg)

    if installed:
        console.print(f"[green]Installed ({len(installed)}):[/green]")
        for pkg in installed:
            console.print(f"  [green]✓[/green] {pkg.name}")

    if missing:
        console.print(f"\n[yellow]Missing ({len(missing)}):[/yellow]")
        for pkg in missing:
            print_error(pkg.name, indent=2)
        print_hint("Run 'shell-configs packages install' to install missing packages")
    else:
        console.print("\n[green]✓[/green] All required packages are installed")


@packages.command(name="uninstall")
@click.option("--dry-run", is_flag=True, help="Show what would be uninstalled")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option("--profile", "profile_name", default=None, help="Profile to use")
def packages_uninstall(dry_run: bool, yes: bool, profile_name: str | None) -> None:
    """Uninstall managed system packages."""
    from shell_configs.display import (
        console,
        print_error,
        print_hint,
        print_info,
        print_warning,
    )
    from shell_configs.packages import (
        get_package_manager,
        load_packages_for_profile,
        sort_packages_for_uninstall,
    )
    from shell_configs.platform import detect_platform
    from shell_configs.profiles import ProfileLoader, resolve_active_profile

    config_reader = ConfigReader()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)

    platform_name = detect_platform().display_name
    console.print(f"[dim]Platform:[/dim] {platform_name}")

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available for this platform")
        sys.exit(1)

    console.print(f"[dim]Package manager:[/dim] {manager.display_name}\n")

    try:
        packages = load_packages_for_profile(active_profile)
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    if not packages:
        print_info("No packages configured for this platform")
        return

    to_uninstall = []
    managed_externally = []
    not_installed = []

    for pkg in packages:
        if manager.can_uninstall(pkg):
            to_uninstall.append(pkg)
        elif manager.is_installed(pkg):
            managed_externally.append(pkg)
        else:
            not_installed.append(pkg)

    to_uninstall = sort_packages_for_uninstall(to_uninstall)

    if managed_externally:
        console.print(f"[dim]Managed externally ({len(managed_externally)}):[/dim]")
        for pkg in managed_externally:
            console.print(f"  [dim]{pkg.name} (not via {manager.display_name})[/dim]")

    if not_installed:
        console.print(f"[dim]Not installed ({len(not_installed)}):[/dim]")
        for pkg in not_installed:
            console.print(f"  [dim]{pkg.name}[/dim]")

    if not to_uninstall:
        console.print("\n[green]✓[/green] No packages to uninstall")
        return

    console.print(f"\n[cyan]Packages to uninstall ({len(to_uninstall)}):[/cyan]")
    for pkg in to_uninstall:
        desc = f" - {pkg.description}" if pkg.description else ""
        console.print(f"  {pkg.name}{desc}")

    if not yes and not dry_run:
        if not click.confirm("\nUninstall these packages?", default=False):
            print_info("Uninstall cancelled")
            return

    console.print()
    total = len(to_uninstall)
    success_count = 0
    fail_count = 0

    for i, pkg in enumerate(to_uninstall, start=1):
        if not dry_run:
            console.print(f"[dim][{i}/{total}] Uninstalling {pkg.name}...[/dim]")

        success, message = manager.uninstall(pkg, dry_run=dry_run)

        if success:
            if "not installed" in message or "skipping" in message:
                console.print(f"[dim]  {pkg.name} ({message})[/dim]")
            elif dry_run:
                console.print(f"[dim]  Would uninstall {pkg.name}[/dim]")
            else:
                console.print(f"[green]✓[/green] {pkg.name}")
                success_count += 1
        else:
            print_error(f"{pkg.name}: {message}")
            fail_count += 1

        if not dry_run and i < total:
            console.print()

    if dry_run:
        print_hint("Use without --dry-run to uninstall.")
    else:
        if fail_count > 0:
            console.print()
            print_warning(f"{success_count} uninstalled, {fail_count} failed")
        else:
            console.print(
                f"\n[green]✓[/green] Package uninstall complete ({success_count} packages)"
            )
