"""Packages subcommand group."""

from __future__ import annotations

import sys

import click

from shell_configs.cli.helpers import load_profile_context
from shell_configs.cli.options import dry_run_option, profile_option, yes_option


@click.group()
def packages() -> None:
    """Manage system packages required by shell-configs."""
    pass


@packages.command(name="install")
@dry_run_option("Show what would be installed")
@yes_option
@profile_option
def packages_install(dry_run: bool, yes: bool, profile_name: str | None) -> None:
    """Install required system packages."""
    from shell_configs.display import (
        console,
        dim,
        print_dim,
        print_done,
        print_error,
        print_hint,
        print_info,
        print_label,
        print_success,
    )
    from shell_configs.packages import (
        get_package_manager,
        load_packages_for_profile,
        sort_packages_for_install,
    )
    from shell_configs.platform import detect_platform

    _, _, active_profile = load_profile_context(profile_name)

    platform_name = detect_platform().display_name
    print_label("Platform", platform_name)

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available for this platform")
        print_hint("Install Homebrew: https://brew.sh (macOS) or use apt (Linux/WSL)")
        sys.exit(1)

    print_label("Package manager", manager.display_name)
    console.print()

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
            print_dim(pkg.name, indent=2)

    if not to_install:
        console.print()
        print_success("All required packages are already installed")
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
            print_dim(f"[{i}/{total}] Installing {pkg.name}...")

        success, message = manager.install(pkg, dry_run=dry_run)

        if success:
            if "already installed" in message:
                print_done(f"{pkg.name} {dim('(already installed)')}")
            elif dry_run:
                print_dim(f"Would install {pkg.name}", indent=2)
            else:
                print_success(pkg.name)
        else:
            print_error(f"{pkg.name}: {message}")

        if not dry_run and i < total:
            console.print()

    if dry_run:
        print_hint("Use without --dry-run to install.")
    else:
        console.print()
        print_success(f"Package installation complete ({total} packages)")


@packages.command(name="status")
@profile_option
def packages_status(profile_name: str | None) -> None:
    """Show status of required packages."""
    from shell_configs.display import (
        console,
        print_error,
        print_hint,
        print_info,
        print_label,
        print_success,
    )
    from shell_configs.packages import get_package_manager, load_packages_for_profile
    from shell_configs.platform import detect_platform

    _, _, active_profile = load_profile_context(profile_name)

    platform_name = detect_platform().display_name
    print_label("Platform", platform_name)
    console.print()

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available")
        return

    print_label("Package manager", manager.display_name)
    console.print()

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
            print_success(pkg.name, indent=2)

    if missing:
        console.print(f"\n[yellow]Missing ({len(missing)}):[/yellow]")
        for pkg in missing:
            print_error(pkg.name, indent=2)
        print_hint("Run 'shell-configs packages install' to install missing packages")
    else:
        console.print()
        print_success("All required packages are installed")


@packages.command(name="uninstall")
@dry_run_option("Show what would be uninstalled")
@yes_option
@profile_option
def packages_uninstall(dry_run: bool, yes: bool, profile_name: str | None) -> None:
    """Uninstall managed system packages."""
    from shell_configs.display import (
        console,
        print_dim,
        print_error,
        print_hint,
        print_info,
        print_label,
        print_success,
        print_warning,
    )
    from shell_configs.packages import (
        get_package_manager,
        load_packages_for_profile,
        sort_packages_for_uninstall,
    )
    from shell_configs.platform import detect_platform

    _, _, active_profile = load_profile_context(profile_name)

    platform_name = detect_platform().display_name
    print_label("Platform", platform_name)

    manager = get_package_manager()

    if manager is None:
        print_error("No package manager available for this platform")
        sys.exit(1)

    print_label("Package manager", manager.display_name)
    console.print()

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
        print_dim(f"Managed externally ({len(managed_externally)}):")
        for pkg in managed_externally:
            print_dim(f"{pkg.name} (not via {manager.display_name})", indent=2)

    if not_installed:
        print_dim(f"Not installed ({len(not_installed)}):")
        for pkg in not_installed:
            print_dim(pkg.name, indent=2)

    if not to_uninstall:
        console.print()
        print_success("No packages to uninstall")
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
            print_dim(f"[{i}/{total}] Uninstalling {pkg.name}...")

        success, message = manager.uninstall(pkg, dry_run=dry_run)

        if success:
            if "not installed" in message or "skipping" in message:
                print_dim(f"{pkg.name} ({message})", indent=2)
            elif dry_run:
                print_dim(f"Would uninstall {pkg.name}", indent=2)
            else:
                print_success(pkg.name)
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
            console.print()
            print_success(f"Package uninstall complete ({success_count} packages)")
