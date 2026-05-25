"""Tests for AI coding agent management."""

from __future__ import annotations

import subprocess

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shell_configs.agents import (
    Agent,
    AgentInstallConfig,
    get_agent_version,
    install_agent,
    is_agent_installed,
    load_agents,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(
    name: str = "claude-code",
    command: str = "claude",
    description: str = "Claude Code",
    check_path: str | None = None,
    install_cmd: str | None = None,
    macos: AgentInstallConfig | None = None,
    linux: AgentInstallConfig | None = None,
) -> Agent:
    return Agent(
        name=name,
        command=command,
        description=description,
        check_path=check_path,
        install_cmd=install_cmd,
        macos=macos,
        linux=linux,
    )


# ---------------------------------------------------------------------------
# TestLoadAgents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadAgents:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_agents(tmp_path / "nonexistent.yaml")
        assert result == []

    def test_loads_agents(self, tmp_path):
        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n"
            "  - name: claude-code\n"
            "    command: claude\n"
            "    description: Claude Code\n"
        )
        agents = load_agents(manifest)
        assert len(agents) == 1
        assert agents[0].name == "claude-code"
        assert agents[0].command == "claude"

    def test_npm_method_parsed(self, tmp_path):
        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n"
            "  - name: gemini-cli\n"
            "    command: gemini\n"
            "    description: Gemini CLI\n"
            "    macos:\n"
            "      method: npm\n"
            '      package: "@google/gemini-cli"\n'
            "    linux:\n"
            "      method: npm\n"
            '      package: "@google/gemini-cli"\n'
        )
        agents = load_agents(manifest)
        assert agents[0].macos == AgentInstallConfig(
            method="npm", package="@google/gemini-cli"
        )
        assert agents[0].linux == AgentInstallConfig(
            method="npm", package="@google/gemini-cli"
        )

    def test_install_cmd_parsed(self, tmp_path):
        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n"
            "  - name: goose\n"
            "    command: goose\n"
            "    description: Goose\n"
            "    install_cmd: 'curl -fsSL https://example.com | bash'\n"
        )
        agents = load_agents(manifest)
        assert agents[0].install_cmd == "curl -fsSL https://example.com | bash"

    def test_skips_entries_missing_required_fields(self, tmp_path):
        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n"
            "  - name: broken\n"
            "    description: No command\n"
            "  - name: good\n"
            "    command: good\n"
            "    description: OK\n"
        )
        agents = load_agents(manifest)
        assert len(agents) == 1
        assert agents[0].name == "good"

    def test_empty_agents_key(self, tmp_path):
        manifest = tmp_path / "agents.yaml"
        manifest.write_text("agents: []\n")
        assert load_agents(manifest) == []


# ---------------------------------------------------------------------------
# TestIsAgentInstalled
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsAgentInstalled:
    def test_check_path_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        bin_dir = tmp_path / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "claude").touch()
        agent = _make_agent(check_path="~/.local/bin/claude")
        assert is_agent_installed(agent)

    def test_check_path_missing(self, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: Path("/nonexistent")))
        with patch("shell_configs.agents.shutil.which", return_value="/usr/bin/claude"):
            agent = _make_agent(check_path="~/.local/bin/claude")
            assert not is_agent_installed(agent)

    def test_no_check_path_uses_which(self):
        with patch(
            "shell_configs.agents.shutil.which", return_value="/usr/local/bin/claude"
        ):
            assert is_agent_installed(_make_agent())

    def test_no_check_path_command_missing(self):
        with patch("shell_configs.agents.shutil.which", return_value=None):
            assert not is_agent_installed(_make_agent())


