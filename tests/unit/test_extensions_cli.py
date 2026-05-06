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
        "shell_configs.shells.vscode.get_config_dir", lambda: config_dir
    )
    monkeypatch.setattr(
        "shell_configs.shells.cursor.get_config_dir", lambda: config_dir
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
            lambda self, cli_command: set(),
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
            lambda self, cli_command: set(),
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
            lambda self, cli_command: set(),
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
            lambda self, cli_command: set(),
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
