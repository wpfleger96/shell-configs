"""Tests for VSCodeShell WSL-specific path handling."""

from pathlib import Path

import pytest

from shell_configs.platform import Platform
from shell_configs.shells.vscode import VSCodeShell


class TestVSCodeWSLPaths:
    """Test VS Code WSL-specific path handling."""

    def test_vscode_wsl_path_with_username(self, monkeypatch):
        """Test that VSCodeShell returns correct WSL path."""
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_windows_appdata_roaming",
            lambda: Path("/mnt/c/Users/testuser/AppData/Roaming"),
        )

        shell = VSCodeShell()
        vscode_dir = shell._get_vscode_user_dir()

        assert vscode_dir == Path("/mnt/c/Users/testuser/AppData/Roaming/Code/User")

    def test_vscode_wsl_path_no_username(self, monkeypatch):
        """Test that VSCodeShell returns None when username unavailable."""
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_windows_appdata_roaming",
            lambda: None,
        )

        shell = VSCodeShell()
        vscode_dir = shell._get_vscode_user_dir()

        assert vscode_dir is None

    def test_vscode_linux_path(self, monkeypatch, mock_home):
        """Test that VSCodeShell returns correct Linux path."""
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.LINUX,
        )

        shell = VSCodeShell()
        vscode_dir = shell._get_vscode_user_dir()

        assert vscode_dir == mock_home / ".config" / "Code" / "User"

    def test_vscode_macos_path(self, monkeypatch, mock_home):
        """Test that VSCodeShell returns correct macOS path."""
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.MACOS,
        )

        shell = VSCodeShell()
        vscode_dir = shell._get_vscode_user_dir()

        assert (
            vscode_dir
            == mock_home / "Library" / "Application Support" / "Code" / "User"
        )


@pytest.mark.unit
class TestVSCodeExtensionsJsonPath:
    def test_returns_path_on_wsl_when_file_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.vscode.Path.home", lambda: tmp_path)
        ext_json = tmp_path / ".vscode-server" / "extensions" / "extensions.json"
        ext_json.parent.mkdir(parents=True)
        ext_json.write_text("[]")
        shell = VSCodeShell()
        result = shell.get_extensions_json_path()
        assert result == ext_json

    def test_returns_none_on_wsl_when_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.vscode.Path.home", lambda: tmp_path)
        shell = VSCodeShell()
        result = shell.get_extensions_json_path()
        assert result is None

    def test_returns_none_on_non_wsl(self, monkeypatch):
        monkeypatch.setattr("shell_configs.shells.vscode.is_platform", lambda p: False)
        shell = VSCodeShell()
        result = shell.get_extensions_json_path()
        assert result is None
