"""Language runtime management (Go, Rust, Node, Ruby, Python)."""

from __future__ import annotations

import os
import re
import subprocess

from dataclasses import dataclass
from pathlib import Path

import yaml

from shell_configs.bootstrap import is_command_available
from shell_configs.config import get_config_dir
from shell_configs.installers import (
    DEFAULT_TIMEOUT,
    PlatformInstallConfig,
    install_apt,
    install_brew,
    install_winget,
    parse_platform_configs,
    resolve_platform_config,
    run_script,
    run_via_config,
)

LanguageInstallConfig = PlatformInstallConfig

_LANGUAGE_INSTALL = {
    "brew": install_brew,
    "apt": install_apt,
    "winget": install_winget,
}


@dataclass(frozen=True)
class Language:
    name: str
    command: str
    description: str
    status_only: bool = False
    # Path checked for installation (e.g. ~/.cargo/bin/rustup,
    # ~/.nvm/versions/node/v*/bin/node; globs allowed). Necessary for tools that
    # aren't on PATH until their env is sourced. Must be an executable inside a
    # bin/ dir, because ensure_language_paths prepends its parent dir to PATH.
    check_path: str | None = None
    # Cross-platform curl/script install command (used when macos/linux are absent)
    install_cmd: str | None = None
    # Seconds install_cmd may run before it is killed
    install_timeout: int = DEFAULT_TIMEOUT
    macos: LanguageInstallConfig | None = None
    linux: LanguageInstallConfig | None = None
    windows: LanguageInstallConfig | None = None


def load_languages(manifest_path: Path | None = None) -> list[Language]:
    """Load desired language runtimes from the YAML manifest."""
    path = manifest_path or get_config_dir() / "languages.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    entries = data.get("languages") or []
    if not isinstance(entries, list):
        return []

    result: list[Language] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        command = entry.get("command", "")
        if not name or not command:
            continue

        macos_cfg, linux_cfg, windows_cfg = parse_platform_configs(entry)
        timeout = entry.get("install_timeout")

        result.append(
            Language(
                name=name,
                command=command,
                description=entry.get("description", ""),
                status_only=bool(entry.get("status_only", False)),
                check_path=entry.get("check_path") or None,
                install_cmd=entry.get("install_cmd") or None,
                install_timeout=(
                    timeout
                    if isinstance(timeout, int) and timeout > 0
                    else DEFAULT_TIMEOUT
                ),
                macos=macos_cfg,
                linux=linux_cfg,
                windows=windows_cfg,
            )
        )
    return result


def _natural_sort_key(path: Path) -> list[int | str]:
    """Sort key that compares digit runs numerically (``v9`` < ``v10``)."""
    return [
        int(part) if part.isdecimal() else part
        for part in re.split(r"(\d+)", str(path))
    ]


def _resolve_check_path(check_path: str) -> Path | None:
    """Resolve a check_path string to an existing Path, or None.

    Supports glob patterns (e.g. ``~/.nvm/versions/node/v*/bin/node``) —
    when ``*`` is present, returns the match with the highest version,
    comparing numeric components as integers.
    """
    expanded = check_path.replace("~", str(Path.home()))
    if "*" not in expanded:
        p = Path(expanded)
        return p if p.exists() else None
    parent = Path(expanded).anchor or "/"
    rel_pattern = expanded[len(parent) :]
    matches = list(Path(parent).glob(rel_pattern))
    return max(matches, key=_natural_sort_key) if matches else None


def is_language_installed(lang: Language) -> bool:
    """Return True if the language runtime is present on this machine."""
    if lang.check_path and _resolve_check_path(lang.check_path) is not None:
        return True
    return is_command_available(lang.command)


def get_language_version(lang: Language) -> str | None:
    """Return a short version string for display, or None if unavailable."""
    if not is_command_available(lang.command):
        return None
    for flag in ("version", "--version"):
        try:
            result = subprocess.run(
                [lang.command, flag],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                first_line = (result.stdout or result.stderr).splitlines()[0].strip()
                return first_line if first_line else None
        except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
            continue
    return None


def ensure_language_paths(languages: list[Language]) -> None:
    """Prepend the parent dir of each installed language's check_path to the process PATH.

    Dirs already present as an exact PATH entry are skipped.
    """
    path = os.environ.get("PATH", "")
    entries = path.split(os.pathsep) if path else []
    for lang in languages:
        if lang.check_path:
            resolved = _resolve_check_path(lang.check_path)
            if resolved is not None:
                bin_dir = str(resolved.parent)
                if bin_dir not in entries:
                    entries.insert(0, bin_dir)
    os.environ["PATH"] = os.pathsep.join(entries)


def install_language(lang: Language, dry_run: bool = False) -> tuple[bool, str]:
    """Install a language runtime. Returns (success, message)."""
    if lang.status_only:
        return True, f"{lang.name} is status-only (managed externally)"

    if is_language_installed(lang):
        return True, f"{lang.name} is already installed"

    config = resolve_platform_config(
        macos=lang.macos, linux=lang.linux, windows=lang.windows
    )
    if config:
        return run_via_config(lang.name, config, dry_run, handlers=_LANGUAGE_INSTALL)
    if lang.install_cmd:
        return run_script(
            lang.name, lang.install_cmd, dry_run, timeout=lang.install_timeout
        )
    return False, f"No install method configured for {lang.name} on this platform"
