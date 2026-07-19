"""Tests for auto-update configuration management."""

import pytest

from shell_configs.bootstrap.config import (
    AutoUpdateConfig,
    get_config_dir,
    get_config_path,
    load_auto_update_config,
    save_auto_update_config,
)


@pytest.mark.unit
@pytest.mark.bootstrap
class TestGetConfigDir:
    """Tests for get_config_dir function."""

    def test_returns_home_config_dir(self, mock_home):
        """Test that config dir is under ~/.package_name/."""
        config_dir = get_config_dir("test-package")
        assert config_dir == mock_home / ".test-package"

    def test_default_package_name(self, mock_home):
        """Test default package name."""
        config_dir = get_config_dir()
        assert config_dir == mock_home / ".shell-configs"


@pytest.mark.unit
@pytest.mark.bootstrap
class TestGetConfigPath:
    """Tests for get_config_path function."""

    def test_returns_config_yaml_path(self, mock_home):
        """Test that config path points to update_config.yaml."""
        config_path = get_config_path("test-package")
        assert config_path.name == "update_config.yaml"
        assert config_path.parent == mock_home / ".test-package"


@pytest.mark.unit
@pytest.mark.bootstrap
class TestLoadAutoUpdateConfig:
    """Tests for load_auto_update_config function."""

    def test_load_valid_config(self, mock_home, monkeypatch):
        """Test loading valid configuration file."""
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 10\n")

        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        config = load_auto_update_config()
        assert config.backup_retention == 10

    def test_load_missing_config_returns_defaults(self, mock_home, monkeypatch):
        """Test that missing config returns default values."""
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )

        config = load_auto_update_config()
        assert config.backup_retention == 5

    @pytest.mark.parametrize(
        "error_type",
        ["invalid_yaml", "os_error"],
    )
    def test_load_errors_return_defaults(self, mock_home, monkeypatch, error_type):
        """Test that errors during loading return default config."""
        config_file = mock_home / ".shell-configs" / "update_config.yaml"

        if error_type == "invalid_yaml":
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text("invalid: yaml: content:")
        elif error_type == "os_error":

            def mock_open_error(*args, **kwargs):
                raise OSError("Permission denied")

            monkeypatch.setattr("builtins.open", mock_open_error)

        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )

        config = load_auto_update_config()
        assert config.backup_retention == 5


@pytest.mark.unit
@pytest.mark.bootstrap
class TestSaveAutoUpdateConfig:
    """Tests for save_auto_update_config function."""

    def test_save_config_writes_yaml(self, mock_home, monkeypatch):
        """Test that config is saved as YAML."""
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )

        config = AutoUpdateConfig(backup_retention=10)
        save_auto_update_config(config)

        assert config_file.exists()
        import yaml

        with open(config_file, encoding="utf-8") as f:
            saved_data = yaml.safe_load(f)
        assert saved_data["backup_retention"] == 10

    def test_active_profile_round_trips(self, mock_home, monkeypatch):
        """AutoUpdateConfig saves and loads active_profile correctly."""
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )

        config = AutoUpdateConfig(backup_retention=5, active_profile="work")
        save_auto_update_config(config)

        loaded = load_auto_update_config()
        assert loaded.active_profile == "work"
        assert loaded.backup_retention == 5

    def test_missing_active_profile_field_defaults_to_none(
        self, mock_home, monkeypatch
    ):
        """Old configs without active_profile field load with None default."""
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 7\n")

        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )

        loaded = load_auto_update_config()
        assert loaded.active_profile is None
        assert loaded.backup_retention == 7
