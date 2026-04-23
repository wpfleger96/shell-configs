"""Tests for tool installation utilities."""

import subprocess
import sys

import pytest

from shell_configs.bootstrap.installer import (
    UV_NOT_FOUND_ERROR,
    ToolSource,
    get_tool_config_dir,
    get_tool_source,
    install_tool,
    uninstall_tool,
)


@pytest.mark.unit
@pytest.mark.bootstrap
class TestInstallTool:
    """Tests for install_tool function."""

    def test_install_without_uv_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: False
        )
        success, message = install_tool()
        assert success is False
        assert message == UV_NOT_FOUND_ERROR

    def test_install_pypi_package(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: True
        )

        captured_args = []

        def mock_run(*args, **kwargs):
            captured_args.append((args, kwargs))

            class Result:
                returncode = 0
                stderr = ""
                stdout = ""

            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)
        success, message = install_tool()
        assert success is True
        assert message == "Installation successful"
        assert len(captured_args) == 1
        call_args = captured_args[0][0][0]
        assert "uv" in call_args
        assert "tool" in call_args
        assert "install" in call_args
        assert "git+ssh://git@github.com/wpfleger96/shell-configs.git" in call_args

    def test_install_with_force_flag(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: True
        )

        captured_args = []

        def mock_run(*args, **kwargs):
            captured_args.append((args, kwargs))

            class Result:
                returncode = 0
                stderr = ""
                stdout = ""

            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)
        success, message = install_tool(force=True)
        assert success is True
        assert len(captured_args) == 1
        call_args = captured_args[0][0][0]
        assert "--force" in call_args

    def test_install_dry_run(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: True
        )
        success, message = install_tool(dry_run=True)
        assert success is True
        assert "Would run:" in message

    @pytest.mark.parametrize(
        "error_type,expected_message",
        [
            ("timeout", "timed out"),
            ("command_failure", "package not found"),
            ("empty_error", "failed"),
            ("unexpected", "unexpected error"),
        ],
    )
    def test_install_handles_errors(self, monkeypatch, error_type, expected_message):
        """Test that install handles various error conditions gracefully."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: True
        )

        def mock_run(*args, **kwargs):
            if error_type == "timeout":
                raise subprocess.TimeoutExpired("uv", 60)
            elif error_type == "command_failure":

                class CommandFailureResult:
                    returncode = 1
                    stderr = "Installation failed: package not found"
                    stdout = ""

                return CommandFailureResult()
            elif error_type == "empty_error":

                class EmptyErrorResult:
                    returncode = 1
                    stderr = ""
                    stdout = ""

                return EmptyErrorResult()
            elif error_type == "unexpected":
                raise ValueError("Unexpected error")

        monkeypatch.setattr("subprocess.run", mock_run)
        success, message = install_tool()
        assert success is False
        assert expected_message in message.lower()


@pytest.mark.unit
@pytest.mark.bootstrap
class TestUninstallTool:
    """Tests for uninstall_tool function."""

    def test_uninstall_without_uv_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: False
        )
        success, message = uninstall_tool()
        assert success is False
        assert message == UV_NOT_FOUND_ERROR

    def test_uninstall_package(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: True
        )

        captured_args = []

        def mock_run(*args, **kwargs):
            captured_args.append((args, kwargs))

            class Result:
                returncode = 0
                stderr = ""
                stdout = ""

            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)
        success, message = uninstall_tool()
        assert success is True
        assert message == "Uninstallation successful"
        assert len(captured_args) == 1
        call_args = captured_args[0][0][0]
        assert "uv" in call_args
        assert "tool" in call_args
        assert "uninstall" in call_args
        assert "shell-configs" in call_args

    @pytest.mark.parametrize(
        "error_type,expected_message",
        [
            ("timeout", "timed out"),
            ("command_failure", "package not installed"),
            ("empty_error", "failed"),
            ("unexpected", "unexpected error"),
        ],
    )
    def test_uninstall_handles_errors(self, monkeypatch, error_type, expected_message):
        """Test that uninstall handles various error conditions gracefully."""
        monkeypatch.setattr(
            "shell_configs.bootstrap.installer.is_command_available", lambda cmd: True
        )

        def mock_run(*args, **kwargs):
            if error_type == "timeout":
                raise subprocess.TimeoutExpired("uv", 30)
            elif error_type == "command_failure":

                class CommandFailureResult:
                    returncode = 1
                    stderr = "Package not installed"
                    stdout = ""

                return CommandFailureResult()
            elif error_type == "empty_error":

                class EmptyErrorResult:
                    returncode = 1
                    stderr = ""
                    stdout = ""

                return EmptyErrorResult()
            elif error_type == "unexpected":
                raise ValueError("Unexpected error")

        monkeypatch.setattr("subprocess.run", mock_run)
        success, message = uninstall_tool()
        assert success is False
        assert expected_message in message.lower()


@pytest.mark.unit
@pytest.mark.bootstrap
class TestGetToolConfigDir:
    """Tests for get_tool_config_dir function."""

    def test_returns_expected_path_structure(self):
        """Test that get_tool_config_dir returns correct path structure."""
        result = get_tool_config_dir("shell-configs")
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"

        path_str = str(result)
        assert "uv/tools/shell-configs" in path_str
        assert python_version in path_str
        assert path_str.endswith("shell_configs/config")

    def test_respects_xdg_data_home(self, monkeypatch, tmp_path):
        """Test that XDG_DATA_HOME environment variable is respected."""
        custom_data_home = tmp_path / "custom_data"
        monkeypatch.setenv("XDG_DATA_HOME", str(custom_data_home))

        result = get_tool_config_dir("shell-configs")

        assert str(result).startswith(str(custom_data_home))
        assert "uv/tools/shell-configs" in str(result)

    def test_uses_default_data_home_when_xdg_not_set(self, monkeypatch):
        """Test that ~/.local/share is used when XDG_DATA_HOME is not set."""
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        result = get_tool_config_dir("shell-configs")

        path_str = str(result)
        assert ".local/share" in path_str or ".local\\share" in path_str

    def test_custom_package_name(self):
        """Test that custom package names are handled correctly."""
        result = get_tool_config_dir("my-custom-package")

        assert "my-custom-package" in str(result)
        assert "shell_configs/config" in str(result)


@pytest.mark.unit
@pytest.mark.bootstrap
class TestGetToolSource:
    """Tests for get_tool_source function."""

    def test_detects_local_installation(self, tmp_path, monkeypatch):
        """Test that local file installations are detected."""
        tools_dir = tmp_path / "uv" / "tools" / "test-package"
        tools_dir.mkdir(parents=True)
        receipt = tools_dir / "uv-receipt.toml"
        receipt.write_text(
            '[tool]\nrequirements = [{ name = "test-package", path = "/path/to/local.whl" }]\n'
        )

        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        result = get_tool_source("test-package")
        assert result == ToolSource.LOCAL

    def test_detects_github_installation(self, tmp_path, monkeypatch):
        """Test that GitHub installations are detected."""
        tools_dir = tmp_path / "uv" / "tools" / "test-package"
        tools_dir.mkdir(parents=True)
        receipt = tools_dir / "uv-receipt.toml"
        receipt.write_text(
            '[tool]\nrequirements = [{ name = "test-package", git = "https://github.com/user/repo" }]\n'
        )

        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        result = get_tool_source("test-package")
        assert result == ToolSource.GITHUB

    def test_detects_pypi_installation(self, tmp_path, monkeypatch):
        """Test that PyPI installations are detected."""
        tools_dir = tmp_path / "uv" / "tools" / "test-package"
        tools_dir.mkdir(parents=True)
        receipt = tools_dir / "uv-receipt.toml"
        receipt.write_text(
            '[tool]\nrequirements = [{ name = "test-package", version = "1.0.0" }]\n'
        )

        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        result = get_tool_source("test-package")
        assert result == ToolSource.PYPI

    def test_returns_none_when_not_installed(self, tmp_path, monkeypatch):
        """Test that None is returned for tools that aren't installed."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        result = get_tool_source("nonexistent-package")
        assert result is None
