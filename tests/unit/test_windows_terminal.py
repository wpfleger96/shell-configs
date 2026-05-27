"""Tests for Windows Terminal shell."""

from pathlib import Path

import pytest

from shell_configs.platform import Platform
from shell_configs.shells.windows_terminal import WindowsTerminalShell


@pytest.mark.unit
class TestWindowsTerminalShell:
    def test_name(self):
        shell = WindowsTerminalShell()
        assert shell.name == "windows-terminal"

    def test_display_name(self):
        shell = WindowsTerminalShell()
        assert shell.display_name == "Windows Terminal"

    def test_returns_no_config_files(self):
        shell = WindowsTerminalShell()
        assert shell.get_config_files() == []

    def test_returns_no_extension_cli(self):
        shell = WindowsTerminalShell()
        assert shell.get_extension_cli() is None

    def test_returns_no_extension_invoker(self):
        shell = WindowsTerminalShell()
        assert shell.get_extension_invoker() is None

    def test_additional_files_on_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.windows_terminal.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.windows_terminal.get_windows_appdata_local",
            lambda: Path("/mnt/c/Users/testuser/AppData/Local"),
        )
        monkeypatch.setattr(
            "shell_configs.shells.windows_terminal.get_config_dir",
            lambda: Path("/fake/config"),
        )
        shell = WindowsTerminalShell()
        files = shell.get_additional_files()
        assert len(files) == 1
        assert files[0].name == "settings.json"
        assert files[0].source_path == Path(
            "/fake/config/windows-terminal/settings.json"
        )
        expected_target = Path(
            "/mnt/c/Users/testuser/AppData/Local/Packages"
            "/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json"
        )
        assert files[0].target_path == expected_target

    def test_additional_files_empty_on_non_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.windows_terminal.is_platform",
            lambda p: p == Platform.LINUX,
        )
        shell = WindowsTerminalShell()
        assert shell.get_additional_files() == []

    def test_additional_files_empty_when_no_username(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.windows_terminal.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.windows_terminal.get_windows_appdata_local",
            lambda: None,
        )
        shell = WindowsTerminalShell()
        assert shell.get_additional_files() == []


@pytest.mark.unit
class TestRegistryWindowsTerminalWSLConditional:
    def test_registered_on_wsl(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.WSL,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("windows-terminal") is not None
        assert isinstance(registry.get("windows-terminal"), WindowsTerminalShell)

    def test_not_registered_on_linux(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("windows-terminal") is None
