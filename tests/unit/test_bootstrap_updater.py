"""Tests for update checking and application utilities."""

import subprocess

import pytest

from shell_configs.bootstrap.installer import UV_NOT_FOUND_ERROR
from shell_configs.bootstrap.updater import (
    check_github_updates,
    fetch_changelog_entries,
    perform_github_update,
)


@pytest.mark.unit
@pytest.mark.bootstrap
class TestCheckGitHubUpdates:
    """Tests for check_github_updates function."""

    def test_check_github_no_update(self, monkeypatch):
        """Test when current version is up to date."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = "v1.0.0\n"
                stderr = ""

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False
        assert update_info.current_version == "1.0.0"
        assert update_info.latest_version == "1.0.0"

    def test_check_github_has_update(self, monkeypatch):
        """Test when newer version is available."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = "v1.1.0\n"
                stderr = ""

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is True
        assert update_info.current_version == "1.0.0"
        assert update_info.latest_version == "1.1.0"
        assert update_info.source == "github"

    def test_check_github_network_error(self, monkeypatch):
        """Test handling of network errors."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            raise Exception("Network error")

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False

    def test_check_github_no_tags(self, monkeypatch):
        """Test when repository has no tags."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = "\n"
                stderr = ""

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False

    def test_check_github_gh_not_installed(self, monkeypatch):
        """Test when gh CLI is not available."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: False
        )

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False
        assert update_info.current_version == "1.0.0"
        assert update_info.latest_version == "1.0.0"

    def test_check_github_gh_api_failure(self, monkeypatch):
        """Test handling of gh api failures (auth, rate limit, etc)."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 1
                stdout = ""
                stderr = "gh api failed for some reason"

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False

    def test_check_github_timeout(self, monkeypatch):
        """Test handling of timeout."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired("gh", 10)

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False


@pytest.mark.unit
@pytest.mark.bootstrap
class TestPerformGitHubUpdate:
    """Tests for perform_github_update function."""

    def test_perform_github_update_without_uv(self, monkeypatch):
        """Test that missing uv returns error."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: False
        )
        success, message, was_upgraded = perform_github_update(
            "git+ssh://git@github.com/owner/repo.git"
        )
        assert success is False
        assert message == UV_NOT_FOUND_ERROR
        assert was_upgraded is False

    def test_perform_github_update_success(self, monkeypatch):
        """Test successful upgrade."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(*args, **kwargs):
            class Result:
                returncode = 0
                stderr = ""
                stdout = "Upgraded test-package from 1.0.0 to 1.1.0"

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)
        success, message, was_upgraded = perform_github_update(
            "git+ssh://git@github.com/owner/repo.git"
        )
        assert success is True
        assert "successful" in message.lower()
        assert was_upgraded is True

    def test_perform_github_update_failure(self, monkeypatch):
        """Test upgrade failure."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(*args, **kwargs):
            class Result:
                returncode = 1
                stderr = "Package not found"
                stdout = ""

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)
        success, message, was_upgraded = perform_github_update(
            "git+ssh://git@github.com/owner/nonexistent.git"
        )
        assert success is False
        assert "Package not found" in message
        assert was_upgraded is False

    def test_perform_github_update_timeout(self, monkeypatch):
        """Test handling of timeout."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired("uv", 60)

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)
        success, message, was_upgraded = perform_github_update(
            "git+ssh://git@github.com/owner/repo.git"
        )
        assert success is False
        assert "timed out" in message.lower()
        assert was_upgraded is False

    def test_perform_github_update_unexpected_exception(self, monkeypatch):
        """Test handling of unexpected errors."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(*args, **kwargs):
            raise ValueError("Unexpected error")

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)
        success, message, was_upgraded = perform_github_update(
            "git+ssh://git@github.com/owner/repo.git"
        )
        assert success is False
        assert "Unexpected error" in message
        assert was_upgraded is False

    def test_perform_github_update_empty_stderr(self, monkeypatch):
        """Test handling of failures with no stderr."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(*args, **kwargs):
            class Result:
                returncode = 1
                stderr = ""
                stdout = ""

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)
        success, message, was_upgraded = perform_github_update(
            "git+ssh://git@github.com/owner/repo.git"
        )
        assert success is False
        assert "failed" in message.lower()
        assert was_upgraded is False

    def test_github_upgrade_with_reinstall_flag(self, monkeypatch):
        """Test that GitHub upgrades include --reinstall flag."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        captured_args = []

        def mock_run(*args, **kwargs):
            captured_args.append(args)

            class Result:
                returncode = 0
                stderr = ""
                stdout = "Successfully installed shell-configs"

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)
        success, message, was_upgraded = perform_github_update(
            "git+ssh://git@github.com/owner/repo.git"
        )

        assert success is True
        assert was_upgraded is True
        assert len(captured_args) == 1
        cmd = captured_args[0][0]
        assert "--force" in cmd
        assert "--reinstall" in cmd
        assert was_upgraded is True


@pytest.mark.unit
@pytest.mark.bootstrap
class TestFetchChangelogEntries:
    """Tests for fetch_changelog_entries function."""

    def test_returns_entries_in_version_range(self, monkeypatch):
        """Test that only releases between current and latest are returned."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        releases_json = '[{"tag_name": "v1.2.0", "body": "notes 1.2.0"}, {"tag_name": "v1.1.0", "body": "notes 1.1.0"}, {"tag_name": "v1.0.0", "body": "notes 1.0.0"}]'

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = releases_json
                stderr = ""

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        entries = fetch_changelog_entries("owner/repo", "1.0.0", "1.2.0")
        versions = [v for v, _ in entries]
        assert "1.2.0" in versions
        assert "1.1.0" in versions
        assert "1.0.0" not in versions

    def test_empty_releases_returns_empty_list(self, monkeypatch):
        """Test that an empty releases list returns an empty result."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = "[]"
                stderr = ""

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        entries = fetch_changelog_entries("owner/repo", "1.0.0", "1.2.0")
        assert entries == []

    def test_gh_not_available_returns_empty_list(self, monkeypatch):
        """Test that missing gh CLI returns empty list without calling subprocess."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: False
        )

        entries = fetch_changelog_entries("owner/repo", "1.0.0", "1.2.0")
        assert entries == []

    def test_gh_api_failure_returns_empty_list(self, monkeypatch):
        """Test that a non-zero gh exit code returns empty list."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.is_command_available", lambda cmd: True
        )

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 1
                stdout = ""
                stderr = "API rate limit exceeded"

            return Result()

        monkeypatch.setattr("shell_configs.bootstrap.updater.subprocess.run", mock_run)

        entries = fetch_changelog_entries("owner/repo", "1.0.0", "1.2.0")
        assert entries == []
