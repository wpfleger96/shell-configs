"""Validate command — checks configuration file syntax."""

from __future__ import annotations

import sys

import click

from shell_configs.cli.helpers import _get_selected_shells, load_profile_context
from shell_configs.cli.options import profile_option, shells_option


@click.command()
@shells_option("Comma-separated list of shells to validate")
@profile_option
def validate(shells: list[str] | None, profile_name: str | None) -> None:
    """Validate configuration file syntax."""
    from shell_configs.display import (
        add_validation_row,
        console,
        create_validation_table,
        print_error,
        print_info,
        print_warning,
    )

    config_reader, registry, active_profile = load_profile_context(profile_name)

    selected_shells = _get_selected_shells(
        registry, shells, config_reader=config_reader
    )

    all_valid = True
    table = create_validation_table()

    if not selected_shells:
        print_warning("No shell configurations found")
    else:
        for shell in selected_shells:
            for config_file in shell.get_config_files():
                content = config_reader.get_config_content(
                    shell.name, config_file.repo_config_name, profile=active_profile
                )
                if content is None:
                    continue

                valid, message = shell.validate_syntax(content)
                add_validation_row(table, shell.display_name, valid, message)

                if not valid:
                    all_valid = False

        console.print(table)

    from shell_configs.profiles import ProfileLoader
    from shell_configs.profiles.profile import ProfileError

    profile_loader = ProfileLoader(config_reader.config_dir)
    profile_errors: list[str] = []
    for pname in profile_loader.list_profiles():
        try:
            profile_loader.resolve_profile(pname)
        except ProfileError as e:
            profile_errors.append(f"{pname}: {e}")

    if profile_errors:
        console.print()
        for err in profile_errors:
            print_error(f"Profile inheritance error — {err}")
        all_valid = False

    if not all_valid:
        print_error("Some configurations have syntax errors")
        sys.exit(1)
    else:
        print_info("All configurations are valid")
