"""ConfigsComponent — manages shell config file installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import Component, ComponentPlan, ConfigsPlan, Context


class ConfigsComponent(Component):
    label = "configs"
    display_name = "Configs"

    def plan(self, ctx: Context) -> ConfigsPlan:
        from shell_configs.bootstrap import load_auto_update_config
        from shell_configs.cli.helpers import _compute_diffs_for_shells
        from shell_configs.manager import (
            AdditionalFileManifest,
            ConfigManager,
            get_default_additional_manifest_path,
        )

        auto_update_config = load_auto_update_config()
        manager = ConfigManager(backup_retention=auto_update_config.backup_retention)
        diffs = _compute_diffs_for_shells(ctx, manager)

        additional_manifest = AdditionalFileManifest(
            get_default_additional_manifest_path()
        )
        if additional_manifest.is_new:
            orphaned_additional_files: list[str] = []
        else:
            current_targets = {
                str(af.target_path)
                for shell in ctx.selected_shells
                for af in shell.get_additional_files()
            }
            orphaned_additional_files = additional_manifest.find_orphans(
                current_targets
            )

        from shell_configs.cli.context import StateDbChange
        from shell_configs.shells.state_db import (
            read_state_db_value,
            values_match,
        )

        state_db_changes: list[StateDbChange] = []
        for shell in ctx.selected_shells:
            for entry in shell.get_state_db_entries():
                current = read_state_db_value(entry.db_path, entry.key)
                is_synced = current is not None and values_match(current, entry.value)
                if not is_synced:
                    state_db_changes.append(
                        StateDbChange(
                            shell_name=shell.display_name,
                            entry_name=entry.name,
                            db_path=str(entry.db_path),
                            key=entry.key,
                            current_value=current,
                            desired_value=entry.value,
                        )
                    )

        return ConfigsPlan(
            has_changes=bool(diffs)
            or bool(orphaned_additional_files)
            or bool(state_db_changes),
            diffs=diffs,
            orphaned_additional_files=orphaned_additional_files,
            state_db_changes=state_db_changes,
        )

    def display_plan(self, plan: ComponentPlan) -> None:
        from shell_configs.cli.helpers import _render_diffs
        from shell_configs.display import console, print_section

        if not isinstance(plan, ConfigsPlan):
            raise TypeError(f"expected ConfigsPlan, got {type(plan).__name__}")
        _render_diffs(plan.diffs)
        if plan.orphaned_additional_files:
            print_section("Orphaned Additional Files")
            for path_str in plan.orphaned_additional_files:
                console.print(f"  {path_str}: [red]orphaned (source removed)[/red]")
        if plan.state_db_changes:
            print_section("State Database Changes")
            for change in plan.state_db_changes:
                current_display = (
                    change.current_value
                    if change.current_value is not None
                    else "(not set)"
                )
                console.print(
                    f"  [bold]{change.shell_name}[/bold] {change.entry_name}: "
                    f"[red]{current_display}[/red] → [green]{change.desired_value}[/green]"
                )

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

        from shell_configs.manager import (
            AdditionalFileManifest,
            get_default_additional_manifest_path,
        )

        additional_manifest = AdditionalFileManifest(
            get_default_additional_manifest_path()
        )
        is_first_manifest_run = additional_manifest.is_new

        for shell in ctx.selected_shells:
            additional_files = shell.get_additional_files()
            for additional_file in additional_files:
                is_merge_mode = bool(
                    additional_file.xml_guiconfig_merge
                    or additional_file.ini_merge
                    or additional_file.comment_prefix
                    or additional_file.target_merge
                )
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
                if not ctx.dry_run and result not in (
                    OperationResult.NOT_FOUND,
                    OperationResult.ERROR,
                ):
                    additional_manifest.record_install(
                        str(additional_file.target_path),
                        shell.name,
                        owned_file=not is_merge_mode,
                    )

        if not is_first_manifest_run and not ctx.dry_run:
            from pathlib import Path

            for target_str in plan.orphaned_additional_files:
                entry = additional_manifest.files.get(target_str)
                if entry and entry.owned_file:
                    orphan_result, orphan_msg = manager.uninstall_additional_file(
                        Path(target_str)
                    )
                    if orphan_result != OperationResult.NOT_FOUND:
                        print_operation_result(orphan_result, orphan_msg)
                    # Only remove the manifest entry when the file was actually gone or
                    # successfully deleted; keep it if uninstall failed so the orphan
                    # is re-detected on the next run.
                    if orphan_result in (
                        OperationResult.REMOVED,
                        OperationResult.NOT_FOUND,
                    ):
                        additional_manifest.remove(target_str)
                # Non-owned (merge-mode) orphans: keep the manifest entry — we lack
                # enough context here to invoke the correct uninstall_* method.

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

        state_db_results: dict[str, OperationResult] = {}
        if plan.state_db_changes:
            from pathlib import Path as _Path

            from shell_configs.shells.state_db import write_state_db_value

            for change in plan.state_db_changes:
                if ctx.dry_run:
                    print_operation_result(
                        OperationResult.UPDATED, f"Would update: {change.key}"
                    )
                    state_db_results[change.key] = OperationResult.UPDATED
                else:
                    result, message = write_state_db_value(
                        _Path(change.db_path), change.key, change.desired_value
                    )
                    print_operation_result(result, message)
                    if result == OperationResult.ERROR and "locked" in message.lower():
                        print_warning(
                            "Close the editor and re-run 'shell-configs install' to apply",
                            indent=2,
                        )
                    state_db_results[change.key] = result

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
        state_db_success_count = sum(
            1
            for r in state_db_results.values()
            if r in [OperationResult.CREATED, OperationResult.UPDATED]
        )
        total_success = (
            success_count
            + additional_success_count
            + preferences_success_count
            + state_db_success_count
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

        if not ctx.dry_run:
            additional_manifest.save()

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

            from shell_configs.shells.state_db import (
                read_state_db_value as _read_state_db_value,
            )
            from shell_configs.shells.state_db import (
                values_match as _state_db_values_match,
            )

            state_db_entries = shell.get_state_db_entries()
            for i, entry in enumerate(state_db_entries):
                exists = entry.db_path.exists()
                current = (
                    _read_state_db_value(entry.db_path, entry.key) if exists else None
                )
                synced = current is not None and _state_db_values_match(
                    current, entry.value
                )
                status_str = get_status_indicator(synced, exists or current is not None)
                path_display = str(entry.db_path).replace(home, "~")
                label = f"{path_display} ({entry.name})"
                if i == 0 and not has_shown_name:
                    add_status_row(table, shell.display_name, label, status_str)
                    has_shown_name = True
                else:
                    add_additional_file_row(table, label, status_str)

        console.print(table)

        from shell_configs.manager import (
            AdditionalFileManifest,
            get_default_additional_manifest_path,
        )

        additional_manifest = AdditionalFileManifest(
            get_default_additional_manifest_path()
        )
        if not additional_manifest.is_new:
            from shell_configs.display import print_warning

            current_targets = {
                str(af.target_path)
                for shell in ctx.selected_shells
                for af in shell.get_additional_files()
            }
            orphaned = additional_manifest.find_orphans(current_targets)
            if orphaned:
                print_warning(
                    f"{len(orphaned)} orphaned additional file(s) no longer in config"
                    " — run 'shell-configs install' to clean up",
                    indent=2,
                )

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

        # Remove shell completions (same RC files, must run sequentially)
        from shell_configs.completions import (
            detect_shell,
            find_config_file,
            uninstall_completion,
        )

        detected_shell = detect_shell()
        if detected_shell:
            config_path = find_config_file(detected_shell)
            if config_path:
                result_ok, msg = uninstall_completion(config_path)
                if result_ok:
                    print_operation_result(OperationResult.REMOVED, msg)
