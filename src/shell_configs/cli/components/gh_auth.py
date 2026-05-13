"""GhAuthComponent — GitHub CLI auth and OAuth scope setup."""

from __future__ import annotations

import sys

from shell_configs.cli.context import Component, Context


class GhAuthComponent(Component):
    label = "gh-auth"

    def install(self, ctx: Context) -> bool:
        if ctx.dry_run:
            return True

        from shell_configs.display import console
        from shell_configs.signing import ensure_gh_auth, ensure_gh_scopes

        console.print()
        console.print("[yellow]Ensuring GitHub CLI auth and scopes...[/yellow]")

        interactive = sys.stdin.isatty()

        auth_ok, auth_msg = ensure_gh_auth(interactive=interactive)
        if auth_ok:
            console.print(f"[green]✓[/green] {auth_msg}")
        else:
            console.print(f"[red]✗[/red] {auth_msg}")
            return False

        scopes_ok, scopes_msg = ensure_gh_scopes(interactive=interactive)
        if scopes_ok:
            console.print(f"[green]✓[/green] {scopes_msg}")
        else:
            console.print(f"[red]✗[/red] {scopes_msg}")
            return False

        return True

    def status(self, ctx: Context) -> None:
        from shell_configs.display import console
        from shell_configs.signing import ensure_gh_auth, ensure_gh_scopes

        console.print("[bold cyan]GitHub CLI Auth[/bold cyan]\n")

        auth_ok, auth_msg = ensure_gh_auth(interactive=False)
        if auth_ok:
            console.print(f"  [green]✓[/green] {auth_msg}")
        else:
            console.print(f"  [yellow]⚠[/yellow] {auth_msg}")

        if auth_ok:
            scopes_ok, scopes_msg = ensure_gh_scopes(interactive=False)
            if scopes_ok:
                console.print(f"  [green]✓[/green] {scopes_msg}")
            else:
                console.print(f"  [yellow]⚠[/yellow] {scopes_msg}")

        console.print()

    def diff(self, ctx: Context) -> bool:
        import subprocess

        from shell_configs.display import console
        from shell_configs.gh_auth import load_desired_scopes
        from shell_configs.signing import ensure_gh_auth, ensure_gh_scopes

        auth_ok, _ = ensure_gh_auth(interactive=False)
        if not auth_ok:
            return False

        scopes_ok, _ = ensure_gh_scopes(interactive=False)
        if scopes_ok:
            return False

        desired = load_desired_scopes()

        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        current_scopes: set[str] = set()
        if result.returncode == 0:
            output = f"{result.stdout}\n{result.stderr}"
            for line in output.splitlines():
                if "Token scopes:" in line:
                    scopes_str = line.split("Token scopes:", 1)[1].strip()
                    current_scopes = {
                        s.strip().strip("'\"") for s in scopes_str.split(",")
                    }
                    break

        missing = [s for s in desired if s not in current_scopes]
        if not missing:
            return False

        console.print("\n[bold cyan]GitHub CLI Auth Scopes[/bold cyan]\n")
        for scope in missing:
            console.print(f"  [yellow]⚠[/yellow] {scope} (missing)")
        return True
