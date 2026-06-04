"""Manifest tracking which AI coding agents shell-configs has installed."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell_configs.agents import Agent

logger = logging.getLogger(__name__)


@dataclass
class AgentManifestEntry:
    command_name: str
    install_method: str
    package: str | None
    installed_at: str


class AgentManifest:
    """Tracks which AI coding agents shell-configs has installed."""

    def __init__(self, manifest_path: Path) -> None:
        self.path = manifest_path
        self._existed = manifest_path.exists()
        self.agents: dict[str, AgentManifestEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            for name, entry in data.get("agents", {}).items():
                self.agents[name] = AgentManifestEntry(
                    command_name=entry["command_name"],
                    install_method=entry["install_method"],
                    package=entry["package"],
                    installed_at=entry["installed_at"],
                )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Corrupt agent manifest at %s: %s", self.path, e)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "agents": {
                name: {
                    "command_name": entry.command_name,
                    "install_method": entry.install_method,
                    "package": entry.package,
                    "installed_at": entry.installed_at,
                }
                for name, entry in sorted(self.agents.items())
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

    def record_install(
        self,
        name: str,
        command_name: str,
        install_method: str,
        package: str | None,
    ) -> None:
        self.agents[name] = AgentManifestEntry(
            command_name=command_name,
            install_method=install_method,
            package=package,
            installed_at=datetime.now(UTC).isoformat(),
        )

    def remove(self, name: str) -> None:
        self.agents.pop(name, None)

    @property
    def is_new(self) -> bool:
        return not self._existed


def find_orphaned_agents(
    manifest: AgentManifest, current_agents: list[Agent]
) -> list[str]:
    """Return sorted list of manifest agent names not in current_agents."""
    current_names = {a.name for a in current_agents}
    return sorted(name for name in manifest.agents if name not in current_names)


def get_default_agent_manifest_path() -> Path:
    return Path.home() / ".shell-configs" / "installed_agents.json"
