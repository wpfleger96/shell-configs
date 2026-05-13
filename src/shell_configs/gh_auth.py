"""gh CLI OAuth scope configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

from shell_configs.config import get_config_dir

_DEFAULT_SCOPES: list[str] = ["admin:public_key", "admin:ssh_signing_key"]


def load_desired_scopes(manifest_path: Path | None = None) -> list[str]:
    """Load desired gh OAuth scopes from the YAML manifest."""
    path = manifest_path or get_config_dir() / "gh_auth.yaml"
    if not path.exists():
        return _DEFAULT_SCOPES
    with open(path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return _DEFAULT_SCOPES
    scopes = data.get("scopes")
    if not isinstance(scopes, list):
        return _DEFAULT_SCOPES
    return [s for s in scopes if isinstance(s, str)]
