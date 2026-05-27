"""Tests for CursorShell WSL-specific path handling."""

from pathlib import Path

import pytest

from shell_configs.platform import Platform
from shell_configs.shells.cursor import CursorShell


@pytest.mark.unit
class TestCursorWSLPaths:
    """Test Cursor WSL-specific path handling."""

    def test_cursor_wsl_path_with_username(self, monkeypatch):
        """Test that CursorShell returns correct WSL path."""
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_appdata_roaming",
            lambda: Path("/mnt/c/Users/testuser/AppData/Roaming"),
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
            "shell_configs.shells.cursor.get_windows_appdata_roaming",
            lambda: None,
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


@pytest.mark.unit
class TestCursorWSLRemoteCli:
    def test_finds_remote_cli_on_wsl(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.cursor.Path.home", lambda: tmp_path)
        hash_dir = tmp_path / ".cursor-server" / "bin" / "abc123" / "bin" / "remote-cli"
        hash_dir.mkdir(parents=True)
        cli = hash_dir / "cursor"
        cli.write_text("#!/bin/sh")
        shell = CursorShell()
        result = shell.get_extension_cli()
        assert result == str(cli)

    def test_returns_none_when_no_server_on_wsl(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.cursor.Path.home", lambda: tmp_path)
        shell = CursorShell()
        result = shell.get_extension_cli()
        assert result is None

    def test_selects_newest_hash_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.cursor.Path.home", lambda: tmp_path)

        old_hash = tmp_path / ".cursor-server" / "bin" / "old_hash"
        old_cli = old_hash / "bin" / "remote-cli" / "cursor"
        old_cli.parent.mkdir(parents=True)
        old_cli.write_text("#!/bin/sh")

        new_hash = tmp_path / ".cursor-server" / "bin" / "new_hash"
        new_cli = new_hash / "bin" / "remote-cli" / "cursor"
        new_cli.parent.mkdir(parents=True)
        new_cli.write_text("#!/bin/sh")

        import os
        import time

        os.utime(old_hash, (time.time() - 100, time.time() - 100))

        shell = CursorShell()
        result = shell.get_extension_cli()
        assert result == str(new_cli)

    def test_falls_back_when_not_wsl(self, monkeypatch):
        monkeypatch.setattr("shell_configs.shells.cursor.is_platform", lambda p: False)
        shell = CursorShell()
        result = shell.get_extension_cli()
        assert result == "cursor"


@pytest.mark.unit
class TestCursorExtensionsJsonPath:
    def test_returns_path_on_wsl_when_file_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.cursor.Path.home", lambda: tmp_path)
        ext_json = tmp_path / ".cursor-server" / "extensions" / "extensions.json"
        ext_json.parent.mkdir(parents=True)
        ext_json.write_text("[]")
        shell = CursorShell()
        result = shell.get_extensions_json_path()
        assert result == ext_json

    def test_returns_none_on_wsl_when_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.cursor.Path.home", lambda: tmp_path)
        shell = CursorShell()
        result = shell.get_extensions_json_path()
        assert result is None

    def test_returns_none_on_non_wsl(self, monkeypatch):
        monkeypatch.setattr("shell_configs.shells.cursor.is_platform", lambda p: False)
        shell = CursorShell()
        result = shell.get_extensions_json_path()
        assert result is None
