"""Shared install/uninstall helpers for manifest-driven tools.

Consolidates the platform-config parsing/resolution and the
which-check → dry-run → subprocess → message pattern previously
duplicated across the agents and languages modules.
"""

from __future__ import annotations

import shutil
import subprocess

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from shell_configs.platform import Platform, is_platform

NPM_MISSING_MSG = "npm is not available — install Node.js first, then re-run"


@dataclass(frozen=True)
class PlatformInstallConfig:
    method: str  # "npm", "brew", "apt", or "winget"
    package: str | None = None


def parse_platform_configs(
    entry: dict[str, Any],
) -> tuple[
    PlatformInstallConfig | None,
    PlatformInstallConfig | None,
    PlatformInstallConfig | None,
]:
    """Extract (macos, linux, windows) install configs from a manifest entry."""

    def _parse(key: str) -> PlatformInstallConfig | None:
        raw = entry.get(key)
        if not isinstance(raw, dict):
            return None
        return PlatformInstallConfig(
            method=raw.get("method", ""),
            package=raw.get("package") or None,
        )

    return _parse("macos"), _parse("linux"), _parse("windows")


def resolve_platform_config(
    *,
    macos: PlatformInstallConfig | None,
    linux: PlatformInstallConfig | None,
    windows: PlatformInstallConfig | None,
) -> PlatformInstallConfig | None:
    """Pick the install config for the current platform (WSL uses linux)."""
    if is_platform(Platform.MACOS) and macos:
        return macos
    if is_platform(Platform.WINDOWS) and windows:
        return windows
    if (is_platform(Platform.WSL) or is_platform(Platform.LINUX)) and linux:
        return linux
    return None


def _run_step(
    cmd: list[str] | str,
    *,
    name: str,
    verb: str,
    via: str | None,
    dry_run: bool,
    would_msg: str,
    timeout: int = 300,
) -> tuple[bool, str]:
    """Run an install/uninstall command with uniform dry-run/timeout handling."""
    if dry_run:
        return True, would_msg
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        what = via or f"{verb} script"
        return False, f"Failed to {verb} {name}: {what} timed out"
    if result.returncode == 0:
        suffix = f" via {via}" if via else ""
        return True, f"{verb.capitalize()}ed {name}{suffix}"
    return False, f"Failed to {verb} {name}: {result.stderr.strip()}"


def install_npm(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("npm"):
        return False, NPM_MISSING_MSG
    return _run_step(
        ["npm", "install", "-g", package],
        name=name,
        verb="install",
        via="npm",
        dry_run=dry_run,
        would_msg=f"Would install {package} via npm install -g",
    )


def uninstall_npm(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("npm"):
        return False, NPM_MISSING_MSG
    return _run_step(
        ["npm", "uninstall", "-g", package],
        name=name,
        verb="uninstall",
        via="npm",
        dry_run=dry_run,
        would_msg=f"Would uninstall {package} via npm uninstall -g",
    )


def install_winget(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("winget"):
        return False, "winget is not available"
    return _run_step(
        [
            "winget",
            "install",
            package,
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--silent",
        ],
        name=name,
        verb="install",
        via="winget",
        dry_run=dry_run,
        would_msg=f"Would install {package} via winget",
    )


def uninstall_winget(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("winget"):
        return False, "winget is not available"
    return _run_step(
        ["winget", "uninstall", package, "--silent"],
        name=name,
        verb="uninstall",
        via="winget",
        dry_run=dry_run,
        would_msg=f"Would uninstall {package} via winget",
    )


def install_brew(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("brew"):
        return False, "brew is not available"
    return _run_step(
        ["brew", "install", package],
        name=name,
        verb="install",
        via="brew",
        dry_run=dry_run,
        would_msg=f"Would install {package} via brew",
    )


def install_apt(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("apt"):
        return False, "apt is not available"
    return _run_step(
        ["sudo", "apt-get", "install", "-y", package],
        name=name,
        verb="install",
        via="apt",
        dry_run=dry_run,
        would_msg=f"Would install {package} via apt",
    )


def run_script(
    name: str, cmd: str, dry_run: bool, verb: str = "install"
) -> tuple[bool, str]:
    """Run a shell install/uninstall script command."""
    return _run_step(
        cmd,
        name=name,
        verb=verb,
        via=None,
        dry_run=dry_run,
        would_msg=f"Would {verb} {name} via: {cmd}",
    )


_INSTALL_BY_METHOD: dict[str, Callable[[str, str, bool], tuple[bool, str]]] = {
    "npm": install_npm,
    "brew": install_brew,
    "apt": install_apt,
    "winget": install_winget,
}

_UNINSTALL_BY_METHOD: dict[str, Callable[[str, str, bool], tuple[bool, str]]] = {
    "npm": uninstall_npm,
    "winget": uninstall_winget,
}


def install_via_config(
    name: str,
    config: PlatformInstallConfig,
    dry_run: bool,
    *,
    methods: frozenset[str],
) -> tuple[bool, str]:
    """Install via the method named in config, restricted to allowed methods."""
    fn = _INSTALL_BY_METHOD.get(config.method)
    if fn is None or config.method not in methods:
        return False, f"Unknown install method: {config.method}"
    return fn(name, config.package or name, dry_run)


def uninstall_via_config(
    name: str,
    config: PlatformInstallConfig,
    dry_run: bool,
    *,
    methods: frozenset[str],
) -> tuple[bool, str]:
    """Uninstall via the method named in config, restricted to allowed methods."""
    fn = _UNINSTALL_BY_METHOD.get(config.method)
    if fn is None or config.method not in methods:
        return False, f"Unknown install method: {config.method}"
    return fn(name, config.package or name, dry_run)
