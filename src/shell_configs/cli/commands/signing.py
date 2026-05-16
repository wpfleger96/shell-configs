"""Signing subcommand (top-level command under cli)."""

from __future__ import annotations

import sys

import click


@click.command()
@click.option(
    "--fix",
    is_flag=True,
    help="Run full SSH key lifecycle (generate, auth, upload, sign)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed key information")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm without prompting")
@click.option(
    "--cleanup",
    is_flag=True,
    help="Find and remove stale SSH keys from GitHub",
)
def signing(fix: bool, verbose: bool, yes: bool, cleanup: bool) -> None:
    """Validate and manage SSH key lifecycle with GitHub."""
    from shell_configs.display import console, print_error, print_success, print_warning
    from shell_configs.signing import (
        get_signing_key_info,
        setup_signing,
    )

    if cleanup:
        from shell_configs.signing import (
            delete_github_key_by_fingerprint,
            discover_managed_key,
            find_local_ssh_keys,
            find_stale_github_keys,
            get_github_key_fingerprints,
        )

        local_keys = find_local_ssh_keys()
        github_fps = get_github_key_fingerprints()
        managed_key = discover_managed_key(local_keys, github_fps)
        if not managed_key:
            print_error(
                "Could not determine managed SSH key. "
                "Run 'shell-configs signing --fix' first"
            )
            sys.exit(1)

        stale_keys, current_fp = find_stale_github_keys(managed_key)
        if not current_fp:
            print_error("Could not read local SSH key fingerprint")
            sys.exit(1)

        console.print(f"[dim]Current key fingerprint: {current_fp}[/dim]\n")

        if not stale_keys:
            print_success("No stale SSH keys found on GitHub")
            return

        print_warning(f"Found {len(stale_keys)} stale key(s) on GitHub:\n")
        for key in stale_keys:
            console.print(f"  {key.title}  {key.key_type}  {key.fingerprint}")
        console.print()

        for key in stale_keys:
            if yes or click.confirm(
                f"Remove '{key.title}' ({key.fingerprint})?", default=False
            ):
                ok, msg = delete_github_key_by_fingerprint(key.fingerprint)
                if ok:
                    print_success(msg)
                else:
                    print_error(msg)
            else:
                console.print(f"[dim]Skipped: {key.title}[/dim]")
        return

    interactive = sys.stdin.isatty() if not yes else False
    results = setup_signing(auto_fix=fix, interactive=interactive)

    has_failure = False
    for r in results:
        if r.skipped:
            print_warning(r.message)
        elif r.success:
            print_success(r.message)
        else:
            print_error(r.message)
            has_failure = True

    if verbose and not has_failure:
        info = get_signing_key_info()
        if info:
            console.print()
            console.print("[bold cyan]Signing Key Details[/bold cyan]")
            console.print(f"  Key type:      {info['key_type']}")
            console.print(f"  Fingerprint:   {info['fingerprint']}")
            console.print(f"  GitHub title:  {info['github_title'] or 'N/A'}")
            console.print(f"  Git name:      {info['git_name']}")
            console.print(f"  Git email:     {info['git_email']}")
            if info["comment"]:
                console.print(f"  Key comment:   {info['comment']}")

    if has_failure:
        sys.exit(1)
