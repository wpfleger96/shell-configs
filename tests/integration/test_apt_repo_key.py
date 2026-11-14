"""Integration tests for fetching an apt repo's signing key in ``_setup_apt_repo``.

The real method runs with ``curl``, ``sudo`` and ``gpg`` stubs first on PATH.
``sudo`` and ``gpg`` only record their arguments (and stdin for ``gpg``/``tee``),
so nothing touches ``/usr/share/keyrings`` or ``/etc/apt``. The repo name is
unique, so the existing-key check never skips the fetch.
"""

from __future__ import annotations

import os
import subprocess
import uuid

from pathlib import Path

import pytest

from shell_configs.packages.packages import AptRepo, LinuxInstaller

_RECORDER = """#!/bin/sh
echo "$(basename "$0") $*" >> "$STUB_DIR/ran"
case "$1" in gpg|tee) cat >> "$STUB_DIR/ran" ;; esac
"""


@pytest.fixture
def guard_subprocess() -> None:
    """Allow real subprocesses: every external call is stubbed."""


def _setup_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, curl_stub: str
) -> tuple[str, Path]:
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    for name, body in {"curl": curl_stub, "sudo": _RECORDER, "gpg": _RECORDER}.items():
        stub = stub_dir / name
        stub.write_text(body)
        stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{stub_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STUB_DIR", str(stub_dir))

    name = f"shell-configs-test-{uuid.uuid4().hex}"
    repo = AptRepo(
        name=name,
        key_url="https://example.invalid/key.gpg",
        source="deb https://example.invalid stable main",
    )
    LinuxInstaller()._setup_apt_repo(repo)
    return f"/usr/share/keyrings/{name}-archive-keyring.gpg", stub_dir / "ran"


@pytest.mark.integration
class TestAptRepoKey:
    def test_failed_key_download_raises_without_running_gpg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with pytest.raises(subprocess.CalledProcessError):
            _setup_repo(tmp_path, monkeypatch, "#!/bin/sh\nexit 22\n")

        ran = tmp_path / "stubs" / "ran"
        assert not ran.exists(), ran.read_text()

    def test_downloaded_key_is_piped_to_gpg_dearmor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        key_path, ran = _setup_repo(
            tmp_path, monkeypatch, "#!/bin/sh\necho 'ARMORED KEY'\n"
        )

        assert ran.read_text().startswith(
            f"sudo gpg --dearmor -o {key_path}\nARMORED KEY\n"
        )
