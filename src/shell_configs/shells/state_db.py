"""SQLite state database helpers for managing application internal state."""

from __future__ import annotations

import json
import sqlite3

from pathlib import Path

from shell_configs.manager import OperationResult


def _ensure_state_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path), timeout=2) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ItemTable "
            "(key TEXT UNIQUE ON CONFLICT REPLACE, value TEXT)"
        )


def values_match(current: str, desired: str) -> bool:
    """Check if current DB value satisfies the desired value.

    For JSON arrays, uses containment: if desired is a list whose every
    element already exists in the current list, treat as synced (avoids
    overwriting user-added entries alongside the wildcard).
    """
    try:
        current_parsed = json.loads(current)
        desired_parsed = json.loads(desired)
    except (json.JSONDecodeError, TypeError):
        return current == desired

    if isinstance(desired_parsed, list) and isinstance(current_parsed, list):
        return all(item in current_parsed for item in desired_parsed)
    return bool(current_parsed == desired_parsed)


def read_state_db_value(db_path: Path, key: str) -> str | None:
    if not db_path.exists():
        return None
    try:
        with sqlite3.connect(str(db_path), timeout=2) as conn:
            row = conn.execute(
                "SELECT value FROM ItemTable WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None
    except (sqlite3.OperationalError):
        return None


def write_state_db_value(
    db_path: Path, key: str, value: str
) -> tuple[OperationResult, str]:
    try:
        _ensure_state_db(db_path)

        with sqlite3.connect(str(db_path), timeout=2) as conn:
            row = conn.execute(
                "SELECT value FROM ItemTable WHERE key = ?", (key,)
            ).fetchone()

            if row is not None:
                if values_match(row[0], value):
                    return (
                        OperationResult.ALREADY_SYNCED,
                        f"Already synced: {db_path.name}: {key}",
                    )

                conn.execute(
                    "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                    (key, value),
                )
                return (OperationResult.UPDATED, f"Updated: {db_path.name}: {key}")

            conn.execute(
                "INSERT INTO ItemTable (key, value) VALUES (?, ?)", (key, value)
            )
            return (OperationResult.CREATED, f"Created: {db_path.name}: {key}")

    except (sqlite3.OperationalError):
        return (
            OperationResult.ERROR,
            f"Database locked (editor may be open): {db_path}",
        )
    except Exception as e:
        return (OperationResult.ERROR, f"Failed to write {db_path.name}: {key}: {e}")
