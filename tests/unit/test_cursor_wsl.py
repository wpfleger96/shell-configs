"""Tests for CursorShell WSL-specific path handling."""

from pathlib import Path

from shell_configs.platform import Platform
from shell_configs.shells.cursor import CursorShell


class TestCursorWSLPaths:
    """Test Cursor WSL-specific path handling."""

    def test_cursor_wsl_path_with_username(self, monkeypatch):
        """Test that CursorShell returns correct WSL path."""
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_username",
            lambda: "testuser",
        )

        shell = CursorShell()
        cursor_dir = shell._get_cursor_user_dir()

        assert cursor_dir == Path("/mnt/c/Users/testuser/AppData/Roaming/Cursor/User")

    def test_cursor_wsl_path_no_username(self, monkeypatch):
        """Test that CursorShell returns None when username unavailable."""
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_username",
            lambda: "",
        )

        shell = CursorShell()
        cursor_dir = shell._get_cursor_user_dir()

        assert cursor_dir is None

    def test_cursor_linux_path(self, monkeypatch, mock_home):
        """Test that CursorShell returns correct Linux path."""
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.LINUX,
        )

        shell = CursorShell()
        cursor_dir = shell._get_cursor_user_dir()

        assert cursor_dir == mock_home / ".config" / "Cursor" / "User"

    def test_cursor_macos_path(self, monkeypatch, mock_home):
        """Test that CursorShell returns correct macOS path."""
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.MACOS,
        )

        shell = CursorShell()
        cursor_dir = shell._get_cursor_user_dir()

        assert (
            cursor_dir
            == mock_home / "Library" / "Application Support" / "Cursor" / "User"
        )
