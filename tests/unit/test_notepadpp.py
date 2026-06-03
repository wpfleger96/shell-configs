"""Tests for Notepad++ shell."""

from pathlib import Path

import pytest

from shell_configs.platform import Platform
from shell_configs.shells.notepadpp import NotepadPPShell


@pytest.mark.unit
class TestNotepadPPShell:
    def test_name(self):
        shell = NotepadPPShell()
        assert shell.name == "notepadpp"

    def test_display_name(self):
        shell = NotepadPPShell()
        assert shell.display_name == "Notepad++"

    def test_returns_no_config_files(self):
        shell = NotepadPPShell()
        assert shell.get_config_files() == []

    def test_returns_no_extension_cli(self):
        shell = NotepadPPShell()
        assert shell.get_extension_cli() is None

    def test_returns_no_extension_invoker(self):
        shell = NotepadPPShell()
        assert shell.get_extension_invoker() is None

    def test_additional_files_on_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.notepadpp.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.notepadpp.get_windows_appdata_roaming",
            lambda: Path("/mnt/c/Users/testuser/AppData/Roaming"),
        )
        monkeypatch.setattr(
            "shell_configs.shells.notepadpp.get_config_dir",
            lambda: Path("/fake/config"),
        )
        shell = NotepadPPShell()
        files = shell.get_additional_files()
        assert len(files) == 1
        assert files[0].name == "config.xml"
        assert files[0].xml_guiconfig_merge is True
        assert files[0].source_path == Path("/fake/config/notepadpp/config.xml")
        expected_target = Path(
            "/mnt/c/Users/testuser/AppData/Roaming/Notepad++/config.xml"
        )
        assert files[0].target_path == expected_target

    def test_additional_files_empty_on_non_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.notepadpp.is_platform",
            lambda p: p == Platform.LINUX,
        )
        shell = NotepadPPShell()
        assert shell.get_additional_files() == []

    def test_additional_files_empty_when_no_appdata(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.notepadpp.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.notepadpp.get_windows_appdata_roaming",
            lambda: None,
        )
        shell = NotepadPPShell()
        assert shell.get_additional_files() == []


@pytest.mark.unit
class TestRegistryNotepadPPWSLConditional:
    def test_registered_on_wsl(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.WSL,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("notepadpp") is not None
        assert isinstance(registry.get("notepadpp"), NotepadPPShell)

    def test_not_registered_on_linux(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("notepadpp") is None
