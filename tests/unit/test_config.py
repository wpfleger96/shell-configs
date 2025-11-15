"""Unit tests for the ConfigReader."""

import pytest

from shell_configs.config import ConfigReader, find_repo_root


@pytest.mark.unit
class TestConfigReader:
    """Test the ConfigReader class."""

    def test_get_config_content_exists(self, test_repo):
        reader = ConfigReader(test_repo)
        content = reader.get_config_content("bash", "bashrc")

        assert content is not None
        assert "Test bash config" in content
        assert "alias test='echo test'" in content

    def test_get_config_content_not_found(self, test_repo):
        reader = ConfigReader(test_repo)
        content = reader.get_config_content("bash", "nonexistent")

        assert content is None

    def test_get_available_shells(self, test_repo):
        reader = ConfigReader(test_repo)
        shells = reader.get_available_shells()

        assert set(shells) == {"bash", "git", "zsh"}

    def test_get_available_shells_empty(self, temp_dir):
        reader = ConfigReader(temp_dir)
        shells = reader.get_available_shells()

        assert shells == []


@pytest.mark.unit
class TestFindRepoRoot:
    """Test the find_repo_root function."""

    def test_find_repo_root_from_root(self, test_repo):
        root = find_repo_root(test_repo)

        assert root == test_repo

    def test_find_repo_root_from_subdirectory(self, test_repo):
        subdir = test_repo / "config" / "bash"
        root = find_repo_root(subdir)

        assert root == test_repo

    def test_find_repo_root_not_found(self, temp_dir):
        other_dir = temp_dir / "other"
        other_dir.mkdir()
        root = find_repo_root(other_dir)

        assert root is None

    def test_get_shared_config_content_exists(self, test_repo):
        reader = ConfigReader(test_repo)

        shared_sh = test_repo / "config" / "shared.sh"
        shared_sh.write_text("# Shared shell config\nalias ll='ls -la'")

        shared_git = test_repo / "config" / "shared.gitconfig"
        shared_git.write_text("[alias]\n    st = status")

        shell_content = reader.get_shared_config_content("bash")
        assert shell_content == "# Shared shell config\nalias ll='ls -la'"

        git_content = reader.get_shared_config_content("git")
        assert git_content == "[alias]\n    st = status"

    def test_get_shared_config_content_missing(self, test_repo):
        reader = ConfigReader(test_repo)

        content = reader.get_shared_config_content("bash")

        assert content is None
