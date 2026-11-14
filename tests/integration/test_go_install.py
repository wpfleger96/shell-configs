"""Integration tests for the bundled Linux Go install command.

The real ``install_cmd`` runs under ``/bin/sh`` with stub ``sudo`` and ``curl``
first on PATH: ``sudo`` redirects ``/usr/local`` paths into a temp root, and
``curl`` serves a canned version string and tarball per ``CURL_MODE``.
"""

from __future__ import annotations

import io
import os
import random
import subprocess
import tarfile

from pathlib import Path

import pytest

from shell_configs.languages import load_languages

_STUB_SUDO = """#!/bin/sh
for arg do
  shift
  case "$arg" in /usr/local*) arg="$TMP_ROOT${arg#/usr/local}" ;; esac
  set -- "$@" "$arg"
done
exec "$@"
"""

_STUB_CURL = """#!/bin/sh
for url do :; done
case "$url" in
  *VERSION*) [ "$CURL_MODE" = version-fail ] && exit 22; echo go1.99.0 ;;
  *) case "$CURL_MODE" in
       ok) cat "$STUB_DIR/full.tar.gz" ;;
       truncated) cat "$STUB_DIR/short.tar.gz" ;;
       *) exit 22 ;;
     esac ;;
esac
"""


@pytest.fixture
def guard_subprocess() -> None:
    """Allow the real shell: every external call it makes is stubbed or sandboxed."""


def _go_tarball() -> bytes:
    """Build a Go tarball: bin/go, then an incompressible payload.

    Truncating it halfway cuts into the payload, so tar extracts bin/go before
    it fails, as a dropped download of the real tarball would.
    """
    members = {
        "go/bin/go": b"#!/bin/sh\necho go1.99.0\n",
        "go/payload": random.Random(0).randbytes(256 * 1024),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _run_install(tmp_path: Path, mode: str) -> subprocess.CompletedProcess[str]:
    install_cmd = next(
        lang for lang in load_languages() if lang.name == "go"
    ).install_cmd
    assert install_cmd is not None

    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    for name, body in {"sudo": _STUB_SUDO, "curl": _STUB_CURL}.items():
        stub = stub_dir / name
        stub.write_text(body)
        stub.chmod(0o755)
    tarball = _go_tarball()
    (stub_dir / "full.tar.gz").write_bytes(tarball)
    (stub_dir / "short.tar.gz").write_bytes(tarball[: len(tarball) // 2])

    env = {
        **os.environ,
        "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}",
        "TMP_ROOT": str(tmp_path / "root"),
        "STUB_DIR": str(stub_dir),
        "CURL_MODE": mode,
    }
    return subprocess.run(
        install_cmd, shell=True, env=env, capture_output=True, text=True
    )


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "root"
    path.mkdir()
    return path


@pytest.mark.integration
class TestGoInstall:
    def test_ok_replaces_old_tree(self, tmp_path: Path, root: Path) -> None:
        (root / "go").mkdir()
        (root / "go" / "MARKER").touch()

        result = _run_install(tmp_path, "ok")

        assert result.returncode == 0, result.stderr
        assert (root / "go" / "bin" / "go").is_file()
        assert not (root / "go" / "MARKER").exists()
        assert not (root / ".go-install").exists()

    def test_leftover_staging_dir_cleared_and_installs(
        self, tmp_path: Path, root: Path
    ) -> None:
        (root / ".go-install").mkdir()
        (root / ".go-install" / "junk").touch()

        result = _run_install(tmp_path, "ok")

        assert result.returncode == 0, result.stderr
        assert (root / "go" / "bin" / "go").is_file()
        assert not (root / ".go-install").exists()

    @pytest.mark.parametrize("mode", ["404", "truncated", "version-fail"])
    def test_failed_download_keeps_old_tree(
        self, tmp_path: Path, root: Path, mode: str
    ) -> None:
        (root / "go").mkdir()
        (root / "go" / "MARKER").touch()

        result = _run_install(tmp_path, mode)

        assert result.returncode != 0
        assert (root / "go" / "MARKER").exists()
        assert not (root / "go" / "bin" / "go").exists()
        assert not (root / ".go-install").exists()

    def test_failed_fresh_download_leaves_no_go_dir(
        self, tmp_path: Path, root: Path
    ) -> None:
        result = _run_install(tmp_path, "404")

        assert result.returncode != 0
        assert not (root / "go").exists()
