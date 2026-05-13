"""gh CLI OAuth scope configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

from shell_configs.config import get_config_dir

_DEFAULT_SCOPES: tuple[str, ...] = ("admin:public_key", "admin:ssh_signing_key")


def load_desired_scopes(manifest_path: Path | None = None) -> list[str]:
    """Load desired gh OAuth scopes from the YAML manifest."""
    path = manifest_path or get_config_dir() / "gh_auth.yaml"
    if not path.exists():
        return list(_DEFAULT_SCOPES)
    with open(path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return list(_DEFAULT_SCOPES)
    scopes = data.get("scopes")
    if not isinstance(scopes, list):
        return list(_DEFAULT_SCOPES)
    filtered = [s for s in scopes if isinstance(s, str)]
    return filtered if filtered else list(_DEFAULT_SCOPES)


def get_current_gh_scopes() -> set[str]:
    """Parse current OAuth scopes from gh CLI auth status."""
    from shell_configs.signing import _run

    result = _run(["gh", "auth", "status"], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return set()
    output = f"{result.stdout}\n{result.stderr}"
    for line in output.splitlines():
        if "Token scopes:" in line:
            scopes_str = line.split("Token scopes:", 1)[1].strip()
            return {s.strip().strip("'\"") for s in scopes_str.split(",")}
    return set()
