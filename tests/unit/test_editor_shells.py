"""Tests for EditorShell platform path handling (VS Code + Cursor)."""

import os
import time

from pathlib import Path

import pytest

from shell_configs.platform import Platform
from shell_configs.shells.cursor import CursorShell
from shell_configs.shells.vscode import VSCodeShell

EDITORS = [
    pytest.param(VSCodeShell, "Code", ".vscode-server", id="vscode"),
    pytest.param(CursorShell, "Cursor", ".cursor-server", id="cursor"),
]


@pytest.mark.unit
@pytest.mark.parametrize(("shell_cls", "app_dir", "server_dir"), EDITORS)
class TestEditorUserDirPaths:
    """Platform-specific User directory resolution shared by both editors."""

    def test_wsl_path_with_username(self, monkeypatch, shell_cls, app_dir, server_dir):
        monkeypatch.setattr(
            "shell_configs.shells.editor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.editor.get_windows_appdata_roaming",
            lambda: Path("/mnt/c/Users/testuser/AppData/Roaming"),
        )

        user_dir = shell_cls()._get_user_dir()

        assert user_dir == Path(f"/mnt/c/Users/testuser/AppData/Roaming/{app_dir}/User")

    def test_wsl_path_no_username(self, monkeypatch, shell_cls, app_dir, server_dir):
        monkeypatch.setattr(
            "shell_configs.shells.editor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.editor.get_windows_appdata_roaming",
            lambda: None,
        )

        assert shell_cls()._get_user_dir() is None

    def test_linux_path(self, monkeypatch, mock_home, shell_cls, app_dir, server_dir):
        monkeypatch.setattr(
            "shell_configs.shells.editor.is_platform",
            lambda p: p == Platform.LINUX,
        )

        user_dir = shell_cls()._get_user_dir()

        assert user_dir == mock_home / ".config" / app_dir / "User"

    def test_macos_path(self, monkeypatch, mock_home, shell_cls, app_dir, server_dir):
        monkeypatch.setattr(
            "shell_configs.shells.editor.is_platform",
            lambda p: p == Platform.MACOS,
        )

        user_dir = shell_cls()._get_user_dir()

        assert (
            user_dir == mock_home / "Library" / "Application Support" / app_dir / "User"
        )


@pytest.mark.unit
@pytest.mark.parametrize(("shell_cls", "app_dir", "server_dir"), EDITORS)
class TestEditorExtensionsJsonPath:
    """WSL filesystem-fallback extensions.json discovery shared by both editors."""

    def test_returns_path_on_wsl_when_file_exists(
        self, monkeypatch, tmp_path, shell_cls, app_dir, server_dir
    ):
        monkeypatch.setattr(
            "shell_configs.shells.editor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.editor.Path.home", lambda: tmp_path)
        ext_json = tmp_path / server_dir / "extensions" / "extensions.json"
        ext_json.parent.mkdir(parents=True)
        ext_json.write_text("[]")

        assert shell_cls().get_extensions_json_path() == ext_json

    def test_returns_none_on_wsl_when_file_missing(
        self, monkeypatch, tmp_path, shell_cls, app_dir, server_dir
    ):
        monkeypatch.setattr(
            "shell_configs.shells.editor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr("shell_configs.shells.editor.Path.home", lambda: tmp_path)

        assert shell_cls().get_extensions_json_path() is None

    def test_returns_none_on_non_wsl(self, monkeypatch, shell_cls, app_dir, server_dir):
        monkeypatch.setattr("shell_configs.shells.editor.is_platform", lambda p: False)

        assert shell_cls().get_extensions_json_path() is None


@pytest.mark.unit
class TestCursorWSLRemoteCli:
    """Cursor-specific WSL remote CLI discovery."""

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

        os.utime(old_hash, (time.time() - 100, time.time() - 100))

        shell = CursorShell()
        result = shell.get_extension_cli()
        assert result == str(new_cli)

    def test_falls_back_when_not_wsl(self, monkeypatch):
        monkeypatch.setattr("shell_configs.shells.cursor.is_platform", lambda p: False)
        shell = CursorShell()
        result = shell.get_extension_cli()
        assert result == "cursor"
