"""Integration tests for the `configs` command group.

Covers the scoped `configs install`/`status` path, which drives only the
ConfigsComponent (no package/gh/network components).
"""

import pytest

from shell_configs.cli import cli


@pytest.mark.integration
@pytest.mark.cli
class TestConfigsInstall:
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
