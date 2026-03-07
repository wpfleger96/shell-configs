"""Tests for VSCodeShell WSL-specific path handling."""

from pathlib import Path

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
            "shell_configs.shells.vscode.get_windows_username",
            lambda: "testuser",
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
            "shell_configs.shells.vscode.get_windows_username",
            lambda: "",
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
