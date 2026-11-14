"""Integration tests for bundled recipes that download an installer and run it.

Recipes run under ``/bin/sh``, which has no ``pipefail``, so ``curl -f URL | sh``
still exits 0 when curl fails: the shell reads empty stdin and succeeds. Each
recipe runs with a ``curl`` stub and with recording stubs for every command
that would act on the download. The recorder also logs a ``CONFIGURE`` env
prefix, so recipes that set one are checked too.
"""

from __future__ import annotations

import os
import subprocess

from collections.abc import Callable
from pathlib import Path

import pytest

from shell_configs.agents import load_agents
from shell_configs.languages import load_languages
from shell_configs.packages.packages import load_packages

_RECORDER = """#!/bin/sh
{ echo "${CONFIGURE+CONFIGURE=$CONFIGURE }$(basename "$0") $*"; cat; } >> "$STUB_DIR/ran"
"""


@pytest.fixture
def guard_subprocess() -> None:
    """Allow the real shell: every external call it makes is stubbed or sandboxed."""


def _agent_cmd(name: str) -> str:
    cmd = next(agent for agent in load_agents() if agent.name == name).install_cmd
    assert cmd is not None
    return cmd


def _language_cmd(name: str) -> str:
    cmd = next(lang for lang in load_languages() if lang.name == name).install_cmd
    assert cmd is not None
    return cmd


def _package_cmd(name: str) -> str:
    pkg = next(pkg for pkg in load_packages() if pkg.name == name)
    assert pkg.linux is not None and pkg.linux.install_cmd is not None
    return pkg.linux.install_cmd


def _run(
    tmp_path: Path, install_cmd: str, curl_stub: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    stubs = {"curl": curl_stub, "gpg": "#!/bin/sh\ncat >/dev/null\n"}
    stubs |= dict.fromkeys(["sh", "bash", "sudo", "python3"], _RECORDER)
    for stub_name, body in stubs.items():
        stub = stub_dir / stub_name
        stub.write_text(body)
        stub.chmod(0o755)

    env = {
        **{k: v for k, v in os.environ.items() if k != "CONFIGURE"},
        "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "STUB_DIR": str(stub_dir),
    }
    result = subprocess.run(
        install_cmd, shell=True, env=env, capture_output=True, text=True
    )
    return result, stub_dir / "ran"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("load_cmd", "name"),
    [
        pytest.param(_agent_cmd, "claude-code", id="claude-code"),
        pytest.param(_agent_cmd, "goose", id="goose"),
        pytest.param(_agent_cmd, "codex", id="codex"),
        pytest.param(_agent_cmd, "amp", id="amp"),
        pytest.param(_language_cmd, "rust", id="rust"),
        pytest.param(_language_cmd, "node", id="node"),
        pytest.param(_language_cmd, "ruby", id="ruby"),
        pytest.param(_package_cmd, "shfmt", id="shfmt"),
        pytest.param(_package_cmd, "git-delta", id="git-delta"),
        pytest.param(_package_cmd, "just", id="just"),
        pytest.param(_package_cmd, "pnpm", id="pnpm"),
        pytest.param(_package_cmd, "tflint", id="tflint"),
    ],
)
def test_failed_download_fails_without_running_anything(
    tmp_path: Path, load_cmd: Callable[[str], str], name: str
) -> None:
    result, ran = _run(tmp_path, load_cmd(name), "#!/bin/sh\nexit 22\n")

    assert result.returncode != 0
    assert not ran.exists(), ran.read_text()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("load_cmd", "name", "runner"),
    [
        pytest.param(_agent_cmd, "claude-code", "bash ", id="claude-code"),
        pytest.param(_agent_cmd, "goose", "CONFIGURE=false bash ", id="goose"),
        pytest.param(_agent_cmd, "codex", "sh ", id="codex"),
        pytest.param(_agent_cmd, "amp", "bash ", id="amp"),
        pytest.param(_language_cmd, "rust", "sh -s -- -y", id="rust"),
        pytest.param(_language_cmd, "node", "bash ", id="node"),
        pytest.param(_language_cmd, "ruby", "bash -s stable", id="ruby"),
        pytest.param(_package_cmd, "shfmt", "sh ", id="shfmt"),
        pytest.param(_package_cmd, "git-delta", "sh ", id="git-delta"),
        pytest.param(
            _package_cmd, "just", "bash -s -- --to {home}/.local/bin", id="just"
        ),
        pytest.param(_package_cmd, "pnpm", "sh -", id="pnpm"),
    ],
)
def test_downloaded_installer_is_piped_to_shell(
    tmp_path: Path, load_cmd: Callable[[str], str], name: str, runner: str
) -> None:
    _, ran = _run(tmp_path, load_cmd(name), "#!/bin/sh\necho 'echo installer'\n")

    expected_runner = runner.format(home=tmp_path)
    assert ran.read_text() == f"{expected_runner}\necho installer\n"
