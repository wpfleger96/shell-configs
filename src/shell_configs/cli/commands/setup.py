"""Setup command — one-command setup for shell-configs."""

from __future__ import annotations

import sys

import click

from shell_configs.cli.options import dry_run_option, shells_option, yes_option


@click.command()
@yes_option
@dry_run_option("Show what would be done")
@shells_option("Comma-separated shells to install")
@click.option("--skip-completions", is_flag=True, help="Skip shell completion setup")
@click.option("--skip-packages", is_flag=True, help="Skip package installation")
@click.option("--skip-scripts", is_flag=True, help="Skip utility script installation")
@click.pass_context
def setup(
    ctx: click.Context,
    yes: bool,
    dry_run: bool,
    shells: list[str] | None,
    skip_completions: bool,
    skip_packages: bool,
    skip_scripts: bool,
) -> None:
    """One-command setup for shell-configs.

    Installs shell-configs globally via uv tool install, sets up shell
    configurations, and optionally installs tab completions.

    Run this after installing with uvx: uvx shell-configs setup
    """
    from shell_configs.bootstrap.installer import (
        get_tool_config_dir,
        get_tool_scripts_dir,
        install_tool,
        make_github_install_url,
    )
    from shell_configs.bootstrap.updater import (
        check_tool_updates,
        get_tool_by_id,
        perform_github_update,
    )
    from shell_configs.completions import (
        detect_shell,
        get_supported_shells,
        install_completion,
    )
    from shell_configs.display import (
        console,
        print_dim,
        print_done,
        print_error,
        print_info,
        print_section,
        print_success,
        print_warning,
        print_would,
    )

    if not skip_packages:
        print_section("Step 1/5: Install required packages")
        print_dim("Installing system packages needed by shell configurations.")
        console.print()
        from shell_configs.cli.groups.packages import packages_install

        ctx.invoke(packages_install, dry_run=dry_run, yes=yes)

    print_section("Step 2/5: Install shell-configs system-wide")
    print_dim("This allows you to run 'shell-configs' from any directory.")
    console.print()

    shell_configs_tool = get_tool_by_id("shell-configs")
    tool_install_success = False

    if shell_configs_tool and shell_configs_tool.is_installed():
        try:
            update_info = check_tool_updates(shell_configs_tool, timeout=10)
            if update_info and update_info.has_update:
                if dry_run:
                    print_dim(
                        f"Would upgrade shell-configs {update_info.current_version} → {update_info.latest_version}"
                    )
                    tool_install_success = True
                else:
                    if not yes and not click.confirm(
                        f"Upgrade shell-configs {update_info.current_version} → {update_info.latest_version}?",
                        default=True,
                    ):
                        print_warning("Skipped shell-configs upgrade")
                        tool_install_success = True
                    else:
                        success, msg, _ = perform_github_update(
                            make_github_install_url(shell_configs_tool.github_repo)
                        )
                        if success:
                            print_success(
                                f"Upgraded shell-configs ({update_info.current_version} → {update_info.latest_version})"
                            )
                            tool_install_success = True
                        else:
                            print_error(f"Failed to upgrade shell-configs: {msg}")
            else:
                print_done("shell-configs is already up to date")
                tool_install_success = True
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(f"Failed to check for updates: {e}")
            tool_install_success = False

    if not tool_install_success:
        if not yes and not dry_run:
            if not click.confirm("Install shell-configs permanently?", default=True):
                print_info("Setup cancelled")
                sys.exit(0)

        success, message = install_tool(force=yes, dry_run=dry_run)

        if not success:
            print_error(message)
            sys.exit(1)

        print_success(message)
        tool_install_success = True

    if not tool_install_success:
        sys.exit(1)

    if not dry_run:
        import os

        local_bin = os.path.expanduser("~/.local/bin")
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        if local_bin not in path_dirs:
            print_warning(
                f"{local_bin} is not in your PATH. Add it to use shell-configs from anywhere:"
            )
            console.print('  export PATH="$HOME/.local/bin:$PATH"\n')

    config_dir = get_tool_config_dir("shell-configs") if not dry_run else None

    print_section("Step 3/5: Installing shell configurations")

    from shell_configs.cli.commands.install import install

    ctx.invoke(
        install,
        shells=shells,
        dry_run=dry_run,
        yes=yes,
        config_dir=config_dir,
    )

    if not skip_completions:
        print_section("Step 4/5: Shell completion setup")

        shell = detect_shell()
        if shell is None:
            supported = ", ".join(get_supported_shells())
            print_warning(f"Could not detect shell. Supported: {supported}")
            print_dim("Skipping completion installation")
        else:
            if not yes and not dry_run:
                if not click.confirm(f"Install {shell} tab completion?", default=True):
                    print_dim("Skipping completion installation")
                else:
                    success, message = install_completion(shell, dry_run=dry_run)
                    if success:
                        print_success(message)
                    else:
                        print_warning(message)
            else:
                success, message = install_completion(shell, dry_run=dry_run)
                if success:
                    print_success(message)
                else:
                    print_warning(message)

    if not skip_scripts:
        print_section("Step 5/5: Install utility scripts")
        print_dim("Installing utility scripts to ~/.local/bin.")
        console.print()
        scripts_source = get_tool_scripts_dir("shell-configs") if not dry_run else None
        if scripts_source and scripts_source.exists():
            from shell_configs.script_manager import (
                InstallResult,
                ScriptManifest,
                discover_scripts,
                get_default_manifest_path,
                get_default_target_dir,
                install_script,
            )

            target_dir = get_default_target_dir()
            manifest = ScriptManifest(get_default_manifest_path())
            for entry in discover_scripts(source_dir=scripts_source):
                result, message = install_script(
                    entry,
                    target_dir,
                    manifest,
                    dry_run=dry_run,
                    source_dir=scripts_source,
                )
                if result in (InstallResult.INSTALLED, InstallResult.UPDATED):
                    print_success(message)
                elif result == InstallResult.ALREADY_SYNCED:
                    print_done(message)
                elif result == InstallResult.COLLISION:
                    print_warning(message)
                elif result in (
                    InstallResult.WOULD_INSTALL,
                    InstallResult.WOULD_UPDATE,
                ):
                    print_would(message)

    if dry_run:
        console.print()
        print_dim("Dry run complete - no changes were made.")
    else:
        console.print()
        print_success("Setup complete!")
        console.print("You can now run shell-configs from anywhere.")
