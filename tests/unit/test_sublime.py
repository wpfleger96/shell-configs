"""Tests for Sublime Text shell."""

from pathlib import Path

import pytest

from shell_configs.platform import Platform
from shell_configs.shells.sublime import SublimeShell


@pytest.mark.unit
class TestSublimeShell:
    def test_name(self):
        shell = SublimeShell()
        assert shell.name == "sublime"

    def test_display_name(self):
        shell = SublimeShell()
        assert shell.display_name == "Sublime Text"

    def test_returns_no_config_files(self):
        shell = SublimeShell()
        assert shell.get_config_files() == []

    def test_returns_no_extension_cli(self):
        shell = SublimeShell()
        assert shell.get_extension_cli() is None

    def test_returns_no_extension_invoker(self):
        shell = SublimeShell()
        assert shell.get_extension_invoker() is None

    def test_additional_files_on_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.sublime.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.sublime.get_windows_username",
            lambda: "testuser",
        )
        monkeypatch.setattr(
            "shell_configs.shells.sublime.get_config_dir",
            lambda: Path("/fake/config"),
        )
        shell = SublimeShell()
        files = shell.get_additional_files()
        assert len(files) == 1
        assert files[0].name == "Preferences.sublime-settings"
        assert files[0].source_path == Path("/fake/config/sublime/settings.json")
        expected_target = Path(
            "/mnt/c/Users/testuser/AppData/Roaming/Sublime Text/Packages/User"
            "/Preferences.sublime-settings"
        )
        assert files[0].target_path == expected_target

    def test_additional_files_on_macos(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.shells.sublime.is_platform",
            lambda p: p == Platform.MACOS,
        )
        monkeypatch.setattr(
            "shell_configs.shells.sublime.get_config_dir",
            lambda: Path("/fake/config"),
        )
        shell = SublimeShell()
        files = shell.get_additional_files()
        assert len(files) == 1
        assert files[0].name == "Preferences.sublime-settings"
        expected_target = (
            mock_home
            / "Library"
            / "Application Support"
            / "Sublime Text"
            / "Packages"
            / "User"
            / "Preferences.sublime-settings"
        )
        assert files[0].target_path == expected_target

    def test_additional_files_on_linux(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.shells.sublime.is_platform",
            lambda p: p == Platform.LINUX,
        )
        monkeypatch.setattr(
            "shell_configs.shells.sublime.get_config_dir",
            lambda: Path("/fake/config"),
        )
        shell = SublimeShell()
        files = shell.get_additional_files()
        assert len(files) == 1
        assert files[0].name == "Preferences.sublime-settings"
        expected_target = (
            mock_home
            / ".config"
            / "sublime-text"
            / "Packages"
            / "User"
            / "Preferences.sublime-settings"
        )
        assert files[0].target_path == expected_target

    def test_additional_files_empty_when_no_username_on_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.sublime.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.sublime.get_windows_username",
            lambda: "",
        )
        shell = SublimeShell()
        assert shell.get_additional_files() == []


@pytest.mark.unit
class TestRegistrySublimeUnconditional:
    def test_registered_on_wsl(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.WSL,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("sublime") is not None
        assert isinstance(registry.get("sublime"), SublimeShell)

    def test_registered_on_linux(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("sublime") is not None
        assert isinstance(registry.get("sublime"), SublimeShell)

    def test_registered_on_macos(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.MACOS,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("sublime") is not None
        assert isinstance(registry.get("sublime"), SublimeShell)
