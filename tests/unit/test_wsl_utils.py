"""Tests for WSL path resolution utilities in utils.py."""

import configparser
import logging

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from shell_configs.shells.utils import (
    get_windows_appdata_local,
    get_windows_appdata_roaming,
    get_windows_home,
    get_windows_programs,
    get_windows_username,
    get_wsl_windows_drive,
)


@pytest.fixture(autouse=True)
def clear_caches():
    yield
    get_wsl_windows_drive.cache_clear()
    get_windows_username.cache_clear()


@pytest.mark.unit
class TestGetWslWindowsDrive:
    def test_returns_default_mount_when_no_wsl_conf(self):
        result = get_wsl_windows_drive()
        assert result == Path("/mnt/c")

    def test_reads_custom_root_from_wsl_conf(self, monkeypatch, tmp_path):
        conf = tmp_path / "wsl.conf"
        conf.write_text("[automount]\nroot = /winmnt/\n")
        original_read = configparser.ConfigParser.read

        def patched_read(self, filenames, **kwargs):
            return original_read(self, str(conf), **kwargs)

        monkeypatch.setattr(configparser.ConfigParser, "read", patched_read)
        get_wsl_windows_drive.cache_clear()
        result = get_wsl_windows_drive()
        assert result == Path("/winmnt/c")

    def test_appends_trailing_slash_to_root(self, monkeypatch, tmp_path):
        conf = tmp_path / "wsl.conf"
        conf.write_text("[automount]\nroot = /mnt\n")
        original_read = configparser.ConfigParser.read

        def patched_read(self, filenames, **kwargs):
            return original_read(self, str(conf), **kwargs)

        monkeypatch.setattr(configparser.ConfigParser, "read", patched_read)
        get_wsl_windows_drive.cache_clear()
        result = get_wsl_windows_drive()
        assert result == Path("/mnt/c")

    def test_handles_different_drive_letters(self):
        result = get_wsl_windows_drive(drive="d")
        assert result == Path("/mnt/d")


@pytest.mark.unit
class TestGetWindowsHome:
    def test_returns_home_path_when_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_username",
            lambda: "testuser",
        )
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_wsl_windows_drive",
            lambda: tmp_path,
        )
        home_dir = tmp_path / "Users" / "testuser"
        home_dir.mkdir(parents=True)
        result = get_windows_home()
        assert result == home_dir

    def test_returns_none_when_username_empty(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_username",
            lambda: "",
        )
        result = get_windows_home()
        assert result is None

    def test_returns_none_when_dir_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_username",
            lambda: "testuser",
        )
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_wsl_windows_drive",
            lambda: tmp_path,
        )
        result = get_windows_home()
        assert result is None


@pytest.mark.unit
class TestGetWindowsAppdataRoaming:
    def test_returns_path_when_exists(self, monkeypatch, tmp_path):
        appdata = tmp_path / "AppData" / "Roaming"
        appdata.mkdir(parents=True)
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_home",
            lambda: tmp_path,
        )
        result = get_windows_appdata_roaming()
        assert result == appdata

    def test_returns_none_when_home_missing(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_home",
            lambda: None,
        )
        result = get_windows_appdata_roaming()
        assert result is None


@pytest.mark.unit
class TestGetWindowsAppdataLocal:
    def test_returns_path_when_exists(self, monkeypatch, tmp_path):
        appdata = tmp_path / "AppData" / "Local"
        appdata.mkdir(parents=True)
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_home",
            lambda: tmp_path,
        )
        result = get_windows_appdata_local()
        assert result == appdata

    def test_returns_none_when_home_missing(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_home",
            lambda: None,
        )
        result = get_windows_appdata_local()
        assert result is None


@pytest.mark.unit
class TestGetWindowsPrograms:
    def test_returns_path_when_exists(self, monkeypatch, tmp_path):
        programs = tmp_path / "Programs"
        programs.mkdir(parents=True)
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_appdata_local",
            lambda: tmp_path,
        )
        result = get_windows_programs()
        assert result == programs

    def test_returns_none_when_local_missing(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.utils.get_windows_appdata_local",
            lambda: None,
        )
        result = get_windows_programs()
        assert result is None


@pytest.mark.unit
class TestGetWindowsUsername:
    def test_logs_warning_when_detection_fails(self, monkeypatch, caplog):
        monkeypatch.setattr(
            "shell_configs.shells.utils.subprocess.run",
            MagicMock(side_effect=Exception("no interop")),
        )
        get_windows_username.cache_clear()
        with caplog.at_level(logging.WARNING, logger="shell_configs.shells.utils"):
            result = get_windows_username()
        assert result == ""
        assert "Unable to detect Windows username" in caplog.text
