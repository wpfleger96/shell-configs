"""ScriptsComponent — utility script installation, status, and diff."""

from __future__ import annotations

from shell_configs.cli.context import Component, Context


class ScriptsComponent(Component):
    label = "scripts"

    def install(self, ctx: Context) -> bool:
        from shell_configs.display import console
        from shell_configs.script_manager import (
            InstallResult,
            ScriptManifest,
            discover_scripts,
            get_default_manifest_path,
            get_default_target_dir,
            install_script,
        )

        console.print()
        console.print("[yellow]Installing utility scripts...[/yellow]")
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
                    console.print(f"[yellow]⚠[/yellow] {msg}")
                elif script_result in (
                    InstallResult.INSTALLED,
                    InstallResult.UPDATED,
                    InstallResult.ALREADY_SYNCED,
                ):
                    console.print(f"[green]✓[/green] {msg}")
                elif script_result in (
                    InstallResult.WOULD_INSTALL,
                    InstallResult.WOULD_UPDATE,
                ):
                    console.print(f"[dim]→[/dim] {msg}")
                elif script_result == InstallResult.SKIPPED_PLATFORM:
                    pass
                else:
                    console.print(f"[red]✗[/red] {msg}")

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.script_manager import (
            ScriptManifest,
            ScriptStatus,
            discover_scripts,
            get_default_manifest_path,
            get_default_target_dir,
            get_script_status,
        )

        console.print("[bold cyan]Scripts[/bold cyan]\n")

        scripts_target = get_default_target_dir()
        scripts_manifest = ScriptManifest(get_default_manifest_path())
        script_entries = discover_scripts()
        scripts_installed = sum(
            1
            for e in script_entries
            if get_script_status(e, scripts_target, scripts_manifest)
            == ScriptStatus.INSTALLED
        )
        scripts_total = len(script_entries)
        if scripts_total == 0:
            console.print("  [dim]No scripts available for this platform[/dim]")
        elif scripts_installed == scripts_total:
            console.print(
                f"  [green]✓[/green] {scripts_installed}/{scripts_total} scripts installed (~/.local/bin)"
            )
        else:
            console.print(
                f"  [yellow]⚠[/yellow] {scripts_installed}/{scripts_total} scripts installed "
                f"({scripts_total - scripts_installed} missing)"
            )
            console.print("  [dim]Run 'shell-configs scripts status' for details[/dim]")

        console.print()

    def diff(self, ctx: Context) -> bool:
        from shell_configs.display import console
        from shell_configs.script_manager import (
            ScriptManifest,
            ScriptStatus,
            discover_scripts,
            get_default_manifest_path,
            get_default_target_dir,
            get_script_status,
        )

        scripts_target = get_default_target_dir()
        scripts_manifest = ScriptManifest(get_default_manifest_path())
        out_of_sync = []
        for entry in discover_scripts():
            st = get_script_status(entry, scripts_target, scripts_manifest)
            if st != ScriptStatus.INSTALLED:
                out_of_sync.append((entry, st))

        if not out_of_sync:
            return False

        console.print("\n[bold cyan]Scripts[/bold cyan]\n")
        status_labels = {
            ScriptStatus.MISSING: "[red]not installed[/red]",
            ScriptStatus.OUTDATED: "[yellow]outdated[/yellow]",
            ScriptStatus.MODIFIED: "[yellow]modified[/yellow]",
            ScriptStatus.COLLISION: "[yellow]exists (not ours)[/yellow]",
        }
        for entry, st in out_of_sync:
            label = status_labels.get(st, st.value)
            console.print(f"  {scripts_target / entry.name}: {label}")
        return True

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