# ---------------------------------------------------------------------------
# TestInstallAgent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallAgent:
    def test_already_installed_returns_success(self):
        with patch("shell_configs.agents.is_agent_installed", return_value=True):
            ok, msg = install_agent(_make_agent())
        assert ok
        assert "already installed" in msg

    def test_npm_method(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: p.value == "macos",
        )
        agent = _make_agent(
            name="gemini-cli",
            command="gemini",
            macos=AgentInstallConfig(method="npm", package="@google/gemini-cli"),
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=False),
            patch(
                "shell_configs.agents.shutil.which",
                return_value="/usr/bin/npm",
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = install_agent(agent)
        assert ok
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["npm", "install", "-g", "@google/gemini-cli"]

    def test_script_fallback(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: False,
        )
        agent = _make_agent(
            install_cmd="curl -fsSL https://example.com/install.sh | bash"
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = install_agent(agent)
        assert ok
        assert mock_run.call_args[1].get("shell") is True

    def test_script_install_failure(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: False,
        )
        agent = _make_agent(install_cmd="curl -fsSL https://example.com | bash")
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="connection refused"
            )
            ok, msg = install_agent(agent)
        assert not ok
        assert "connection refused" in msg

    def test_script_install_timeout(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: False,
        )
        agent = _make_agent(install_cmd="curl -fsSL https://example.com | bash")
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=False),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)),
        ):
            ok, msg = install_agent(agent)
        assert not ok
        assert "timed out" in msg

    def test_linux_uses_install_cmd(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: p.value == "wsl",
        )
        agent = _make_agent(
            install_cmd="curl -fsSL https://claude.ai/install.sh | bash"
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = install_agent(agent)
        assert ok
        assert mock_run.call_args[1].get("shell") is True

    def test_dry_run_npm(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: p.value == "macos",
        )
        agent = _make_agent(
            name="gemini-cli",
            command="gemini",
            macos=AgentInstallConfig(method="npm", package="@google/gemini-cli"),
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=False),
            patch(
                "shell_configs.agents.shutil.which",
                return_value="/usr/bin/npm",
            ),
        ):
            ok, msg = install_agent(agent, dry_run=True)
        assert ok
        assert "Would" in msg

    def test_no_install_method_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: False,
        )
        agent = _make_agent()
        with patch("shell_configs.agents.is_agent_installed", return_value=False):
            ok, msg = install_agent(agent)
        assert not ok
        assert "No install method" in msg

    def test_npm_unavailable_returns_clear_message(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.agents.is_platform",
            lambda p: p.value == "macos",
        )
        agent = _make_agent(
            name="gemini-cli",
            command="gemini",
            macos=AgentInstallConfig(method="npm", package="@google/gemini-cli"),
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=False),
            patch("shell_configs.agents.shutil.which", return_value=None),
        ):
            ok, msg = install_agent(agent)
        assert not ok
        assert "npm is not available" in msg
        assert "Node.js" in msg


# ---------------------------------------------------------------------------
# TestGetAgentVersion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAgentVersion:
    def test_returns_version_string(self):
        with (
            patch(
                "shell_configs.agents.shutil.which",
                return_value="/usr/local/bin/claude",
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="claude-code 1.0.0",
                stderr="",
            )
            version = get_agent_version(_make_agent())
        assert version == "claude-code 1.0.0"

    def test_returns_none_when_command_not_found(self):
        with patch("shell_configs.agents.shutil.which", return_value=None):
            assert get_agent_version(_make_agent()) is None

    def test_version_flag_fallback(self):
        with (
            patch("shell_configs.agents.shutil.which", return_value="/usr/bin/goose"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[], returncode=1, stdout="", stderr="unknown flag"
                ),
                subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="goose 1.2.3", stderr=""
                ),
            ]
            version = get_agent_version(_make_agent(name="goose", command="goose"))
        assert version == "goose 1.2.3"
        assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# TestAgentsComponent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAgentsComponent:
    def _make_ctx(self, dry_run: bool = False, yes: bool = True) -> MagicMock:
        ctx = MagicMock()
        ctx.dry_run = dry_run
        ctx.yes = yes
        return ctx

    def test_plan_identifies_missing(self, tmp_path):
        from shell_configs.cli.components.agents import AgentsComponent

        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n"
            "  - name: claude-code\n"
            "    command: claude\n"
            "    description: Claude Code\n"
        )
        with (
            patch("shell_configs.agents.get_config_dir", return_value=tmp_path),
            patch("shell_configs.agents.is_agent_installed", return_value=False),
        ):
            plan = AgentsComponent().plan(self._make_ctx())

        assert plan.has_changes
        assert len(plan.missing) == 1
        assert plan.missing[0].name == "claude-code"

    def test_plan_no_changes_when_all_installed(self, tmp_path):
        from shell_configs.cli.components.agents import AgentsComponent

        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n"
            "  - name: claude-code\n"
            "    command: claude\n"
            "    description: Claude Code\n"
        )
        with (
            patch("shell_configs.agents.get_config_dir", return_value=tmp_path),
            patch("shell_configs.agents.is_agent_installed", return_value=True),
        ):
            plan = AgentsComponent().plan(self._make_ctx())

        assert not plan.has_changes
        assert plan.missing == []

    def test_apply_installs_missing(self, tmp_path):
        from shell_configs.cli.components.agents import AgentsComponent
        from shell_configs.cli.context import AgentsPlan

        agent = _make_agent()
        plan = AgentsPlan(has_changes=True, all_agents=[agent], missing=[agent])

        with patch(
            "shell_configs.agents.install_agent",
            return_value=(True, "Installed claude-code"),
        ) as mock_install:
            AgentsComponent().apply(self._make_ctx(), plan)

        mock_install.assert_called_once_with(agent, dry_run=False)

    def test_apply_respects_dry_run(self, tmp_path):
        from shell_configs.cli.components.agents import AgentsComponent
        from shell_configs.cli.context import AgentsPlan

        agent = _make_agent()
        plan = AgentsPlan(has_changes=True, all_agents=[agent], missing=[agent])

        with patch(
            "shell_configs.agents.install_agent",
            return_value=(True, "Would install claude-code"),
        ) as mock_install:
            AgentsComponent().apply(self._make_ctx(dry_run=True), plan)

        mock_install.assert_called_once_with(agent, dry_run=True)
