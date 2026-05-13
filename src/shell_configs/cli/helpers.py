"""Shared helper functions for shell selection and diff display."""

from __future__ import annotations

import difflib
import sys

from concurrent.futures import FIRST_EXCEPTION, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from shell_configs.config import ConfigReader
from shell_configs.shells.base import merge_json_with_profile

if TYPE_CHECKING:
    from shell_configs.cli.context import Context, FileDiff
    from shell_configs.extensions import ExtensionResult
    from shell_configs.manager import ConfigManager
    from shell_configs.profiles.profile import Profile
    from shell_configs.shells.base import Shell
    from shell_configs.shells.registry import ShellRegistry


def parse_shell_filter(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> list[str] | None:
    """Parse shell filter from comma-separated string."""
    if not value:
        return None
    return [s.strip() for s in value.split(",")]


def build_context(
    profile_name: str | None,
    shells_filter: list[str] | None = None,
    config_dir: Path | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> Context | None:
    """Build a Context from common CLI parameters.

    Returns None when no shells are found (caller should warn and return).
    """
    from shell_configs.cli.context import Context
    from shell_configs.config import ConfigReader
    from shell_configs.profiles import ProfileLoader, resolve_active_profile
    from shell_configs.shells.registry import ShellRegistry

    config_reader = ConfigReader(config_dir=config_dir)
    registry = ShellRegistry()
    profile_loader = ProfileLoader(config_reader.config_dir)
    active_profile = resolve_active_profile(profile_name, profile_loader)
    selected_shells = _get_selected_shells(
        registry, shells_filter, config_reader=config_reader
    )
    if not selected_shells:
        return None
    return Context(
        dry_run=dry_run,
        yes=yes,
        profile_name=profile_name,
        profile=active_profile,
        selected_shells=tuple(selected_shells),
        config_reader=config_reader,
        registry=registry,
    )


def _get_selected_shells(
    registry: ShellRegistry,
    shells_filter: list[str] | None = None,
    config_reader: ConfigReader | None = None,
    use_all: bool = False,
) -> list[Shell]:
    """Get selected shells based on filter or available configs.

    Args:
        registry: ShellRegistry instance
        shells_filter: Optional list of shell names to filter
        config_reader: Optional ConfigReader for auto-detecting available shells
        use_all: If True and no filter, return all registered shells

    Returns:
        List of selected Shell instances, or exits on error

    Raises:
        SystemExit: If invalid shell names provided
    """
    from shell_configs.display import print_error, print_info

    if shells_filter:
        selected_shells, invalid = registry.filter_by_names(shells_filter)
        if invalid:
            print_error(f"Unknown shells: {', '.join(invalid)}")
            print_info(f"Available shells: {', '.join(registry.get_names())}")
            sys.exit(1)
    elif use_all:
        selected_shells = registry.get_all()
    elif config_reader:
        available = config_reader.get_available_shells()
        selected_shells, _ = registry.filter_by_names(available)
    else:
        selected_shells = []

    return selected_shells


def _get_extension_shells(
    registry: ShellRegistry,
    shells_filter: list[str] | None = None,
) -> list[Shell]:
    """Get shells that support extension management."""
    from shell_configs.display import print_error, print_info

    if shells_filter:
        selected, invalid = registry.filter_by_names(shells_filter)
        if invalid:
            print_error(f"Unknown shells: {', '.join(invalid)}")
            print_info(f"Available shells: {', '.join(registry.get_names())}")
            sys.exit(1)
    else:
        selected = registry.get_all()

    return [
        s
        for s in selected
        if s.get_extension_cli() is not None or s.get_extension_invoker() is not None
    ]


def _print_ignored_builtin_extensions(
    console: Any,
    shell_display_name: str,
    ignored_extensions: frozenset[str],
    *,
    header_printed: bool,
) -> bool:
    """Print a warning for builtin extensions listed in desired config."""
    if not ignored_extensions:
        return header_printed

    if not header_printed:
        console.print(f"\n[bold cyan]{shell_display_name}[/bold cyan]")
        header_printed = True

    ignored = ", ".join(sorted(ignored_extensions))
    console.print(
        f"  [yellow]! Ignoring built-in extensions from config: {ignored}[/yellow]"
    )
    return header_printed


def _print_extension_result(console: Any, result: ExtensionResult) -> None:
    """Render extension install/uninstall results consistently."""
    from shell_configs.extensions import ExtensionResultStatus

    if result.status == ExtensionResultStatus.SKIPPED_BUILTIN:
        console.print(f"  [yellow]![/yellow] {result.extension_id}: {result.message}")
    elif result.success:
        console.print(f"  [green]✓[/green] {result.message}")
    else:
        console.print(f"  [red]✗[/red] {result.extension_id}: {result.message}")


def _compute_diffs_for_shells(
    ctx: Context,
    manager: ConfigManager,
    console_obj: Any = None,
) -> list[FileDiff]:
    """Compute diffs for all selected shells without rendering anything.

    Returns a list of FileDiff objects describing every file that differs
    (or is not yet installed). Callers are responsible for display.
    """
    from shell_configs.cli.context import FileDiff

    diffs: list[FileDiff] = []
    config_reader = ctx.config_reader
    profile = ctx.profile

    for shell in ctx.selected_shells:
        for config_file in shell.get_config_files():
            repo_content = config_reader.get_config_content(
                shell.name, config_file.repo_config_name, profile=profile
            )
            if repo_content is None:
                continue

            shared_content = None
            if shell.supports_shared_config():
                shared_content = config_reader.get_shared_config_content(
                    shell.name, profile=profile
                )

            repo_content = manager.combine_content(shared_content, repo_content)
            section = manager.extract_managed_section(config_file.path)

            if section is None:
                diffs.append(
                    FileDiff(
                        shell_name=shell.display_name,
                        file_path=str(config_file.path),
                        diff_text="",
                        file_type="config",
                        current_content="",
                        desired_content=repo_content,
                    )
                )
                continue

            if section.content.strip() == repo_content.strip():
                continue

            installed_lines = section.content.splitlines(keepends=True)
            repo_lines = repo_content.splitlines(keepends=True)
            diff_text = "\n".join(
                difflib.unified_diff(
                    installed_lines,
                    repo_lines,
                    fromfile="Installed",
                    tofile="Repository",
                    lineterm="",
                )
            )
            diffs.append(
                FileDiff(
                    shell_name=shell.display_name,
                    file_path=str(config_file.path),
                    diff_text=diff_text,
                    file_type="config",
                    current_content=section.content,
                    desired_content=repo_content,
                )
            )

        additional_files = shell.get_additional_files()
        for additional_file in additional_files:
            if not additional_file.target_path.exists():
                diffs.append(
                    FileDiff(
                        shell_name=shell.display_name,
                        file_path=str(additional_file.target_path),
                        diff_text="",
                        file_type="additional",
                        current_content="",
                        desired_content="",
                    )
                )
                continue

            if additional_file.base_source_path:
                profile_overrides = (
                    profile.settings_overrides.get(shell.name) if profile else None
                )
                repo_content = merge_json_with_profile(
                    additional_file.base_source_path,
                    additional_file.source_path,
                    profile_overrides,
                )
            else:
                repo_content = additional_file.source_path.read_text()

            if additional_file.ini_merge:
                if manager.check_ini_file_synced(
                    additional_file.source_path, additional_file.target_path
                ):
                    continue
                ini_diff = manager.diff_ini_file(
                    additional_file.source_path, additional_file.target_path
                )
                if ini_diff:
                    diffs.append(
                        FileDiff(
                            shell_name=shell.display_name,
                            file_path=str(additional_file.target_path),
                            diff_text=ini_diff,
                            file_type="additional",
                            current_content="",
                            desired_content=repo_content,
                        )
                    )
                continue

            if additional_file.comment_prefix:
                section = manager.extract_managed_section(
                    additional_file.target_path,
                    comment_prefix=additional_file.comment_prefix,
                )
                if section is None:
                    diffs.append(
                        FileDiff(
                            shell_name=shell.display_name,
                            file_path=str(additional_file.target_path),
                            diff_text="",
                            file_type="additional",
                            current_content="",
                            desired_content=repo_content,
                        )
                    )
                    continue

                if manager.managed_content_matches(section.content, repo_content):
                    continue

                installed_content = section.content
                repo_content = manager.strip_json_outer_brackets(repo_content)
            else:
                if additional_file.base_source_path:
                    if manager.content_matches(
                        repo_content, additional_file.target_path
                    ):
                        continue
                else:
                    if manager.files_match(
                        additional_file.source_path, additional_file.target_path
                    ):
                        continue
                installed_content = additional_file.target_path.read_text()

            installed_lines = installed_content.splitlines(keepends=True)
            repo_lines = repo_content.splitlines(keepends=True)
            diff_text = "\n".join(
                difflib.unified_diff(
                    installed_lines,
                    repo_lines,
                    fromfile="Installed",
                    tofile="Repository",
                    lineterm="",
                )
            )
            diffs.append(
                FileDiff(
                    shell_name=shell.display_name,
                    file_path=str(additional_file.target_path),
                    diff_text=diff_text,
                    file_type="additional",
                    current_content=installed_content,
                    desired_content=repo_content,
                )
            )

        preferences_files = shell.get_preferences_files()
        for pref_file in preferences_files:
            pref_diff = manager.diff_preferences_file(
                pref_file.source_path, pref_file.domain
            )
            if pref_diff:
                diffs.append(
                    FileDiff(
                        shell_name=shell.display_name,
                        file_path=pref_file.domain,
                        diff_text=pref_diff,
                        file_type="preferences",
                        current_content="",
                        desired_content="",
                    )
                )

    return diffs


def _render_diffs(diffs: list[FileDiff], console_obj: Any = None) -> None:
    """Render a list of FileDiff objects to the console.

    Args:
        diffs: Diffs produced by _compute_diffs_for_shells.
        console_obj: Rich Console to use; falls back to the shared display console.
    """
    from rich.syntax import Syntax

    if console_obj is None:
        from shell_configs.display import console as console_obj

    for diff in diffs:
        if diff.file_type == "preferences":
            console_obj.print(
                f"\n[bold cyan]{diff.shell_name}[/bold cyan]: "
                f"{diff.file_path} (preferences)"
            )
            console_obj.print(diff.diff_text)
            continue

        console_obj.print(
            f"\n[bold cyan]{diff.shell_name}[/bold cyan]: {diff.file_path}"
        )

        if not diff.diff_text:
            console_obj.print("[yellow]Not installed[/yellow]")
            continue

        syntax = Syntax(diff.diff_text, "diff", theme="monokai")
        console_obj.print(syntax)


def _display_diffs_for_shells(
    selected_shells: list[Shell],
    config_reader: ConfigReader,
    manager: ConfigManager,
    profile: Profile | None = None,
) -> bool:
    """Display diffs for selected shells before install.

    Returns:
        True if diffs were found and displayed, False otherwise
    """
    from shell_configs.cli.context import Context
    from shell_configs.shells.registry import ShellRegistry

    ctx = Context(
        dry_run=False,
        yes=False,
        profile_name=None,
        profile=profile,
        selected_shells=tuple(selected_shells),
        config_reader=config_reader,
        registry=ShellRegistry(),
    )
    diffs = _compute_diffs_for_shells(ctx, manager)
    if diffs:
        _render_diffs(diffs)
    return bool(diffs)


def run_components_parallel(
    components: list,
    method: str,
    ctx: Context,
    plans: dict | None = None,
    max_workers: int | None = None,
) -> dict:
    """Run a component method across all components in parallel.

    Args:
        components: List of Component instances.
        method: Method name to call ("plan", "apply", "status").
        ctx: Context object (frozen, safe to share).
        plans: For "apply", the plan dict keyed by component.
        max_workers: Thread pool size (defaults to len(components)).

    Returns:
        Dict mapping component to its method's return value.
    """
    from rich.status import Status

    from shell_configs.display import console

    results: dict = {}
    futures: dict[Future, Any] = {}

    with ThreadPoolExecutor(max_workers=max_workers or len(components)) as pool:
        with Status(f"Running {method}...", console=console) as status:
            for component in components:
                if method == "apply":
                    plan = (plans or {})[component]
                    future = pool.submit(getattr(component, method), ctx, plan)
                else:
                    future = pool.submit(getattr(component, method), ctx)
                futures[future] = component

            done, not_done = wait(futures, return_when=FIRST_EXCEPTION)

            for future in not_done:
                future.cancel()

            for future in done:
                exc = future.exception()
                if exc is not None:
                    raise exc

            for future in done:
                component = futures[future]
                results[component] = future.result()
                status.update(
                    f"Running {method}... ({len(results)}/{len(components)} done)"
                )

    return results
