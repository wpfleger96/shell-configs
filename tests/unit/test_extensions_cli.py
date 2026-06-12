"""Tests for extension CLI commands."""

from pathlib import Path

import pytest

from click.testing import CliRunner

from shell_configs.cli import cli


@pytest.fixture
def extension_config_dir(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Config dir with a stale builtin VS Code extension entry."""
    config_dir = temp_dir / "config"
    (config_dir / "editor").mkdir(parents=True)
    (config_dir / "vscode").mkdir(parents=True)
    (config_dir / "editor" / "extensions.txt").write_text("")
    (config_dir / "vscode" / "extensions.txt").write_text("github.copilot-chat\n")

    monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr(
        "shell_configs.shells.editor.get_config_dir", lambda: config_dir
    )
    monkeypatch.setattr(
        "shell_configs.shells.editor.get_config_dir", lambda: config_dir
    )

    return config_dir


@pytest.mark.unit
@pytest.mark.cli
class TestExtensionsCLI:
    """Tests for builtin extension warnings in CLI commands."""

    def test_status_warns_for_builtin_entries(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: set(),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "status", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "built-ins ignored" in result.output
        assert "github.copilot-chat" in result.output

    def test_status_warns_for_builtin_entries_when_out_of_sync(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        (extension_config_dir / "editor" / "extensions.txt").write_text("golang.go\n")
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: set(),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "status", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "out of sync" in result.output
        assert "github.copilot-chat" in result.output

    def test_diff_warns_for_builtin_entries(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: set(),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "diff", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "Ignored built-ins in config" in result.output
        assert "github.copilot-chat" in result.output

    def test_install_dry_run_warns_without_installing_builtin_entries(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: set(),
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["extensions", "install", "--shells", "vscode", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "Ignoring built-in extensions from config" in result.output
        assert "github.copilot-chat" in result.output
        assert "Would install" not in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestExtensionsListCLI:
    """Tests for extensions list command."""

    def test_list_shows_installed_extensions(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        (extension_config_dir / "editor" / "extensions.txt").write_text("golang.go\n")
        (extension_config_dir / "vscode" / "extensions.txt").write_text("")
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: {"golang.go"},
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "list", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "golang.go" in result.output
        assert "installed" in result.output

    def test_list_shows_missing_extensions(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        (extension_config_dir / "editor" / "extensions.txt").write_text("golang.go\n")
        (extension_config_dir / "vscode" / "extensions.txt").write_text("")
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: set(),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "list", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "golang.go" in result.output
        assert "missing" in result.output

    def test_list_shows_extra_extensions(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        (extension_config_dir / "editor" / "extensions.txt").write_text("golang.go\n")
        (extension_config_dir / "vscode" / "extensions.txt").write_text("")
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: {"golang.go", "some.extra"},
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "list", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "some.extra" in result.output
        assert "extra" in result.output

    def test_list_shows_builtin_as_builtin(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: set(),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "list", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "github.copilot-chat" in result.output
        assert "builtin" in result.output

    def test_list_no_data_available(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: None,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "list", "--shells", "vscode"])

        assert result.exit_code == 0
        assert "No extension data available" in result.output

    def test_list_no_ide_shells_found(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        # bash has no extension CLI/invoker, so the filtered IDE list is empty
        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "list", "--shells", "bash"])

        assert result.exit_code == 0
        assert "No IDEs with extension management found" in result.output

    def test_list_multiple_ides_shows_table_per_ide(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        (extension_config_dir / "editor" / "extensions.txt").write_text("golang.go\n")
        (extension_config_dir / "vscode" / "extensions.txt").write_text("")
        (extension_config_dir / "cursor").mkdir(exist_ok=True)
        (extension_config_dir / "cursor" / "extensions.txt").write_text("")
        monkeypatch.setattr(
            "shell_configs.shells.editor.get_config_dir", lambda: extension_config_dir
        )
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: {"golang.go"},
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["extensions", "list", "--shells", "vscode,cursor"])

        assert result.exit_code == 0
        # Both IDE tables should appear in output
        assert "VS Code" in result.output
        assert "Cursor" in result.output
        assert "golang.go" in result.output

    def test_list_profile_adds_extensions(
        self,
        extension_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_home: Path,
    ) -> None:
        import yaml

        (extension_config_dir / "editor" / "extensions.txt").write_text("")
        (extension_config_dir / "vscode" / "extensions.txt").write_text("")
        profiles_dir = extension_config_dir / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        (profiles_dir / "work.yaml").write_text(
            yaml.dump(
                {
                    "name": "work",
                    "extensions": {"vscode": {"add": ["ms-vscode.powershell"]}},
                }
            )
        )
        monkeypatch.setattr(
            "shell_configs.extensions.ExtensionManager.get_installed_extensions",
            lambda self, cli_command=None, **kwargs: set(),
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["extensions", "list", "--shells", "vscode", "--profile", "work"]
        )

        assert result.exit_code == 0
        assert "ms-vscode.powershell" in result.output
        assert "missing" in result.output
