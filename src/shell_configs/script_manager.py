"""Script discovery, installation, and management."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from importlib.resources import files
from pathlib import Path

from shell_configs.platform import Platform, detect_platform

logger = logging.getLogger(__name__)

ALL_PLATFORMS = frozenset({Platform.MACOS, Platform.LINUX, Platform.WSL})


@dataclass(frozen=True)
class ScriptEntry:
    """Declarative metadata for a distributable script."""

    source: str
    name: str
    description: str
    platforms: frozenset[Platform]
    mode: int = 0o755


SCRIPT_REGISTRY: list[ScriptEntry] = [
    ScriptEntry(
        source="git/check_pr_release_status.py",
        name="check-pr-release-status",
        description="Check if a merged PR's commit is included in any published release",
        platforms=ALL_PLATFORMS,
    ),
    ScriptEntry(
        source="git/fix-git-case-conflicts.sh",
        name="fix-git-case-conflicts",
        description="Fix macOS case-sensitivity git ref conflicts",
        platforms=frozenset({Platform.MACOS}),
    ),
    ScriptEntry(
        source="goose/db-helper.sh",
        name="db-helper",
        description="Manage Goose AI assistant's SQLite session database",
        platforms=ALL_PLATFORMS,
    ),
    ScriptEntry(
        source="transcription/transcribe.py",
        name="transcribe",
        description="Transcribe audio files using faster-whisper",
        platforms=frozenset({Platform.MACOS, Platform.LINUX}),
    ),
    ScriptEntry(
        source="windows/fix-date-formatting.ps1",
        name="fix-date-formatting",
        description="Rename files from MM-DD-YY to YYYY-MM-DD date format",
        platforms=frozenset({Platform.WSL}),
    ),
    ScriptEntry(
        source="work_laptop/backup-repos",
        name="backup-repos",
        description="Back up all local git repo remote URLs",
        platforms=ALL_PLATFORMS,
    ),
    ScriptEntry(
        source="work_laptop/clone-repos",
        name="clone-repos",
        description="Clone repos from backup file",
        platforms=ALL_PLATFORMS,
    ),
    ScriptEntry(
        source="work_laptop/disk-cleanup",
        name="disk-cleanup",
        description="Clean up disk space (caches, build artifacts)",
        platforms=frozenset({Platform.MACOS}),
    ),
    ScriptEntry(
        source="work_laptop/laptop-upgrade",
        name="laptop-upgrade",
        description="Update brew, gcloud, and system packages",
        platforms=frozenset({Platform.MACOS}),
    ),
    ScriptEntry(
        source="work_laptop/new-laptop-setup",
        name="new-laptop-setup",
        description="Bootstrap a new Mac for development",
        platforms=frozenset({Platform.MACOS}),
    ),
]


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
            data = json.loads(self.path.read_text())
            for name, entry in data.get("scripts", {}).items():
                self.scripts[name] = ManifestEntry(
                    source_hash=entry["source_hash"],
                    source_path=entry["source_path"],
                    installed_at=entry["installed_at"],
                )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Corrupt script manifest at %s: %s", self.path, e)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
        content = json.dumps(data, indent=2) + "\n"
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent, prefix=".manifest.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            shutil.move(temp_path, self.path)
        except BaseException:
            Path(temp_path).unlink(missing_ok=True)
            raise

    def record_install(self, name: str, source_hash: str, source_path: str) -> None:
        self.scripts[name] = ManifestEntry(
            source_hash=source_hash,
            source_path=source_path,
            installed_at=datetime.now(timezone.utc).isoformat(),
        )

    def remove(self, name: str) -> None:
        self.scripts.pop(name, None)


def get_default_manifest_path() -> Path:
    return Path.home() / ".shell-configs" / "installed_scripts.json"


def get_default_target_dir() -> Path:
    return Path.home() / ".local" / "bin"


def _read_script_bytes(source: str, source_dir: Path | None = None) -> bytes:
    if source_dir is not None:
        return (source_dir / source).read_bytes()
    resource = files("shell_configs.scripts").joinpath(source)
    return resource.read_bytes()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_available_scripts(
    current_platform: Platform | None = None,
) -> list[ScriptEntry]:
    if current_platform is None:
        current_platform = detect_platform()

    return [entry for entry in SCRIPT_REGISTRY if current_platform in entry.platforms]


def get_script_status(
    entry: ScriptEntry,
    target_dir: Path,
    manifest: ScriptManifest,
    source_dir: Path | None = None,
) -> ScriptStatus:
    current_platform = detect_platform()
    if current_platform not in entry.platforms:
        return ScriptStatus.SKIPPED_PLATFORM

    target = target_dir / entry.name

    if not target.exists():
        if entry.name in manifest.scripts:
            manifest.remove(entry.name)
        return ScriptStatus.MISSING

    if entry.name not in manifest.scripts:
        return ScriptStatus.COLLISION

    try:
        source_bytes = _read_script_bytes(entry.source, source_dir)
    except (FileNotFoundError, TypeError):
        return ScriptStatus.MISSING

    source_hash = _hash_bytes(source_bytes)
    installed_hash = _hash_bytes(target.read_bytes())
    recorded_hash = manifest.scripts[entry.name].source_hash

    if installed_hash == source_hash:
        return ScriptStatus.INSTALLED

    if installed_hash != recorded_hash:
        return ScriptStatus.MODIFIED

    return ScriptStatus.OUTDATED


def install_script(
    entry: ScriptEntry,
    target_dir: Path,
    manifest: ScriptManifest,
    dry_run: bool = False,
    source_dir: Path | None = None,
) -> tuple[InstallResult, str]:
    current_platform = detect_platform()
    if current_platform not in entry.platforms:
        return (
            InstallResult.SKIPPED_PLATFORM,
            f"{entry.name}: not supported on {current_platform.display_name}",
        )

    try:
        source_bytes = _read_script_bytes(entry.source, source_dir)
    except FileNotFoundError:
        return InstallResult.ERROR, f"{entry.name}: source not found: {entry.source}"

    source_hash = _hash_bytes(source_bytes)
    target = target_dir / entry.name

    if target.exists() and entry.name not in manifest.scripts:
        return (
            InstallResult.COLLISION,
            f"{entry.name}: already exists in {target_dir} and wasn't installed by shell-configs",
        )

    if target.exists() and entry.name in manifest.scripts:
        installed_hash = _hash_bytes(target.read_bytes())
        if installed_hash == source_hash:
            return InstallResult.ALREADY_SYNCED, f"{entry.name}: already up to date"
        if dry_run:
            return InstallResult.WOULD_UPDATE, f"{entry.name}: would update"

    elif dry_run:
        return InstallResult.WOULD_INSTALL, f"{entry.name}: would install to {target}"

    target_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix=f".{entry.name}.")
    try:
        os.write(fd, source_bytes)
        os.close(fd)
        os.chmod(temp_path, entry.mode)
        shutil.move(temp_path, target)
    except Exception as e:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        return InstallResult.ERROR, f"{entry.name}: {e}"

    is_update = entry.name in manifest.scripts
    manifest.record_install(entry.name, source_hash, entry.source)
    manifest.save()

    if is_update:
        return InstallResult.UPDATED, f"{entry.name}: updated"
    return InstallResult.INSTALLED, f"{entry.name}: installed to {target}"


def uninstall_script(
    name: str,
    target_dir: Path,
    manifest: ScriptManifest,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[UninstallResult, str]:
    target = target_dir / name

    if not target.exists():
        manifest.remove(name)
        manifest.save()
        return UninstallResult.NOT_FOUND, f"{name}: not found in {target_dir}"

    if name not in manifest.scripts:
        return UninstallResult.NOT_OURS, f"{name}: not installed by shell-configs"

    current_hash = _hash_bytes(target.read_bytes())
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
