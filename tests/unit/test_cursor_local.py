"""Tests for Cursor Local (Windows-side) extension management on WSL."""

import pytest

from shell_configs.extensions import (
    ExtensionManager,
    PowerShellExtensionInvoker,
    get_builtin_extensions,
)
from shell_configs.platform import Platform
from shell_configs.shells.cursor import CursorLocalShell


@pytest.mark.unit
class TestCursorLocalShell:
    """Tests for CursorLocalShell class."""

    def test_name(self):
        shell = CursorLocalShell()
        assert shell.name == "cursor-local"

    def test_display_name(self):
        shell = CursorLocalShell()
        assert shell.display_name == "Cursor (Local)"

    def test_get_extension_cli_returns_none(self):
        shell = CursorLocalShell()
        assert shell.get_extension_cli() is None

    def test_returns_none_on_non_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.LINUX,
        )
        shell = CursorLocalShell()
        assert shell.get_extension_invoker() is None

    def test_returns_invoker_on_wsl(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_username",
            lambda: "testuser",
        )
        programs = tmp_path / "Programs"
        cursor_cmd = programs / "cursor" / "resources" / "app" / "bin" / "cursor.cmd"
        cursor_cmd.parent.mkdir(parents=True)
        cursor_cmd.touch()

        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_programs",
            lambda: programs,
        )

        shell = CursorLocalShell()
        invoker = shell.get_extension_invoker()
        assert isinstance(invoker, PowerShellExtensionInvoker)

    def test_returns_none_when_username_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_username",
            lambda: "",
        )
        shell = CursorLocalShell()
        assert shell.get_extension_invoker() is None

    def test_returns_invoker_on_wsl_with_underscore_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_username",
            lambda: "testuser",
        )
        programs = tmp_path / "Programs"
        cursor_cmd = (
            programs / "cursor" / "_" / "resources" / "app" / "bin" / "cursor.cmd"
        )
        cursor_cmd.parent.mkdir(parents=True)
        cursor_cmd.touch()

        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_programs",
            lambda: programs,
        )

        shell = CursorLocalShell()
        invoker = shell.get_extension_invoker()
        assert isinstance(invoker, PowerShellExtensionInvoker)

    def test_returns_none_when_cursor_cmd_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_windows_username",
            lambda: "testuser",
        )
        shell = CursorLocalShell()
        assert shell.get_extension_invoker() is None

    def test_extension_list_paths(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_config_dir", lambda: tmp_path
        )
        shell = CursorLocalShell()
        paths = shell.get_extension_list_paths()
        assert len(paths) == 1
        assert paths[0] == tmp_path / "cursor" / "extensions-local.txt"


@pytest.mark.unit
class TestRegistryCursorLocalWSLConditional:
    """Tests for conditional registration of CursorLocalShell."""

    def test_cursor_local_registered_on_wsl(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.WSL,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("cursor-local") is not None
        assert isinstance(registry.get("cursor-local"), CursorLocalShell)

    def test_cursor_local_not_registered_on_linux(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("cursor-local") is None


@pytest.mark.unit
class TestBuiltinExtensionsCursorLocal:
    """Tests for cursor-local builtin extension filtering."""

    def test_cursor_local_builtins(self):
        builtins = get_builtin_extensions("cursor-local")
        assert "anysphere.remote-wsl" in builtins
        assert "anysphere.cursorpyright" in builtins
        assert "ms-vscode-remote.remote-wsl" in builtins

    def test_compute_diff_ignores_builtin_extensions(self):
        manager = ExtensionManager()
        desired = {
            "ms-vscode.powershell",
            "anysphere.remote-wsl",
            "anysphere.cursorpyright",
        }
        installed = {
            "ms-vscode.powershell",
            "anysphere.remote-wsl",
            "anysphere.cursorpyright",
        }
        diff = manager.compute_diff(desired, installed, shell_name="cursor-local")
        assert "anysphere.remote-wsl" in diff.ignored
        assert "anysphere.cursorpyright" in diff.ignored
        assert not diff.missing
        assert not diff.extra
