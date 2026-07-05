"""Integration tests for the backup-resmed health script serial guard."""

from __future__ import annotations

import json
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
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_SCRIPT_PATH), *args],
        input=stdin,
        capture_output=True,
        text=True,
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
