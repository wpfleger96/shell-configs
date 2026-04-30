"""Unit tests for SSH agent and signing utilities."""

from __future__ import annotations

import subprocess

from pathlib import Path
from unittest.mock import patch

import pytest

from shell_configs.signing import ensure_ssh_agent


def _make_result(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


PUB_KEY_CONTENT = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAATESTKEYDATAXXXX user@host\n"
KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAATESTKEYDATAXXXX"


@pytest.mark.unit
class TestEnsureSshAgent:
    """Tests for ensure_ssh_agent()."""

    @pytest.fixture
    def key_files(self, tmp_path: Path) -> Path:
        key_path = tmp_path / "id_ed25519"
        key_path.with_suffix(".pub").write_text(PUB_KEY_CONTENT)
        return key_path

    def test_returns_failure_when_pub_key_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def mock_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(list(cmd))
            return _make_result(0)

        monkeypatch.setattr("shell_configs.signing._run", mock_run)

        key_path = tmp_path / "id_ed25519"
        success, message, pub_key = ensure_ssh_agent(key_path)

        assert success is False
        assert "Public key not found" in message
        assert pub_key is None
        assert calls == []

    def test_returns_failure_when_agent_not_running(
        self, key_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.signing._run",
            lambda *a, **kw: _make_result(2),
        )
        success, message, pub_key = ensure_ssh_agent(key_files)

        assert success is False
        assert "ssh-agent is not running" in message
        assert pub_key is None

    def test_returns_success_when_key_already_loaded(
        self, key_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def mock_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(list(cmd))
            if cmd[:2] == ["ssh-add", "-L"]:
                return _make_result(0, stdout=f"ssh-ed25519 {KEY_DATA} user@host\n")
            return _make_result(0)

        monkeypatch.setattr("shell_configs.signing._run", mock_run)
        success, message, pub_key = ensure_ssh_agent(key_files)

        assert success is True
        assert "loaded" in message
        assert pub_key is not None
        assert not any(c[0] == "ssh-add" and len(c) > 2 for c in calls)

    def test_loads_key_when_missing_and_auto_fix_true(
        self, key_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def mock_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(list(cmd))
            if cmd[:2] == ["ssh-add", "-L"]:
                return _make_result(0, stdout="")
            return _make_result(0)

        monkeypatch.setattr("shell_configs.signing._run", mock_run)
        success, message, pub_key = ensure_ssh_agent(key_files, auto_fix=True)

        assert success is True
        assert "Added" in message
        assert pub_key is not None
        assert any(c[0] == "ssh-add" and str(key_files) in c for c in calls)

    def test_does_not_load_key_when_auto_fix_false(
        self, key_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def mock_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(list(cmd))
            if cmd[:2] == ["ssh-add", "-L"]:
                return _make_result(0, stdout="")
            return _make_result(0)

        monkeypatch.setattr("shell_configs.signing._run", mock_run)
        success, message, pub_key = ensure_ssh_agent(key_files, auto_fix=False)

        assert success is False
        assert "not in ssh-agent" in message
        assert "--fix" in message
        assert pub_key is None
        ssh_add_load_calls = [
            c for c in calls if c[0] == "ssh-add" and len(c) > 1 and c[1] != "-L"
        ]
        assert ssh_add_load_calls == []

    def test_agent_not_running_takes_precedence_over_auto_fix(
        self, key_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.signing._run",
            lambda *a, **kw: _make_result(2),
        )
        success, message, pub_key = ensure_ssh_agent(key_files, auto_fix=False)

        assert success is False
        assert "ssh-agent is not running" in message
        assert pub_key is None

    def test_returns_failure_when_ssh_add_fails(
        self, key_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def mock_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if cmd[:2] == ["ssh-add", "-L"]:
                return _make_result(0, stdout="")
            return _make_result(1)

        monkeypatch.setattr("shell_configs.signing._run", mock_run)
        success, message, pub_key = ensure_ssh_agent(key_files, auto_fix=True)

        assert success is False
        assert "Failed to add key" in message
        assert pub_key is None


@pytest.mark.unit
class TestValidateAllStepsNoMutation:
    """Regression test: _validate_all_steps must not trigger ssh-add <key_path>."""

    def test_validate_does_not_load_ssh_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        key_path = tmp_path / "id_ed25519"
        key_path.touch()
        key_path.with_suffix(".pub").write_text(PUB_KEY_CONTENT)

        ssh_add_load_calls: list[list[str]] = []

        def mock_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if cmd[0] == "ssh-add" and len(cmd) > 1 and cmd[1] != "-L":
                ssh_add_load_calls.append(list(cmd))
            if cmd[:2] == ["ssh-add", "-L"]:
                return _make_result(0, stdout="")
            if cmd[:2] == ["gh", "auth"]:
                return _make_result(0)
            if cmd[:2] == ["gh", "ssh-key"]:
                return _make_result(0, stdout="")
            return _make_result(0)

        monkeypatch.setattr("shell_configs.signing._run", mock_run)

        from shell_configs.signing import _validate_all_steps

        with (
            patch("shell_configs.signing.find_local_ssh_keys", return_value=[key_path]),
            patch(
                "shell_configs.signing.get_github_key_fingerprints", return_value=set()
            ),
            patch(
                "shell_configs.signing.get_key_fingerprint_from_pub",
                return_value="SHA256:test",
            ),
        ):
            _validate_all_steps(key_path)

        assert ssh_add_load_calls == [], (
            f"_validate_all_steps must not call ssh-add to load keys, "
            f"but called: {ssh_add_load_calls}"
        )
