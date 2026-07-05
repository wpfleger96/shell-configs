"""Integration tests for the backup-resmed health script serial guard."""

from __future__ import annotations

import json
import os
import subprocess

from pathlib import Path

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "shell_configs"
    / "scripts"
    / "health"
    / "backup-resmed"
)

_SERIAL_A = "11111111111"
_SERIAL_B = "22222222222"


def _id_json(serial: str) -> str:
    return json.dumps(
        {
            "FlowGenerator": {
                "IdentificationProfiles": {
                    "Product": {
                        "SerialNumber": serial,
                        "ProductName": "AirSense11AutoSet",
                    }
                }
            }
        }
    )


def _make_source(path: Path, serial: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "STR.edf").write_text("fake")
    (path / "Identification.json").write_text(_id_json(serial))


def _make_dest(path: Path, serial: str | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if serial is not None:
        (path / "Identification.json").write_text(_id_json(serial))


def _run(
    *args: str,
    stdin: str = "",
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", str(_SCRIPT_PATH), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=merged_env,
    )


@pytest.mark.integration
class TestSerialGuard:
    def test_serial_match_proceeds(self, tmp_path: Path) -> None:
        src = tmp_path / "source"
        dest = tmp_path / "dest"
        _make_source(src, _SERIAL_A)
        _make_dest(dest, _SERIAL_A)

        result = _run("--dry-run", "--source", str(src), "--dest", str(dest))

        assert result.returncode == 0
        assert "mismatch" not in result.stdout.lower()
        assert "mismatch" not in result.stderr.lower()

    def test_serial_mismatch_refused_aborts_nonzero(self, tmp_path: Path) -> None:
        src = tmp_path / "source"
        dest = tmp_path / "dest"
        _make_source(src, _SERIAL_A)
        _make_dest(dest, _SERIAL_B)

        result = _run("--source", str(src), "--dest", str(dest), stdin="no\n")

        assert result.returncode != 0
        assert "mismatch" in result.stdout.lower()
        assert "aborted" in (result.stdout + result.stderr).lower()

    def test_serial_mismatch_dry_run_exits_zero(self, tmp_path: Path) -> None:
        src = tmp_path / "source"
        dest = tmp_path / "dest"
        _make_source(src, _SERIAL_A)
        _make_dest(dest, _SERIAL_B)

        result = _run("--dry-run", "--source", str(src), "--dest", str(dest))

        assert result.returncode == 0
        assert "mismatch" in result.stdout.lower()
        assert "dry run" in result.stdout.lower()

    def test_missing_dest_identification_json_proceeds(self, tmp_path: Path) -> None:
        src = tmp_path / "source"
        dest = tmp_path / "dest"
        _make_source(src, _SERIAL_A)
        _make_dest(dest, serial=None)

        result = _run("--dry-run", "--source", str(src), "--dest", str(dest))

        assert result.returncode == 0
        assert "first backup" in result.stdout.lower()


@pytest.mark.integration
class TestAutodetectAndArchiving:
    def test_autodetect_single_card_used_noninteractively(self, tmp_path: Path) -> None:
        base = tmp_path / "media"
        card = base / "RESMED-CARD"
        _make_source(card, _SERIAL_A)
        dest = tmp_path / "dest"
        _make_dest(dest, serial=None)

        result = _run(
            "--dry-run",
            "--dest",
            str(dest),
            env={"BACKUP_RESMED_SCAN_DIRS": str(base)},
        )

        assert result.returncode == 0
        assert str(card) in result.stdout

    def test_autodetect_multiple_cards_prompts_selection(self, tmp_path: Path) -> None:
        base = tmp_path / "media"
        card1 = base / "CARD-1"
        card2 = base / "CARD-2"
        _make_source(card1, _SERIAL_A)
        _make_source(card2, _SERIAL_B)
        dest = tmp_path / "dest"
        _make_dest(dest, serial=None)

        result = _run(
            "--dry-run",
            "--dest",
            str(dest),
            stdin="1\n",
            env={"BACKUP_RESMED_SCAN_DIRS": str(base)},
        )

        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "multiple resmed sd cards" in combined.lower()

    def test_autodetect_no_card_falls_back_to_manual_prompt(
        self, tmp_path: Path
    ) -> None:
        base = tmp_path / "media"
        base.mkdir(parents=True)

        result = _run(
            "--dest",
            str(tmp_path / "dest"),
            stdin="",
            env={"BACKUP_RESMED_SCAN_DIRS": str(base)},
        )

        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "no" in combined.lower() and "sd card" in combined.lower()

    def test_existing_dest_str_archived_with_mtime_date(self, tmp_path: Path) -> None:
        import datetime

        src = tmp_path / "source"
        dest = tmp_path / "dest"
        _make_source(src, _SERIAL_A)
        _make_dest(dest, serial=_SERIAL_A)

        # Pin STR.edf mtime to 2026-01-15 12:00 local time
        str_edf = dest / "STR.edf"
        str_edf.write_text("old data")
        known_ts = datetime.datetime(2026, 1, 15, 12, 0, 0).timestamp()
        os.utime(str(str_edf), (known_ts, known_ts))

        result = _run("--source", str(src), "--dest", str(dest))

        assert result.returncode == 0
        assert (dest / "STR_Backup" / "STR-2026-01-15.edf").exists()
