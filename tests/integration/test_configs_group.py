"""Integration tests for the `configs` command group.

Mirrors TestInstallCommand in test_cli.py but for the scoped `configs install`/
`status` path, which drives only the ConfigsComponent (no package/gh/network
components).
"""

import pytest

from shell_configs.cli import cli
from shell_configs.manager import ConfigManager


@pytest.mark.integration
@pytest.mark.cli
class TestConfigsInstall:
    def test_install_writes_managed_sections(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["configs", "install", "-y"])
        assert result.exit_code == 0

        manager = ConfigManager()
        assert manager.has_managed_section(mock_home / ".bashrc")
        assert manager.has_managed_section(mock_home / ".zshrc")
        assert manager.has_managed_section(mock_home / ".gitconfig")

    def test_install_shell_filter(self, test_repo, mock_home, cli_runner, monkeypatch):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(
            cli, ["configs", "install", "--shells", "bash,zsh", "-y"]
        )
        assert result.exit_code == 0

        manager = ConfigManager()
        assert manager.has_managed_section(mock_home / ".bashrc")
        assert manager.has_managed_section(mock_home / ".zshrc")
        assert not manager.has_managed_section(mock_home / ".gitconfig")

    def test_install_dry_run_writes_nothing(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["configs", "install", "--dry-run", "-y"])
        assert result.exit_code == 0
        assert not (mock_home / ".bashrc").exists()

    def test_install_idempotent(self, test_repo, mock_home, cli_runner, monkeypatch):
        monkeypatch.chdir(test_repo)

        first = cli_runner.invoke(cli, ["configs", "install", "-y"])
        assert first.exit_code == 0
        second = cli_runner.invoke(cli, ["configs", "install", "-y"])
        assert second.exit_code == 0
        assert "already in sync" in second.output.lower()


@pytest.mark.integration
@pytest.mark.cli
class TestConfigsStatus:
    def test_status_reflects_install(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        before = cli_runner.invoke(cli, ["configs", "status"])
        assert before.exit_code == 0
        assert "Not installed" in before.output

        cli_runner.invoke(cli, ["configs", "install", "-y"])

        after = cli_runner.invoke(cli, ["configs", "status"])
        assert after.exit_code == 0
        assert "Synced" in after.output
