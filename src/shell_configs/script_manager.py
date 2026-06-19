"""Script discovery, installation, and management."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from importlib.resources import files
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from shell_configs.fsio import atomic_write_text
from shell_configs.platform import Platform, detect_platform

logger = logging.getLogger(__name__)

_ALL_PLATFORMS = frozenset({Platform.MACOS, Platform.LINUX, Platform.WSL})

_SKIP_NAMES = frozenset({"__init__.py", "__pycache__", "scripts.toml"})

_PLATFORM_NAMES: dict[str, Platform] = {
    "macos": Platform.MACOS,
    "linux": Platform.LINUX,
    "wsl": Platform.WSL,
}


@dataclass(frozen=True)
class DiscoveredScript:
    """A script discovered from the scripts directory."""

    name: str
    rel_path: str
    platforms: frozenset[Platform]


class InstallResult(Enum):
    INSTALLED = "installed"
    UPDATED = "updated"
    ALREADY_SYNCED = "already_synced"
    COLLISION = "collision"
    WOULD_INSTALL = "would_install"
    WOULD_UPDATE = "would_update"
    SKIPPED_PLATFORM = "skipped_platform"
    ERROR = "error"


class UninstallResult(Enum):
    REMOVED = "removed"
    NOT_FOUND = "not_found"
    NOT_OURS = "not_ours"
    MODIFIED = "modified"
    WOULD_REMOVE = "would_remove"
    ERROR = "error"


class ScriptStatus(Enum):
    INSTALLED = "installed"
    OUTDATED = "outdated"
    MODIFIED = "modified"
    MISSING = "missing"
    COLLISION = "collision"
    SKIPPED_PLATFORM = "skipped_platform"


@dataclass
class ManifestEntry:
    source_hash: str
    source_path: str
    installed_at: str


class ScriptManifest:
    """Tracks which scripts shell-configs has installed."""

    def __init__(self, manifest_path: Path) -> None:
        self.path = manifest_path
        self.scripts: dict[str, ManifestEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for name, entry in data.get("scripts", {}).items():
                self.scripts[name] = ManifestEntry(
                    source_hash=entry["source_hash"],
                    source_path=entry["source_path"],
                    installed_at=entry["installed_at"],
                )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Corrupt script manifest at %s: %s", self.path, e)

    def save(self) -> None:
        data = {
            "version": 1,
            "scripts": {
                name: {
                    "source_hash": entry.source_hash,
                    "source_path": entry.source_path,
                    "installed_at": entry.installed_at,
                }
                for name, entry in sorted(self.scripts.items())
            },
        }
        atomic_write_text(self.path, json.dumps(data, indent=2) + "\n")

    def record_install(self, name: str, source_hash: str, source_path: str) -> None:
        self.scripts[name] = ManifestEntry(
            source_hash=source_hash,
            source_path=source_path,
            installed_at=datetime.now(UTC).isoformat(),
        )

    def remove(self, name: str) -> None:
        self.scripts.pop(name, None)


def get_default_manifest_path() -> Path:
    return Path.home() / ".shell-configs" / "installed_scripts.json"


def get_default_target_dir() -> Path:
    return Path.home() / ".local" / "bin"


def _load_platform_exceptions(
    source_dir: Path | None = None,
) -> dict[str, frozenset[Platform]]:
    try:
        if source_dir is not None:
            raw = (source_dir / "scripts.toml").read_bytes()
        else:
            raw = files("shell_configs.scripts").joinpath("scripts.toml").read_bytes()
    except FileNotFoundError:
        return {}

    data = tomllib.loads(raw.decode())
    result: dict[str, frozenset[Platform]] = {}
    for script_name, table in data.items():
        if not isinstance(table, dict):
            continue
        raw_platforms = table.get("platforms", [])
        platforms = frozenset(
            _PLATFORM_NAMES[p] for p in raw_platforms if p in _PLATFORM_NAMES
        )
        if raw_platforms and not platforms:
            logger.warning("Unknown platforms for %s: %s", script_name, raw_platforms)
        result[script_name] = platforms
    return result


def _walk_tree(root: object, rel_parts: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for item in sorted(root.iterdir(), key=lambda x: x.name):  # type: ignore[attr-defined]
        if item.name in _SKIP_NAMES or item.name.endswith(".pyc"):
            continue
        if item.is_dir():
            found.extend(_walk_tree(item, rel_parts + (item.name,)))
        elif item.is_file():
            found.append((item.name, "/".join(rel_parts + (item.name,))))
    return found


def discover_scripts(
    current_platform: Platform | None = None,
    source_dir: Path | None = None,
    include_all: bool = False,
) -> list[DiscoveredScript]:
    if current_platform is None and not include_all:
        current_platform = detect_platform()

    exceptions = _load_platform_exceptions(source_dir)

    root = source_dir if source_dir is not None else files("shell_configs.scripts")
    entries = _walk_tree(root)

    seen: dict[str, str] = {}
    scripts: list[DiscoveredScript] = []
    for name, rel_path in entries:
        if name in seen:
            logger.warning(
                "Script name collision: %s and %s both resolve to '%s'",
                seen[name],
                rel_path,
                name,
            )
            continue
        seen[name] = rel_path
        platforms = exceptions.get(name, _ALL_PLATFORMS)
        if not include_all and current_platform not in platforms:
            continue
        scripts.append(
            DiscoveredScript(name=name, rel_path=rel_path, platforms=platforms)
        )

    return scripts


def _read_script_bytes(rel_path: str, source_dir: Path | None = None) -> bytes:
    if source_dir is not None:
        return (source_dir / rel_path).read_bytes()
    resource = files("shell_configs.scripts").joinpath(rel_path)
    return resource.read_bytes()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_script_status(
    script: DiscoveredScript,
    target_dir: Path,
    manifest: ScriptManifest,
    source_dir: Path | None = None,
) -> ScriptStatus:
    current_platform = detect_platform()
    if current_platform not in script.platforms:
        return ScriptStatus.SKIPPED_PLATFORM

    target = target_dir / script.name

    if not target.exists() and not target.is_symlink():
        if script.name in manifest.scripts:
            manifest.remove(script.name)
        return ScriptStatus.MISSING

    if script.name not in manifest.scripts:
        return ScriptStatus.COLLISION

    if not target.is_file():
        return ScriptStatus.COLLISION

    try:
        source_bytes = _read_script_bytes(script.rel_path, source_dir)
    except (FileNotFoundError, TypeError):
        return ScriptStatus.MISSING

    source_hash = _hash_bytes(source_bytes)
    installed_hash = _hash_bytes(target.read_bytes())
    recorded_hash = manifest.scripts[script.name].source_hash

    if installed_hash == source_hash:
        return ScriptStatus.INSTALLED

    if installed_hash != recorded_hash:
        return ScriptStatus.MODIFIED

    return ScriptStatus.OUTDATED


def install_script(
    script: DiscoveredScript,
    target_dir: Path,
    manifest: ScriptManifest,
    dry_run: bool = False,
    source_dir: Path | None = None,
) -> tuple[InstallResult, str]:
    current_platform = detect_platform()
    if current_platform not in script.platforms:
        return (
            InstallResult.SKIPPED_PLATFORM,
            f"{script.name}: not supported on {current_platform.display_name}",
        )

    try:
        source_bytes = _read_script_bytes(script.rel_path, source_dir)
    except FileNotFoundError:
        return (
            InstallResult.ERROR,
            f"{script.name}: source not found: {script.rel_path}",
        )

    source_hash = _hash_bytes(source_bytes)
    target = target_dir / script.name

    target_present = target.exists() or target.is_symlink()

    if target_present and script.name not in manifest.scripts:
        return (
            InstallResult.COLLISION,
            f"{script.name}: already exists in {target_dir} and wasn't installed by shell-configs",
        )

    if target_present and script.name in manifest.scripts:
        installed_hash = _hash_bytes(target.read_bytes())
        if installed_hash == source_hash:
            return InstallResult.ALREADY_SYNCED, f"{script.name}: already up to date"
        if dry_run:
            return InstallResult.WOULD_UPDATE, f"{script.name}: would update"

    elif dry_run:
        return InstallResult.WOULD_INSTALL, f"{script.name}: would install to {target}"

    target_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix=f".{script.name}.")
    try:
        os.write(fd, source_bytes)
        os.close(fd)
        os.chmod(temp_path, 0o755)
        shutil.move(temp_path, target)
    except Exception as e:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        return InstallResult.ERROR, f"{script.name}: {e}"

    is_update = script.name in manifest.scripts
    manifest.record_install(script.name, source_hash, script.rel_path)
    manifest.save()

    if is_update:
        return InstallResult.UPDATED, f"{script.name}: updated"
    return InstallResult.INSTALLED, f"{script.name}: installed to {target}"


def uninstall_script(
    name: str,
    target_dir: Path,
    manifest: ScriptManifest,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[UninstallResult, str]:
    target = target_dir / name

    if not target.exists() and not target.is_symlink():
        manifest.remove(name)
        manifest.save()
        return UninstallResult.NOT_FOUND, f"{name}: not found in {target_dir}"

    if name not in manifest.scripts:
        return UninstallResult.NOT_OURS, f"{name}: not installed by shell-configs"

    current_hash = _hash_bytes(target.read_bytes()) if target.is_file() else ""
    recorded_hash = manifest.scripts[name].source_hash
    if current_hash != recorded_hash and not force:
        return (
            UninstallResult.MODIFIED,
            f"{name}: modified since install (use --force to remove)",
        )

    if dry_run:
        return UninstallResult.WOULD_REMOVE, f"{name}: would remove from {target_dir}"

    try:
        target.unlink()
    except OSError as e:
        return UninstallResult.ERROR, f"{name}: {e}"

    manifest.remove(name)
    manifest.save()
    return UninstallResult.REMOVED, f"{name}: removed"


def find_orphaned_scripts(
    manifest: ScriptManifest,
    current_scripts: list[DiscoveredScript],
) -> list[str]:
    """Return manifest entries that no longer correspond to any discovered script.

    Uses include_all=True semantics — callers should pass all scripts regardless
    of platform so that platform-filtered scripts (e.g. macOS-only on WSL) are
    not incorrectly flagged as orphans.
    """
    current_names = {s.name for s in current_scripts}
    return sorted(name for name in manifest.scripts if name not in current_names)
