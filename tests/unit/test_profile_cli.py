"""Tests for profile CLI commands."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from click.testing import CliRunner

from shell_configs.cli import cli


def _make_profiles(config_dir: Path, profiles: dict[str, Any]) -> None:
    profiles_dir = config_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    for name, data in profiles.items():
        (profiles_dir / f"{name}.yaml").write_text(yaml.dump(data))


@pytest.fixture
def profile_config_dir(temp_dir, monkeypatch):
    """Config dir with default/personal/work profiles."""
    config_dir = temp_dir / "config"
    config_dir.mkdir()
    _make_profiles(
        config_dir,
        {
            "default": {"name": "default", "description": "Default profile"},
            "personal": {
                "name": "personal",
                "description": "Personal laptop",
                "extends": "default",
            },
            "work": {
                "name": "work",
                "description": "Work laptop",
                "extends": "personal",
            },
        },
    )
    monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)
    return config_dir


@pytest.mark.unit
@pytest.mark.cli
class TestProfileList:
    """Tests for `profile list` command."""

    def test_shows_all_profiles(self, profile_config_dir, mock_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "list"])
        assert result.exit_code == 0
        assert "default" in result.output
        assert "personal" in result.output
        assert "work" in result.output

    def test_marks_active_profile(self, profile_config_dir, mock_home, monkeypatch):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 5\nactive_profile: work\n")
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "list"])
        assert result.exit_code == 0
        assert "*" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestProfileCurrent:
    """Tests for `profile current` command."""

    def test_shows_default_when_no_state(
        self, profile_config_dir, mock_home, monkeypatch
    ):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "current"])
        assert result.exit_code == 0
        assert "default" in result.output

    def test_shows_active_profile(self, profile_config_dir, mock_home, monkeypatch):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 5\nactive_profile: work\n")
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "current"])
        assert result.exit_code == 0
        assert "work" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestProfileSwitch:
    """Tests for `profile switch` command."""

    def test_switch_writes_to_auto_update_config(
        self, profile_config_dir, mock_home, monkeypatch
    ):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 5\n")
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "switch", "work"])
        assert result.exit_code == 0
        assert "work" in result.output

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["active_profile"] == "work"

    def test_switch_to_nonexistent_profile_fails(
        self, profile_config_dir, mock_home, monkeypatch
    ):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "switch", "nonexistent"])
        assert result.exit_code == 0
        assert "Error" in result.output

    def test_switch_prints_install_reminder(
        self, profile_config_dir, mock_home, monkeypatch
    ):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 5\n")
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "switch", "personal"])
        assert result.exit_code == 0
        assert "install" in result.output.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestValidateProfileChains:
    """Tests for validate catching broken profile inheritance chains."""

    def test_validate_reports_missing_parent(self, temp_dir, mock_home, monkeypatch):
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        _make_profiles(
            config_dir,
            {
                "orphan": {
                    "name": "orphan",
                    "description": "extends a nonexistent profile",
                    "extends": "nonexistent",
                },
            },
        )
        monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)
        runner = CliRunner()
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code != 0
        assert "orphan" in result.output or "nonexistent" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestProfileShow:
    """Tests for `profile show` command."""

    def test_show_raw_yaml(self, profile_config_dir, mock_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "show", "work"])
        assert result.exit_code == 0
        assert "work" in result.output

    def test_show_resolved_flag(self, profile_config_dir, mock_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "show", "work", "--resolved"])
        assert result.exit_code == 0
        assert "work" in result.output

    def test_show_default_without_file(self, temp_dir, mock_home, monkeypatch):
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "show", "default"])
        assert result.exit_code == 0
        assert "default" in result.output
