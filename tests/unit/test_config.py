"""Unit tests for the ConfigReader."""

import pytest

from shell_configs.config import ConfigReader
from shell_configs.shells.bash import BashShell
from shell_configs.shells.git import GitShell


@pytest.mark.unit
class TestConfigReader:
    """Test the ConfigReader class."""

    def test_get_config_content_exists(self, test_repo, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.config.get_config_dir", lambda: test_repo / "config"
        )
        reader = ConfigReader()
        content = reader.get_config_content("bash", "bashrc")

        assert content is not None
        assert "Test bash config" in content
        assert "alias test='echo test'" in content

    def test_get_config_content_not_found(self, test_repo, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.config.get_config_dir", lambda: test_repo / "config"
        )
        reader = ConfigReader()
        content = reader.get_config_content("bash", "nonexistent")

        assert content is None

    def test_get_available_shells(self, test_repo, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.config.get_config_dir", lambda: test_repo / "config"
        )
        reader = ConfigReader()
        shells = reader.get_available_shells()

        assert set(shells) == {"bash", "git", "zsh"}

    def test_get_available_shells_empty(self, temp_dir, monkeypatch):
        empty_config = temp_dir / "empty_config"
        empty_config.mkdir()
        monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: empty_config)
        reader = ConfigReader()
        shells = reader.get_available_shells()

        assert shells == []

    def test_get_shared_config_content_exists(self, test_repo, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.config.get_config_dir", lambda: test_repo / "config"
        )
        reader = ConfigReader()

        shared_sh = test_repo / "config" / "shared.sh"
        shared_sh.write_text("# Shared shell config\nalias ll='ls -la'")

        shared_git = test_repo / "config" / "shared.gitconfig"
        shared_git.write_text("[alias]\n    st = status")

        shell_content = reader.get_shared_config_content(BashShell())
        expected_shell = f"export SHELL_CONFIGS_DIR=\"{test_repo / 'config'}\"\n\n# Shared shell config\nalias ll='ls -la'"
        assert shell_content == expected_shell

        git_content = reader.get_shared_config_content(GitShell())
        assert git_content == "[alias]\n    st = status"

    def test_get_shared_config_content_missing(self, test_repo, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.config.get_config_dir", lambda: test_repo / "config"
        )
        reader = ConfigReader()

        content = reader.get_shared_config_content(BashShell())

        assert content is None
