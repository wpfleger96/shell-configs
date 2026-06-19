"""gh CLI extension management."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile

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
    build_path: str | None = None


def load_extensions(manifest_path: Path | None = None) -> list[GhExtension]:
    """Load desired gh extensions from the YAML manifest."""
    path = manifest_path or get_config_dir() / "gh_extensions.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
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
                build_path = ext.get("build_path") or None
                result.append(
                    GhExtension(
                        repo=repo,
                        pin=pin if isinstance(pin, str) else None,
                        build_path=build_path if isinstance(build_path, str) else None,
                    )
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
                if repo:
                    installed[repo] = version or None
                elif parts[0].startswith("gh "):
                    # Local extensions (symlinks/source-built) have empty
                    # repo and version columns — key by command name instead.
                    cmd_name = parts[0][3:].strip()
                    if cmd_name:
                        installed[cmd_name] = None
        return installed
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}


def command_name(repo: str) -> str:
    """Derive the gh extension command name from an owner/repo slug.

    e.g. "wpfleger96/gh-infra" → "infra"
    """
    project = repo.split("/")[-1]
    return project.removeprefix("gh-")


def _remove_extension(cmd_name: str) -> bool:
    """Remove an installed gh extension by command name."""
    try:
        result = subprocess.run(
            ["gh", "extension", "remove", cmd_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_extensions_dir() -> Path:
    """Return the gh CLI extensions directory."""
    try:
        result = subprocess.run(
            ["gh", "config", "get", "extensions_dir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return Path.home() / ".local" / "share" / "gh" / "extensions"


_BUILD_PATH_RE = re.compile(r"^\.(/[a-zA-Z0-9_.-]+)+/?$")


def install_from_source(
    name: str, build_path: str, pin: str | None = None, dry_run: bool = False
) -> tuple[bool, str]:
    """Build and install a gh CLI extension from source using Go."""
    if not _BUILD_PATH_RE.match(build_path):
        return False, f"Rejected invalid build_path: {build_path!r}"

    ext_name = name.split("/")[-1]
    ext_dir = _get_extensions_dir() / ext_name
    binary_dest = ext_dir / ext_name

    if dry_run:
        return True, f"Would build {name} from source and install to {binary_dest}"

    if not shutil.which("go"):
        return False, f"Failed to install {name}: go not found in PATH"

    clone_dir = tempfile.mkdtemp(prefix="gh-ext-build-")
    try:
        clone_cmd = ["git", "clone", "--depth", "1"]
        if pin:
            clone_cmd += ["-b", pin]
        clone_cmd += [f"https://github.com/{name}.git", clone_dir]
        clone_result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if clone_result.returncode != 0:
            return False, f"Failed to clone {name}: {clone_result.stderr.strip()}"

        build_dir = tempfile.mkdtemp(prefix="gh-ext-out-")
        staged_binary = Path(build_dir) / ext_name

        build_result = subprocess.run(
            ["go", "build", "-trimpath", "-o", str(staged_binary), build_path],
            capture_output=True,
            text=True,
            cwd=clone_dir,
            timeout=300,
        )
        if build_result.returncode != 0:
            shutil.rmtree(build_dir, ignore_errors=True)
            return False, f"Failed to build {name}: {build_result.stderr.strip()}"

        # Build succeeded — now remove existing extension and move binary into place.
        _remove_extension(command_name(name))
        ext_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_binary), str(binary_dest))
        binary_dest.chmod(0o755)
        shutil.rmtree(build_dir, ignore_errors=True)
        return True, f"Built and installed {name} from source"
    except FileNotFoundError as e:
        return False, f"Failed to install {name}: {e}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: build timed out"
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)


def install_extension(
    name: str,
    pin: str | None = None,
    dry_run: bool = False,
    build_path: str | None = None,
) -> tuple[bool, str]:
    """Install a gh CLI extension by owner/name."""
    if not _EXTENSION_RE.match(name):
        return False, f"Rejected invalid extension name: {name!r}"

    cmd_name = command_name(name)

    if build_path is not None:
        return install_from_source(name, build_path, pin=pin, dry_run=dry_run)

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

    # Handle conflict: another extension already provides this command.
    if "already" in result.stderr and "provides" in result.stderr:
        _remove_extension(cmd_name)
        try:
            retry = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return (
                False,
                f"Failed to install {name}: retry failed after removing conflict",
            )
        if retry.returncode == 0:
            return True, f"Installed {name}"
        return False, f"Failed to install {name}: {retry.stderr.strip()}"

    return False, f"Failed to install {name}: {result.stderr.strip()}"
