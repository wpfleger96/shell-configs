"""Pytest configuration and fixtures."""

import tempfile

from pathlib import Path

import pytest

from click.testing import CliRunner


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
