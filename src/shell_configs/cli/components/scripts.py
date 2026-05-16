"""ScriptsComponent — utility script installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import Component, ComponentPlan, Context, ScriptsPlan


class ScriptsComponent(Component):
    label = "scripts"
    display_name = "Scripts"

    def plan(self, ctx: Context) -> ScriptsPlan:
        from shell_configs.script_manager import (
            ScriptManifest,
            ScriptStatus,
            discover_scripts,
            get_default_manifest_path,
            get_default_target_dir,
            get_script_status,
        )

        target_dir = get_default_target_dir()
        manifest = ScriptManifest(get_default_manifest_path())
        entries = [
            (entry, get_script_status(entry, target_dir, manifest))
            for entry in discover_scripts()
        ]
        has_changes = any(status != ScriptStatus.INSTALLED for _, status in entries)
        return ScriptsPlan(has_changes=has_changes, entries=entries)

    def display_plan(self, plan: ComponentPlan) -> None:
        if not isinstance(plan, ScriptsPlan):
            raise TypeError(f"expected ScriptsPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return

        from shell_configs.display import console
        from shell_configs.script_manager import ScriptStatus, get_default_target_dir

        target_dir = get_default_target_dir()
        status_labels = {
            ScriptStatus.MISSING: "[red]not installed[/red]",
            ScriptStatus.OUTDATED: "[yellow]outdated[/yellow]",
            ScriptStatus.MODIFIED: "[yellow]modified[/yellow]",
            ScriptStatus.COLLISION: "[yellow]exists (not ours)[/yellow]",
        }

        console.print(f"\n[bold cyan]{self.display_name}[/bold cyan]\n")
        for entry, st in plan.entries:
            if st != ScriptStatus.INSTALLED:
                label = status_labels.get(st, st.value)
                console.print(f"  {target_dir / entry.name}: {label}")

    def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
        if not isinstance(plan, ScriptsPlan):
            raise TypeError(f"expected ScriptsPlan, got {type(plan).__name__}")
        if not plan.has_changes:
            return True

        from shell_configs.script_manager import (
            InstallResult,
            ScriptManifest,
            ScriptStatus,
            get_default_manifest_path,
            get_default_target_dir,
            install_script,
        )

        target_dir = get_default_target_dir()
        manifest = ScriptManifest(get_default_manifest_path())
        success = True
        for entry, status in plan.entries:
            if status == ScriptStatus.INSTALLED:
                continue
            result, _ = install_script(entry, target_dir, manifest, dry_run=False)
            if result not in (
                InstallResult.INSTALLED,
                InstallResult.UPDATED,
                InstallResult.ALREADY_SYNCED,
                InstallResult.COLLISION,
                InstallResult.SKIPPED_PLATFORM,
            ):
                success = False
        return success

    def install(self, ctx: Context) -> bool:
        from shell_configs.display import (
            console,
            print_done,
            print_error,
            print_progress,
            print_success,
            print_warning,
            print_would,
        )
        from shell_configs.script_manager import (
            InstallResult,
            ScriptManifest,
            discover_scripts,
            get_default_manifest_path,
            get_default_target_dir,
            install_script,
        )

        console.print()
        print_progress("Installing utility scripts...")
        target_dir = get_default_target_dir()
        manifest = ScriptManifest(get_default_manifest_path())
        entries = discover_scripts()
        if not entries:
            console.print("[dim]No scripts available for this platform[/dim]")
        else:
            for entry in entries:
                script_result, msg = install_script(
                    entry, target_dir, manifest, dry_run=ctx.dry_run
                )
                if script_result == InstallResult.COLLISION:
                    print_warning(msg)
                elif script_result in (InstallResult.INSTALLED, InstallResult.UPDATED):
                    print_success(msg)
                elif script_result == InstallResult.ALREADY_SYNCED:
                    print_done(msg)
                elif script_result in (
                    InstallResult.WOULD_INSTALL,
                    InstallResult.WOULD_UPDATE,
                ):
                    print_would(msg)
                elif script_result == InstallResult.SKIPPED_PLATFORM:
                    pass
                else:
                    print_error(msg)

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.script_manager import ScriptStatus

        plan = self.plan(ctx)

        total = len(plan.entries)
        installed = sum(1 for _, st in plan.entries if st == ScriptStatus.INSTALLED)

        if total == 0:
            console.print("  [dim]No scripts available for this platform[/dim]")
        elif installed == total:
            from shell_configs.display import print_success

            print_success(
                f"{installed}/{total} scripts installed (~/.local/bin)", indent=2
            )
        else:
            from shell_configs.display import print_hint, print_warning

            print_warning(
                f"{installed}/{total} scripts installed ({total - installed} missing)",
                indent=2,
            )
            print_hint("Run 'shell-configs scripts status' for details")

        console.print()

    def diff(self, ctx: Context) -> bool:
        plan = self.plan(ctx)
        self.display_plan(plan)
        return plan.has_changes

    def uninstall(self, ctx: Context) -> None:
        from shell_configs.display import print_operation_result, print_warning
        from shell_configs.manager import OperationResult
        from shell_configs.script_manager import (
            ScriptManifest,
            UninstallResult,
            get_default_manifest_path,
            get_default_target_dir,
            uninstall_script,
        )

        manifest = ScriptManifest(get_default_manifest_path())
        if manifest.scripts:
            target_dir = get_default_target_dir()
            for name in list(manifest.scripts.keys()):
                script_result, message = uninstall_script(
                    name, target_dir, manifest, force=True
                )
                if script_result == UninstallResult.REMOVED:
                    print_operation_result(OperationResult.REMOVED, message)
                elif script_result == UninstallResult.NOT_FOUND:
                    pass
                else:
                    print_warning(message)
