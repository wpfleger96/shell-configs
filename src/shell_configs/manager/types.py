"""Shared types for the configuration manager.

The result enum, dataclasses, and the additional-files manifest. Kept
dependency-light (no subprocess / plistlib) so they can be imported without
pulling in the full manager.
"""

import json
import logging

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from shell_configs.fsio import atomic_write_text

logger = logging.getLogger(__name__)


class OperationResult(Enum):
    """Result of a configuration operation."""

    CREATED = "created"
    UPDATED = "updated"
    REMOVED = "removed"
    ALREADY_SYNCED = "already_synced"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class ManagedSection:
    """Represents a managed configuration section."""

    content: str
    start_line: int
    end_line: int


@dataclass
class AdditionalFileEntry:
    """Manifest record for a single installed additional file."""

    shell_name: str
    installed_at: str
    # False for merge-mode files (ini_merge, target_merge, xml_guiconfig_merge,
    # comment_prefix) that modify user-owned files — these can't be deleted whole.
    owned_file: bool = True


class AdditionalFileManifest:
    """Tracks which additional files shell-configs has installed.

    Stored at ~/.shell-configs/installed_additional_files.json. Keyed by
    absolute target path string. On the first run (no manifest file), orphan
    detection is skipped and the manifest is seeded with the current state.
    """

    def __init__(self, manifest_path: Path) -> None:
        self.path = manifest_path
        self.files: dict[str, AdditionalFileEntry] = {}
        self._existed = manifest_path.exists()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for target, entry in data.get("files", {}).items():
                self.files[target] = AdditionalFileEntry(
                    shell_name=entry["shell_name"],
                    installed_at=entry["installed_at"],
                    owned_file=entry.get("owned_file", True),
                )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Corrupt additional file manifest at %s: %s", self.path, e)

    def save(self) -> None:
        data = {
            "version": 1,
            "files": {
                target: {
                    "shell_name": entry.shell_name,
                    "installed_at": entry.installed_at,
                    "owned_file": entry.owned_file,
                }
                for target, entry in sorted(self.files.items())
            },
        }
        atomic_write_text(self.path, json.dumps(data, indent=2) + "\n")

    def record_install(
        self, target_path: str, shell_name: str, owned_file: bool = True
    ) -> None:
        from datetime import UTC, datetime

        self.files[target_path] = AdditionalFileEntry(
            shell_name=shell_name,
            installed_at=datetime.now(UTC).isoformat(),
            owned_file=owned_file,
        )

    def remove(self, target_path: str) -> None:
        self.files.pop(target_path, None)

    def find_orphans(self, current_targets: set[str]) -> list[str]:
        """Return manifest entries whose target is no longer in the active config."""
        return sorted(t for t in self.files if t not in current_targets)

    @property
    def is_new(self) -> bool:
        """True if the manifest file did not exist when this instance was created."""
        return not self._existed


def get_default_additional_manifest_path() -> Path:
    return Path.home() / ".shell-configs" / "installed_additional_files.json"
