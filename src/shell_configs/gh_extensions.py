"""gh CLI extension management."""

from __future__ import annotations

import re
import subprocess

from dataclasses import dataclass
from pathlib import Path

import yaml

from shell_configs.config import get_config_dir

# Validates owner/repo format — rejects URLs, bare names, and paths.
_EXTENSION_RE = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")


@dataclass(frozen=True)
class GhExtension:
    repo: str
    pin: str | None = None


def load_extensions(manifest_path: Path | None = None) -> list[GhExtension]:
    """Load desired gh extensions from the YAML manifest."""
    path = manifest_path or get_config_dir() / "gh_extensions.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    extensions = data.get("extensions") or []
    if not isinstance(extensions, list):
        return []

    result: list[GhExtension] = []
    for ext in extensions:
        if isinstance(ext, str):
            if _EXTENSION_RE.match(ext):
                result.append(GhExtension(repo=ext))
        elif isinstance(ext, dict):
            repo = ext.get("repo", "")
            if isinstance(repo, str) and _EXTENSION_RE.match(repo):
                pin = ext.get("pin") or None
                result.append(
                    GhExtension(repo=repo, pin=pin if isinstance(pin, str) else None)
                )
    return result


def list_installed() -> dict[str, str | None]:
    """Return installed gh extensions as a mapping of owner/repo → version."""
    try:
        result = subprocess.run(
            ["gh", "extension", "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {}
        installed: dict[str, str | None] = {}
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                repo = parts[1].strip()
                version = parts[2].strip() if len(parts) >= 3 else None
                installed[repo] = version or None
        return installed
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}


def install_extension(
    name: str, pin: str | None = None, dry_run: bool = False
) -> tuple[bool, str]:
    """Install a gh CLI extension by owner/name."""
    if not _EXTENSION_RE.match(name):
        return False, f"Rejected invalid extension name: {name!r}"
    if dry_run:
        return True, f"Would install {name}"
    cmd = ["gh", "extension", "install", name]
    if pin:
        cmd += ["--pin", pin]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return False, f"Failed to install {name}: gh CLI not found"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: timed out"
    if result.returncode == 0:
        return True, f"Installed {name}"
    return False, f"Failed to install {name}: {result.stderr.strip()}"
