"""Tests for update checking and application utilities."""

import json
import subprocess
import urllib.error

import pytest

from shell_configs.bootstrap.installer import UV_NOT_FOUND_ERROR
from shell_configs.bootstrap.updater import check_github_updates, perform_github_update


@pytest.mark.unit
@pytest.mark.bootstrap
class TestCheckGitHubUpdates:
    """Tests for check_github_updates function."""

    def test_check_github_no_update(self, monkeypatch):
        """Test when current version is up to date."""

        class MockResponse:
            def read(self):
                return json.dumps([{"name": "v1.0.0"}]).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.urllib.request.urlopen",
            lambda req, timeout: MockResponse(),
        )

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False
        assert update_info.current_version == "1.0.0"
        assert update_info.latest_version == "1.0.0"

    def test_check_github_has_update(self, monkeypatch):
        """Test when newer version is available."""

        class MockResponse:
            def read(self):
                return json.dumps([{"name": "v1.1.0"}]).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.urllib.request.urlopen",
            lambda req, timeout: MockResponse(),
        )

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is True
        assert update_info.current_version == "1.0.0"
        assert update_info.latest_version == "1.1.0"
        assert update_info.source == "github"

    def test_check_github_network_error(self, monkeypatch):
        """Test handling of network errors."""

        def mock_urlopen(*args, **kwargs):
            raise urllib.error.URLError("Network error")

        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.urllib.request.urlopen", mock_urlopen
        )
        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False

    def test_check_github_no_tags(self, monkeypatch):
        """Test when repository has no tags."""

        class MockResponse:
            def read(self):
                return json.dumps([]).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.urllib.request.urlopen",
            lambda req, timeout: MockResponse(),
        )

        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False

    def test_check_github_handles_missing_name_key(self, monkeypatch):
        """Test handling of malformed GitHub response."""

        class MockResponse:
            def read(self):
                return json.dumps([{"commit": "abc123"}]).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.urllib.request.urlopen",
            lambda req, timeout: MockResponse(),
        )
        update_info = check_github_updates("owner/repo", "1.0.0")
        assert update_info.has_update is False

    def test_check_github_handles_json_decode_error(self, monkeypatch):
        """Test handling of invalid JSON response."""

        class MockResponse:
            def read(self):
                return b"invalid json"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(
            "shell_configs.bootstrap.updater.urllib.request.urlopen",
            lambda req, timeout: MockResponse(),
        )
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
