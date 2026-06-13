"""Unit tests for SSH agent and signing utilities."""

from __future__ import annotations

import subprocess

from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from shell_configs.signing import ensure_gh_scopes, ensure_ssh_agent, upload_auth_key


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
                "shell_configs.signing.get_key_fingerprint",
                return_value="SHA256:test",
            ),
        ):
            _validate_all_steps(key_path)

        assert ssh_add_load_calls == [], (
            f"_validate_all_steps must not call ssh-add to load keys, "
            f"but called: {ssh_add_load_calls}"
        )


@pytest.mark.unit
class TestEnsureGhScopes:
    def test_returns_true_when_all_scopes_present(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0],
                0,
                stdout=(
                    "github.com\n"
                    "  ✓ Logged in to github.com account user\n"
                    "  - Token scopes: 'admin:public_key', 'admin:ssh_signing_key', 'repo'\n"
                ),
                stderr="",
            ),
        )
        ok, msg = ensure_gh_scopes(
            scopes=["admin:public_key", "admin:ssh_signing_key"], interactive=False
        )
        assert ok is True
        assert "present" in msg

    def test_returns_false_when_missing_scope_noninteractive(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0],
                0,
                stdout=(
                    "github.com\n  - Token scopes: 'admin:ssh_signing_key', 'repo'\n"
                ),
                stderr="",
            ),
        )
        ok, msg = ensure_gh_scopes(
            scopes=["admin:public_key", "admin:ssh_signing_key"], interactive=False
        )
        assert ok is False
        assert "Missing OAuth scopes" in msg
        assert "admin:public_key" in msg
        assert "admin:ssh_signing_key" not in msg

    def test_parses_scopes_from_stderr_fallback(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0],
                0,
                stdout="",
                stderr=(
                    "github.com\n"
                    "  - Token scopes: 'admin:public_key', 'admin:ssh_signing_key'\n"
                ),
            ),
        )
        ok, msg = ensure_gh_scopes(
            scopes=["admin:public_key", "admin:ssh_signing_key"], interactive=False
        )
        assert ok is True

    def test_returns_false_when_gh_auth_fails(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0], 1, stdout="", stderr="not logged in"
            ),
        )
        ok, msg = ensure_gh_scopes(
            scopes=["admin:public_key", "admin:ssh_signing_key"], interactive=False
        )
        assert ok is False

    def test_parses_scopes_when_split_across_streams(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0],
                0,
                stdout="Logged in to github.com account user\n",
                stderr="  - Token scopes: 'admin:public_key', 'admin:ssh_signing_key'\n",
            ),
        )
        ok, msg = ensure_gh_scopes(
            scopes=["admin:public_key", "admin:ssh_signing_key"], interactive=False
        )
        assert ok is True
        assert "present" in msg


