"""Small shared file-system and text helpers.

Consolidates the atomic-write and unified-diff patterns previously
duplicated across the manager, script manager, and CLI helpers.
"""

from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import tempfile

from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str, *, preserve_stat: bool = False) -> None:
    """Write content to a file atomically via a temp file in the same directory.

    Args:
        path: Destination file path (parent directories are created).
        preserve_stat: Copy permissions/timestamps from an existing file at
            ``path`` onto the new content before replacing it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        if preserve_stat and path.exists():
            shutil.copystat(path, temp_path)
        shutil.move(temp_path, path)
    except BaseException:
        Path(temp_path).unlink(missing_ok=True)
        raise


def unified_diff_text(
    old: str | list[str],
    new: str | list[str],
    *,
    fromfile: str = "Previous",
    tofile: str = "Updated",
) -> str | None:
    """Return a unified diff between old and new, or None when empty.

    Accepts whole strings (split with keepends) or pre-built line lists.
    """
    old_lines = old.splitlines(keepends=True) if isinstance(old, str) else old
    new_lines = new.splitlines(keepends=True) if isinstance(new, str) else new
    diff = "\n".join(
        difflib.unified_diff(
            old_lines, new_lines, fromfile=fromfile, tofile=tofile, lineterm=""
        )
    )
    return diff if diff.strip() else None


def run_quiet(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """subprocess.run that converts a timeout into a returncode-1 result."""
    try:
        return subprocess.run(*args, **kwargs)  # noqa: S603
    except subprocess.TimeoutExpired:
        cmd = args[0] if args else kwargs.get("args", [])
        timeout = kwargs.get("timeout", "?")
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr=f"Command timed out after {timeout}s"
        )
