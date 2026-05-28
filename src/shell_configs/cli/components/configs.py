"""ConfigsComponent — manages shell config file installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import Component, ComponentPlan, ConfigsPlan, Context


class ConfigsComponent(Component):
    label = "configs"
    display_name = "Configs"

    def plan(self, ctx: Context) -> ConfigsPlan:
        from shell_configs.bootstrap import load_auto_update_config
        from shell_configs.cli.helpers import _compute_diffs_for_shells
        from shell_configs.manager import ConfigManager

        auto_update_config = load_auto_update_config()
        manager = ConfigManager(backup_retention=auto_update_config.backup_retention)
        diffs = _compute_diffs_for_shells(ctx, manager)
        return ConfigsPlan(has_changes=bool(diffs), diffs=diffs)

    def display_plan(self, plan: ComponentPlan) -> None:
        from shell_configs.cli.helpers import _render_diffs

        if not isinstance(plan, ConfigsPlan):
            raise TypeError(f"expected ConfigsPlan, got {type(plan).__name__}")
        _render_diffs(plan.diffs)

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, ConfigsPlan):
            raise TypeError(f"expected ConfigsPlan, got {type(plan).__name__}")

        from shell_configs.bootstrap import load_auto_update_config
        from shell_configs.bootstrap.config import save_auto_update_config
        from shell_configs.display import (
            print_diff,
            print_hint,
            print_info,
            print_operation_result,
            print_warning,
        )
        from shell_configs.manager import ConfigManager, OperationResult
        from shell_configs.shells.base import merge_json_with_profile

        auto_update_config = load_auto_update_config()
        manager = ConfigManager(backup_retention=auto_update_config.backup_retention)

        results = {}
        additional_file_results = {}

        for shell in ctx.selected_shells:
            for config_file in shell.get_config_files():
                if config_file.repo_config_name is None:
                    content = None
                else:
                    content = ctx.config_reader.get_config_content(
                        shell.name, config_file.repo_config_name, profile=ctx.profile
                    )
                    if content is None:
                        print_warning(
                            f"No configuration found for {shell.name}/{config_file.repo_config_name}"
                        )
                        continue

                shared_content = None
                if shell.supports_shared_config():
                    shared_content = ctx.config_reader.get_shared_config_content(
                        shell.name, profile=ctx.profile
                    )

                if content is None and shared_content is None:
                    continue

                result, message, diff_text = manager.install_section(
                    config_file.path,
                    content,
                    dry_run=ctx.dry_run,
                    shared_content=shared_content,
                    force=ctx.force,
                )
                print_operation_result(result, message)
                if diff_text and result == OperationResult.UPDATED:
                    print_diff(diff_text)
                results[shell.name] = result

        for shell in ctx.selected_shells:
            additional_files = shell.get_additional_files()
            for additional_file in additional_files:
                if additional_file.xml_guiconfig_merge:
                    result, message, diff_text = manager.install_xml_guiconfig_file(
                        additional_file.source_path,
                        additional_file.target_path,
                        dry_run=ctx.dry_run,
                        force=ctx.force,
                    )
                elif additional_file.ini_merge:
                    result, message, diff_text = manager.install_ini_file(
                        additional_file.source_path,
                        additional_file.target_path,
                        dry_run=ctx.dry_run,
                        force=ctx.force,
                    )
                elif additional_file.comment_prefix:
                    content = additional_file.source_path.read_text()
                    result, message, diff_text = manager.install_section(
                        additional_file.target_path,
                        content,
                        dry_run=ctx.dry_run,
                        comment_prefix=additional_file.comment_prefix,
                        force=ctx.force,
                    )
                elif additional_file.target_merge:
                    from shell_configs.shells.base import merge_json_into_target

                    merged_content, is_synced = merge_json_into_target(
                        additional_file.source_path,
                        additional_file.target_path,
                    )
                    if is_synced:
                        result = OperationResult.ALREADY_SYNCED
                        message = f"Already synced: {additional_file.target_path}"
                        diff_text = None
                    else:
                        result, message, diff_text = (
                            manager.install_additional_file_from_content(
                                merged_content,
                                additional_file.target_path,
                                dry_run=ctx.dry_run,
                                backup_dir=additional_file.backup_dir,
                                force=ctx.force,
                            )
                        )
                elif additional_file.base_source_path:
                    profile_overrides = (
                        ctx.profile.settings_overrides.get(shell.name)
                        if ctx.profile
                        else None
                    )
                    merged_content = merge_json_with_profile(
                        additional_file.base_source_path,
                        additional_file.source_path,
                        profile_overrides,
                    )
                    result, message, diff_text = (
                        manager.install_additional_file_from_content(
                            merged_content,
                            additional_file.target_path,
                            dry_run=ctx.dry_run,
                            backup_dir=additional_file.backup_dir,
                            force=ctx.force,
                        )
                    )
                else:
                    result, message, diff_text = manager.install_additional_file(
                        additional_file.source_path,
                        additional_file.target_path,
                        dry_run=ctx.dry_run,
                        backup_dir=additional_file.backup_dir,
                        force=ctx.force,
                    )
                print_operation_result(result, message)
                if diff_text and result == OperationResult.UPDATED:
                    print_diff(diff_text)
                additional_file_results[str(additional_file.target_path)] = result

        preferences_results: dict[str, OperationResult] = {}
        for shell in ctx.selected_shells:
            preferences_files = shell.get_preferences_files()
            for pref_file in preferences_files:
                result, message, diff_text = manager.install_preferences_file(
                    pref_file.source_path,
                    pref_file.domain,
                    dry_run=ctx.dry_run,
                    app_name=pref_file.app_name,
                    force=ctx.force,
                )
                print_operation_result(result, message)
                if diff_text and result == OperationResult.UPDATED:
                    print_diff(diff_text)
                preferences_results[pref_file.name] = result

        if ctx.dry_run:
            print_hint("Use without --dry-run to apply changes.")

        success_count = sum(
            1
            for r in results.values()
            if r in [OperationResult.CREATED, OperationResult.UPDATED]
        )
        additional_success_count = sum(
            1
            for r in additional_file_results.values()
            if r in [OperationResult.CREATED, OperationResult.UPDATED]
        )
        preferences_success_count = sum(
            1
            for r in preferences_results.values()
            if r in [OperationResult.CREATED, OperationResult.UPDATED]
        )
        total_success = (
            success_count + additional_success_count + preferences_success_count
        )

        if total_success > 0 and not ctx.dry_run:
            print_info(f"Successfully installed/updated {total_success} file(s)")
        elif not plan.has_changes and not ctx.dry_run:
            print_info("All configurations already in sync")

        if not ctx.dry_run and ctx.profile_name is not None:
            save_auto_update_config(
                auto_update_config.__class__(
                    backup_retention=auto_update_config.backup_retention,
                    active_profile=ctx.profile_name,
                )
            )

        return True

    def install(self, ctx: Context) -> bool:
        import click

        from shell_configs.display import console, print_info

        configs_plan = self.plan(ctx)

        if not ctx.yes or ctx.dry_run:
            self.display_plan(configs_plan)

            if configs_plan.has_changes and not ctx.dry_run:
                console.print()
                if not click.confirm("Apply these changes?"):
                    print_info("Installation cancelled")
                    return False

        return self.apply(ctx, configs_plan)

    def diff(self, ctx: Context) -> bool:
        configs_plan = self.plan(ctx)
        self.display_plan(configs_plan)
        return configs_plan.has_changes

    def status(self, ctx: Context) -> None:
        from pathlib import Path

        from shell_configs.bootstrap import load_auto_update_config
        from shell_configs.display import (
            add_additional_file_row,
            add_status_row,
            console,
            create_status_table,
            get_status_indicator,
        )
        from shell_configs.manager import ConfigManager
        from shell_configs.shells.base import merge_json_with_profile

        auto_update_config = load_auto_update_config()
        manager = ConfigManager(backup_retention=auto_update_config.backup_retention)

        table = create_status_table()
        home = str(Path.home())

        for shell in ctx.selected_shells:
            has_shown_name = False

            for config_file in shell.get_config_files():
                repo_content = ctx.config_reader.get_config_content(
                    shell.name, config_file.repo_config_name, profile=ctx.profile
                )
                shared_content = None
                if shell.supports_shared_config():
                    shared_content = ctx.config_reader.get_shared_config_content(
                        shell.name, profile=ctx.profile
                    )

                if repo_content is None and shared_content is not None:
                    repo_content = ""
                elif repo_content is None:
                    continue

                repo_content = manager.combine_content(shared_content, repo_content)

                section = manager.extract_managed_section(config_file.path)
                exists = section is not None
                synced = (
                    (exists and section.content.strip() == repo_content.strip())
                    if section
                    else False
                )

                status_str = get_status_indicator(synced, exists)
                path_display = str(config_file.path).replace(home, "~")
                add_status_row(table, shell.display_name, path_display, status_str)
                has_shown_name = True

            additional_files = shell.get_additional_files()
            for i, additional_file in enumerate(additional_files):
                if additional_file.xml_guiconfig_merge:
                    exists = additional_file.target_path.exists()
                    synced = manager.check_xml_guiconfig_synced(
                        additional_file.source_path,
                        additional_file.target_path,
                    )
                elif additional_file.ini_merge:
                    exists = additional_file.target_path.exists()
                    synced = manager.check_ini_file_synced(
                        additional_file.source_path,
                        additional_file.target_path,
                    )
                elif additional_file.comment_prefix:
                    source_content = (
                        additional_file.source_path.read_text()
                        if additional_file.source_path.exists()
                        else None
                    )
                    section = manager.extract_managed_section(
                        additional_file.target_path,
                        comment_prefix=additional_file.comment_prefix,
                    )
                    exists = section is not None
                    synced = (
                        manager.managed_content_matches(section.content, source_content)
                        if section and source_content
                        else False
                    )
                else:
                    exists = additional_file.target_path.exists()
                    if additional_file.target_merge:
                        from shell_configs.shells.base import merge_json_into_target

                        _, synced = merge_json_into_target(
                            additional_file.source_path,
                            additional_file.target_path,
                        )
                    elif additional_file.base_source_path:
                        profile_overrides = (
                            ctx.profile.settings_overrides.get(shell.name)
                            if ctx.profile
                            else None
                        )
                        merged_content = merge_json_with_profile(
                            additional_file.base_source_path,
                            additional_file.source_path,
                            profile_overrides,
                        )
                        synced = manager.content_matches(
                            merged_content, additional_file.target_path
                        )
                    else:
                        synced = manager.files_match(
                            additional_file.source_path, additional_file.target_path
                        )
                status_str = get_status_indicator(synced, exists)
                path_display = str(additional_file.target_path).replace(home, "~")

                if i == 0 and not has_shown_name:
                    add_status_row(table, shell.display_name, path_display, status_str)
                    has_shown_name = True
                else:
                    add_additional_file_row(table, path_display, status_str)

            preferences_files = shell.get_preferences_files()
            for i, pref_file in enumerate(preferences_files):
                exists, synced = manager.check_preferences_file_status(
                    pref_file.source_path, pref_file.domain
                )
                status_str = get_status_indicator(synced, exists)
                path_display = f"{pref_file.domain} (preferences)"

                if i == 0 and not has_shown_name:
                    add_status_row(table, shell.display_name, path_display, status_str)
                    has_shown_name = True
                else:
                    add_additional_file_row(table, path_display, status_str)

        console.print(table)
        console.print()

    def uninstall(self, ctx: Context) -> None:
        from shell_configs.bootstrap import load_auto_update_config
        from shell_configs.display import print_operation_result
        from shell_configs.manager import ConfigManager, OperationResult

        auto_update_config = load_auto_update_config()
        manager = ConfigManager(backup_retention=auto_update_config.backup_retention)

        for shell in ctx.selected_shells:
            for config_file in shell.get_config_files():
                result, message = manager.uninstall_section(config_file.path)
                if result != OperationResult.NOT_FOUND:
                    print_operation_result(result, message)

        for shell in ctx.selected_shells:
            additional_files = shell.get_additional_files()
            for additional_file in additional_files:
                if additional_file.xml_guiconfig_merge:
                    result, message = manager.uninstall_xml_guiconfig_file(
                        additional_file.source_path,
                        additional_file.target_path,
                    )
                elif additional_file.ini_merge:
                    result, message = manager.uninstall_ini_file(
                        additional_file.target_path,
                    )
                elif additional_file.comment_prefix:
                    result, message = manager.uninstall_section(
                        additional_file.target_path,
                        comment_prefix=additional_file.comment_prefix,
                    )
                else:
                    result, message = manager.uninstall_additional_file(
                        additional_file.target_path,
                        backup_dir=additional_file.backup_dir,
                    )
                if result != OperationResult.NOT_FOUND:
                    print_operation_result(result, message)

        for shell in ctx.selected_shells:
            preferences_files = shell.get_preferences_files()
            for pref_file in preferences_files:
                result, message = manager.uninstall_preferences_file(
                    pref_file.source_path,
                    pref_file.domain,
                    app_name=pref_file.app_name,
                )
                if result != OperationResult.NOT_FOUND:
                    print_operation_result(result, message)
