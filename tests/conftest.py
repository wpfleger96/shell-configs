"""Pytest configuration and fixtures."""

import subprocess
import tempfile

from pathlib import Path
from typing import Any

import pytest

from click.testing import CliRunner

PASSTHROUGH_COMMANDS = {"bash", "git", "zsh"}

STUB_COMMANDS = {
    "brew",
    "code",
    "curl",
    "cursor",
    "defaults",
    "gh",
    "go",
    "node",
    "ruby",
    "rustup",
    "ssh",
    "ssh-add",
    "sudo",
    "uv",
}


def _stub_ssh_keygen(cmd: list[Any]) -> subprocess.CompletedProcess[str]:
    """Stub ssh-keygen that writes dummy key files when generating."""
    try:
        str_cmd = [str(c) for c in cmd]
        if "-f" in str_cmd:
            key_path = Path(str_cmd[str_cmd.index("-f") + 1])
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text(
                "-----BEGIN OPENSSH PRIVATE KEY-----\n"
                "FAKEKEYDATA\n"
                "-----END OPENSSH PRIVATE KEY-----\n"
            )
            key_path.with_suffix(".pub").write_text(
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAFAKEKEYDATA test@stubbed\n"
            )
    except (ValueError, IndexError):
        pass
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


@pytest.fixture(autouse=True)
def guard_subprocess(monkeypatch):
    """Block real subprocess calls, return no-op results for known commands.

    Prevents tests from hitting real system commands (IDE CLIs, package
    managers, SSH tools). Commands in PASSTHROUGH_COMMANDS execute normally
    (needed for syntax validation). Commands in STUB_COMMANDS get a
    successful empty result. Unknown commands raise RuntimeError so new
    subprocess usage is caught immediately.
    """
    real_run = subprocess.run

    def _guarded_run(cmd, *args, **kwargs):
        exe = (cmd[0] if isinstance(cmd, list) else cmd.split()[0]).rsplit("/", 1)[-1]
        if exe in PASSTHROUGH_COMMANDS:
            return real_run(cmd, *args, **kwargs)
        if exe == "ssh-keygen":
            return _stub_ssh_keygen(cmd if isinstance(cmd, list) else cmd.split())
        if exe in STUB_COMMANDS:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="", stderr=""
            )
        raise RuntimeError(
            f"Subprocess call to '{exe}' blocked by test guard. "
            f"Add to PASSTHROUGH_COMMANDS or STUB_COMMANDS in conftest.py, "
            f"or mock it in your test."
        )

    monkeypatch.setattr(subprocess, "run", _guarded_run)


@pytest.fixture(autouse=True)
def mock_platform_for_tests(monkeypatch):
    """Force non-WSL platform detection during tests.

    This prevents tests from accidentally modifying real Windows files
    when running on WSL. The WSL-specific code paths can be tested
    with dedicated unit tests that explicitly mock the platform.
    """
    from shell_configs.platform import Platform, detect_platform

    detect_platform.cache_clear()
    monkeypatch.setattr(
        "shell_configs.platform.detect_platform",
        lambda: Platform.LINUX,
    )
    yield
    detect_platform.cache_clear()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_home(temp_dir, monkeypatch):
    """Create isolated home directory for tests.

    This fixture:
    1. Sets HOME environment variable to temp directory
    2. Patches Path.home() to return the temp directory

    This double-patching ensures complete isolation even if code
    uses Path.home() directly instead of reading HOME.
    """
    home = temp_dir / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def test_repo(temp_dir, monkeypatch):
    repo = (temp_dir / "repo").resolve()
    repo.mkdir()

    config_dir = repo / "config"
    config_dir.mkdir()

    bash_dir = config_dir / "bash"
    bash_dir.mkdir()
    (bash_dir / "bashrc").write_text("# Test bash config\nalias test='echo test'\n")

    zsh_dir = config_dir / "zsh"
    zsh_dir.mkdir()
    (zsh_dir / "zshrc").write_text("# Test zsh config\nalias test='echo test'\n")

    git_dir = config_dir / "git"
    git_dir.mkdir()

    shared_gitconfig = config_dir / "shared.gitconfig"
    shared_gitconfig.write_text("[user]\n    name = Test User\n")

    monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)

    return repo


@pytest.fixture
def cli_runner():
    return CliRunner(env={"COLUMNS": "200"})