@pytest.mark.unit
class TestUploadAuthKey:
    def test_skips_upload_when_auth_key_exists(self, monkeypatch, tmp_path):
        key_path = tmp_path / "id_rsa"
        key_path.write_text("ssh-rsa AAAA user@host")
        pub_path = tmp_path / "id_rsa.pub"
        pub_path.write_text("ssh-rsa AAAA user@host")

        monkeypatch.setattr(
            "shell_configs.signing._run",
            lambda *a, **kw: subprocess.CompletedProcess(
                a[0],
                0,
                stdout="title\tssh-rsa AAAA\t2026-01-01\t123\tauthentication\n",
                stderr="",
            ),
        )
        ok, msg = upload_auth_key(key_path)
        assert ok is True
        assert "already uploaded" in msg

    def test_uploads_when_only_signing_key_exists(self, monkeypatch, tmp_path):
        key_path = tmp_path / "id_rsa"
        key_path.write_text("ssh-rsa AAAA user@host")
        pub_path = tmp_path / "id_rsa.pub"
        pub_path.write_text("ssh-rsa AAAA user@host")

        calls = []

        def mock_run(*a, **kw):
            cmd = a[0] if a else kw.get("args", [])
            calls.append(cmd)
            if "ssh-key" in cmd and "list" in cmd:
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="title\tssh-rsa AAAA\t2026-01-01\t123\tsigning\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr("shell_configs.signing._run", mock_run)
        ok, msg = upload_auth_key(key_path)
        assert ok is True
        assert any("ssh-key" in str(c) and "add" in str(c) for c in calls)

    def test_uploads_when_key_not_found(self, monkeypatch, tmp_path):
        key_path = tmp_path / "id_rsa"
        key_path.write_text("ssh-rsa BBBB user@host")
        pub_path = tmp_path / "id_rsa.pub"
        pub_path.write_text("ssh-rsa BBBB user@host")

        calls = []

        def mock_run(*a, **kw):
            cmd = a[0] if a else kw.get("args", [])
            calls.append(cmd)
            if "ssh-key" in cmd and "list" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr("shell_configs.signing._run", mock_run)
        ok, msg = upload_auth_key(key_path)
        assert ok is True
        assert any("ssh-key" in str(c) and "add" in str(c) for c in calls)

    def test_handles_malformed_gh_output(self, monkeypatch, tmp_path):
        key_path = tmp_path / "id_rsa"
        key_path.write_text("ssh-rsa CCCC user@host")
        pub_path = tmp_path / "id_rsa.pub"
        pub_path.write_text("ssh-rsa CCCC user@host")

        calls = []

        def mock_run(*a, **kw):
            cmd = a[0] if a else kw.get("args", [])
            calls.append(cmd)
            if "ssh-key" in cmd and "list" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="malformed output no tabs\n", stderr=""
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr("shell_configs.signing._run", mock_run)
        ok, msg = upload_auth_key(key_path)
        assert ok is True
        assert any("ssh-key" in str(c) and "add" in str(c) for c in calls)


@pytest.mark.unit
class TestFindStaleGithubKeys:
    """Regression tests for stale-key detection by computed fingerprint."""

    def _mock_run(
        self, gh_stdout: str
    ) -> Callable[..., subprocess.CompletedProcess[str]]:
        # ssh-keygen fingerprints by a marker in the piped key; gh list is fixed.
        def mock_run(*a, **kw):
            cmd = a[0] if a else kw.get("args", [])
            if cmd[:2] == ["gh", "ssh-key"]:
                return _make_result(0, stdout=gh_stdout)
            if cmd[:2] == ["ssh-keygen", "-lf"]:
                key = kw.get("input", "")
                fp = "SHA256:STALE" if "STALEKEY" in key else "SHA256:LOCAL"
                return _make_result(0, stdout=f"256 {fp} comment (ED25519)")
            return _make_result(0)

        return mock_run

    def test_flags_only_keys_with_mismatched_fingerprint(self, monkeypatch, tmp_path):
        key_path = tmp_path / "id_ed25519"
        key_path.with_suffix(".pub").write_text("ssh-ed25519 LOCALKEY user@host\n")

        # Real `gh ssh-key list` columns: title, key, added, id, type — no
        # fingerprint column, so the local matching key must NOT be reported.
        gh_stdout = (
            "laptop\tssh-ed25519 LOCALKEY\t2024-01-01\t111\tauthentication\n"
            "old-host\tssh-ed25519 STALEKEY\t2023-01-01\t222\tauthentication\n"
        )
        monkeypatch.setattr("shell_configs.signing._run", self._mock_run(gh_stdout))

        from shell_configs.signing import find_stale_github_keys

        stale, current_fp = find_stale_github_keys(key_path)

        assert current_fp == "SHA256:LOCAL"
        assert [(k.title, k.fingerprint) for k in stale] == [
            ("old-host", "SHA256:STALE")
        ]

    def test_returns_empty_when_local_pub_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("shell_configs.signing._run", self._mock_run(""))

        from shell_configs.signing import find_stale_github_keys

        stale, current_fp = find_stale_github_keys(tmp_path / "absent")

        assert stale == []
        assert current_fp is None


@pytest.mark.unit
class TestGetPubFingerprint:
    """get_pub_fingerprint degrades gracefully on unreadable .pub files."""

    def test_missing_file_returns_empty(self, tmp_path):
        from shell_configs.signing import get_pub_fingerprint

        assert get_pub_fingerprint(tmp_path / "nope.pub") == ""

    def test_unreadable_path_returns_empty(self, tmp_path):
        from shell_configs.signing import get_pub_fingerprint

        # Reading a directory raises IsADirectoryError (an OSError subclass).
        assert get_pub_fingerprint(tmp_path) == ""
