"""Language runtime management (Go, Rust, Node, Ruby, Python)."""

from __future__ import annotations

import os
import shutil
import subprocess

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform


@dataclass(frozen=True)
class LanguageInstallConfig:
    method: str  # "brew" or "apt"
    package: str | None = None


@dataclass(frozen=True)
class Language:
    name: str
    command: str
    description: str
    status_only: bool = False
    # Path checked for installation (e.g. ~/.cargo/bin/rustup, ~/.nvm/nvm.sh).
    # Necessary for tools that aren't on PATH until their env is sourced.
    check_path: str | None = None
    # Cross-platform curl/script install command (used when macos/linux are absent)
    install_cmd: str | None = None
    macos: LanguageInstallConfig | None = None
    linux: LanguageInstallConfig | None = None


def load_languages(manifest_path: Path | None = None) -> list[Language]:
    """Load desired language runtimes from the YAML manifest."""
    path = manifest_path or get_config_dir() / "languages.yaml"
    if not path.exists():
        return []
    with open(path) as f:
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

        macos_cfg: LanguageInstallConfig | None = None
        linux_cfg: LanguageInstallConfig | None = None

        if isinstance(entry.get("macos"), dict):
            m: dict[str, Any] = entry["macos"]
            macos_cfg = LanguageInstallConfig(
                method=m.get("method", ""),
                package=m.get("package") or None,
            )
        if isinstance(entry.get("linux"), dict):
            li: dict[str, Any] = entry["linux"]
            linux_cfg = LanguageInstallConfig(
                method=li.get("method", ""),
                package=li.get("package") or None,
            )

        result.append(
            Language(
                name=name,
                command=command,
                description=entry.get("description", ""),
                status_only=bool(entry.get("status_only", False)),
                check_path=entry.get("check_path") or None,
                install_cmd=entry.get("install_cmd") or None,
                macos=macos_cfg,
                linux=linux_cfg,
            )
        )
    return result


def _resolve_check_path(check_path: str) -> Path | None:
    """Resolve a check_path string to an existing Path, or None.

    Supports glob patterns (e.g. ``~/.nvm/versions/node/v*/bin/node``) —
    when ``*`` is present, returns the latest (sorted) match.
    """
    expanded = check_path.replace("~", str(Path.home()))
    if "*" not in expanded:
        p = Path(expanded)
        return p if p.exists() else None
    # Glob from filesystem root — expanded is an absolute path with wildcards
    matches = sorted(Path("/").glob(expanded.lstrip("/")))
    return matches[-1] if matches else None


def is_language_installed(lang: Language) -> bool:
    """Return True if the language runtime is present on this machine."""
    if lang.check_path:
        return _resolve_check_path(lang.check_path) is not None
    return shutil.which(lang.command) is not None


def get_language_version(lang: Language) -> str | None:
    """Return a short version string for display, or None if unavailable."""
    if not shutil.which(lang.command):
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
    """Add check_path directories of installed languages to the current process PATH."""
    path = os.environ.get("PATH", "")
    for lang in languages:
        if lang.check_path:
            resolved = _resolve_check_path(lang.check_path)
            if resolved is not None:
                bin_dir = str(resolved.parent)
                if bin_dir not in path:
                    path = bin_dir + os.pathsep + path
    os.environ["PATH"] = path


def install_language(lang: Language, dry_run: bool = False) -> tuple[bool, str]:
    """Install a language runtime. Returns (success, message)."""
    if lang.status_only:
        return True, f"{lang.name} is status-only (managed externally)"

    if is_language_installed(lang):
        return True, f"{lang.name} is already installed"

    ok, msg = False, f"No install method configured for {lang.name} on this platform"

    if is_platform(Platform.MACOS) and lang.macos:
        ok, msg = _install_via_config(lang.name, lang.macos, dry_run)
    elif (is_platform(Platform.WSL) or is_platform(Platform.LINUX)) and lang.linux:
        ok, msg = _install_via_config(lang.name, lang.linux, dry_run)
    elif lang.install_cmd:
        ok, msg = _install_via_script(lang.name, lang.install_cmd, dry_run)

    return ok, msg


def _install_via_config(
    name: str, config: LanguageInstallConfig, dry_run: bool
) -> tuple[bool, str]:
    pkg = config.package or name
    if config.method == "brew":
        return _install_brew(name, pkg, dry_run)
    if config.method == "apt":
        return _install_apt(name, pkg, dry_run)
    return False, f"Unknown install method: {config.method}"


def _install_brew(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("brew"):
        return False, "brew is not available"
    if dry_run:
        return True, f"Would install {package} via brew"
    try:
        result = subprocess.run(
            ["brew", "install", package],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Installed {name} via brew"
        return False, f"Failed to install {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: brew timed out"


def _install_apt(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("apt"):
        return False, "apt is not available"
    if dry_run:
        return True, f"Would install {package} via apt"
    try:
        result = subprocess.run(
            ["sudo", "apt-get", "install", "-y", package],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Installed {name} via apt"
        return False, f"Failed to install {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: apt timed out"


def _install_via_script(name: str, install_cmd: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, f"Would install {name} via: {install_cmd}"
    try:
        result = subprocess.run(
            install_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Installed {name}"
        return False, f"Failed to install {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: install script timed out"
