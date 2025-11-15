"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_home(temp_dir, monkeypatch):
    home = temp_dir / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def test_repo(temp_dir):
    repo = temp_dir / "repo"
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

    return repo


@pytest.fixture
def cli_runner():
    return CliRunner()
