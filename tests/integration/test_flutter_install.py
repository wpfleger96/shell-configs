"""Integration tests for the bundled Linux Flutter install command.

The real ``install_cmd`` runs under ``/bin/sh`` with stub ``brew``, ``uname``,
``sudo`` and ``curl`` first on PATH: ``brew`` fails so the fallback runs,
``uname`` reports ``UNAME_SM``, ``sudo`` redirects ``/usr/local`` paths into a
temp root, and ``curl`` serves a canned releases manifest and archive per
``CURL_MODE``.
"""

from __future__ import annotations

import io
import json
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
  */releases/releases_linux.json) [ "$CURL_MODE" = releases-fail ] && exit 22; cat "$STUB_DIR/releases.json" ;;
  */releases/stable/linux/flutter_linux_9.9.9-stable.tar.xz) case "$CURL_MODE" in
       ok) cat "$STUB_DIR/full.tar.xz" ;;
       truncated) cat "$STUB_DIR/short.tar.xz" ;;
       no-binary) cat "$STUB_DIR/no-binary.tar.xz" ;;
       *) exit 22 ;;
     esac ;;
  *) exit 22 ;;
esac
"""

_RELEASES = {
    "current_release": {"stable": "abc123"},
    "releases": [
        {
            "hash": "abc123",
            "channel": "stable",
            "archive": "stable/linux/flutter_linux_9.9.9-stable.tar.xz",
        }
    ],
}


@pytest.fixture
def guard_subprocess() -> None:
    """Allow the real shell: every external call it makes is stubbed or sandboxed."""


def _flutter_archive(*, with_binary: bool = True) -> bytes:
    """Build an SDK archive: bin/flutter, then an incompressible payload.

    Truncating it halfway cuts into the payload, so tar extracts bin/flutter
    before it fails, as a dropped download of the real SDK would.
    """
    members = {"flutter/payload": random.Random(0).randbytes(256 * 1024)}
    if with_binary:
        members = {"flutter/bin/flutter": b"#!/bin/sh\necho Flutter 9.9.9\n"} | members
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _run_install(
    tmp_path: Path, mode: str, uname: str = "Linux x86_64"
) -> subprocess.CompletedProcess[str]:
    install_cmd = next(
        lang for lang in load_languages() if lang.name == "flutter"
    ).install_cmd
    assert install_cmd is not None

    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    stubs = {
        "brew": "#!/bin/sh\nexit 1\n",
        "uname": '#!/bin/sh\necho "$UNAME_SM"\n',
        "sudo": _STUB_SUDO,
        "curl": _STUB_CURL,
    }
    for name, body in stubs.items():
        stub = stub_dir / name
        stub.write_text(body)
        stub.chmod(0o755)
    archive = _flutter_archive()
    (stub_dir / "full.tar.xz").write_bytes(archive)
    (stub_dir / "short.tar.xz").write_bytes(archive[: len(archive) // 2])
    (stub_dir / "no-binary.tar.xz").write_bytes(_flutter_archive(with_binary=False))
    (stub_dir / "releases.json").write_text(json.dumps(_RELEASES))

    env = {
        **os.environ,
        "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}",
        "TMP_ROOT": str(tmp_path / "root"),
        "STUB_DIR": str(stub_dir),
        "CURL_MODE": mode,
        "UNAME_SM": uname,
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
class TestFlutterInstall:
    def test_ok_replaces_old_tree(self, tmp_path: Path, root: Path) -> None:
        (root / "flutter").mkdir()
        (root / "flutter" / "MARKER").touch()

        result = _run_install(tmp_path, "ok")

        assert result.returncode == 0, result.stderr
        assert (root / "flutter" / "bin" / "flutter").is_file()
        assert not (root / "flutter" / "MARKER").exists()
        assert not (root / ".flutter-install").exists()

    def test_leftover_staging_dir_cleared_and_installs(
        self, tmp_path: Path, root: Path
    ) -> None:
        (root / ".flutter-install").mkdir()
        (root / ".flutter-install" / "junk").touch()

        result = _run_install(tmp_path, "ok")

        assert result.returncode == 0, result.stderr
        assert (root / "flutter" / "bin" / "flutter").is_file()
        assert not (root / ".flutter-install").exists()

    @pytest.mark.parametrize("mode", ["404", "truncated", "no-binary", "releases-fail"])
    def test_failed_download_keeps_old_tree(
        self, tmp_path: Path, root: Path, mode: str
    ) -> None:
        (root / "flutter").mkdir()
        (root / "flutter" / "MARKER").touch()

        result = _run_install(tmp_path, mode)

        assert result.returncode != 0
        assert (root / "flutter" / "MARKER").exists()
        assert not (root / "flutter" / "bin" / "flutter").exists()
        assert not (root / ".flutter-install").exists()

    def test_failed_fresh_download_leaves_no_flutter_dir(
        self, tmp_path: Path, root: Path
    ) -> None:
        result = _run_install(tmp_path, "404")

        assert result.returncode != 0
        assert not (root / "flutter").exists()

    @pytest.mark.parametrize("uname", ["Darwin arm64", "Linux aarch64"])
    def test_platform_without_linux_x64_archive_installs_nothing(
        self, tmp_path: Path, root: Path, uname: str
    ) -> None:
        result = _run_install(tmp_path, "ok", uname)

        assert result.returncode != 0
        assert "install Flutter manually" in result.stderr
        assert list(root.iterdir()) == []
