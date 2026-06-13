"""Tests for AI coding agent management."""

from __future__ import annotations

import subprocess

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shell_configs.agents import (
    Agent,
    AgentInstallConfig,
    get_agent_install_method,
    get_agent_version,
    install_agent,
    is_agent_installed,
    load_agents,
    uninstall_agent,
    uninstall_agent_by_manifest_entry,
)
from shell_configs.agents_registry import DEPRECATED_AGENTS, DeprecatedAgentSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(
    name: str = "claude-code",
    command: str = "claude",
    description: str = "Claude Code",
    check_path: str | None = None,
    install_cmd: str | None = None,
    uninstall_cmd: str | None = None,
    macos: AgentInstallConfig | None = None,
    linux: AgentInstallConfig | None = None,
) -> Agent:
    return Agent(
        name=name,
        command=command,
        description=description,
        check_path=check_path,
        install_cmd=install_cmd,
        uninstall_cmd=uninstall_cmd,
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

    def test_uninstall_cmd_parsed(self, tmp_path):
        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n"
            "  - name: custom-agent\n"
            "    command: custom-agent\n"
            "    description: Custom Agent\n"
            '    uninstall_cmd: "rm -rf /tmp/agent"\n'
        )
        with patch("shell_configs.agents.get_config_dir", return_value=tmp_path):
            agents = load_agents()
        assert agents[0].uninstall_cmd == "rm -rf /tmp/agent"


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
            "shell_configs.installers.is_platform",
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
            "shell_configs.installers.is_platform",
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
            "shell_configs.installers.is_platform",
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
            "shell_configs.installers.is_platform",
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
            "shell_configs.installers.is_platform",
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
            "shell_configs.installers.is_platform",
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
            "shell_configs.installers.is_platform",
            lambda p: False,
        )
        agent = _make_agent()
        with patch("shell_configs.agents.is_agent_installed", return_value=False):
            ok, msg = install_agent(agent)
        assert not ok
        assert "No install method" in msg

    def test_npm_unavailable_returns_clear_message(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform",
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

    def test_plan_includes_deprecated_agents(self, tmp_path, monkeypatch):
        from shell_configs.cli.components.agents import AgentsComponent

        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n  - name: good\n    command: good\n    description: OK\n"
        )

        deprecated = (
            DeprecatedAgentSpec(agent_id="old-tool", command_name="old-tool"),
        )

        with (
            patch("shell_configs.agents.get_config_dir", return_value=tmp_path),
            patch("shell_configs.agents.is_agent_installed", return_value=True),
            patch("shell_configs.agents_registry.DEPRECATED_AGENTS", deprecated),
            patch("shutil.which", return_value="/usr/bin/old-tool"),
            patch("shell_configs.agent_manifest.AgentManifest") as MockManifest,
        ):
            mock_instance = MockManifest.return_value
            mock_instance.is_new = True
            plan = AgentsComponent().plan(self._make_ctx())

        assert len(plan.deprecated_installed) == 1
        assert plan.deprecated_installed[0].agent_id == "old-tool"

    def test_plan_skips_orphans_on_first_run(self, tmp_path):
        from shell_configs.cli.components.agents import AgentsComponent

        manifest = tmp_path / "agents.yaml"
        manifest.write_text(
            "agents:\n  - name: good\n    command: good\n    description: OK\n"
        )

        with (
            patch("shell_configs.agents.get_config_dir", return_value=tmp_path),
            patch("shell_configs.agents.is_agent_installed", return_value=True),
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=tmp_path / "nonexistent.json",
            ),
        ):
            plan = AgentsComponent().plan(self._make_ctx())

        assert plan.orphaned == []

    def test_uninstall_iterates_manifest(self, tmp_path):
        from shell_configs.cli.components.agents import AgentsComponent

        manifest_path = tmp_path / "installed_agents.json"
        import json

        manifest_data = {
            "version": 1,
            "agents": {
                "test-agent": {
                    "command_name": "test-cmd",
                    "install_method": "script",
                    "package": None,
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        manifest_path.write_text(json.dumps(manifest_data))

        with (
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=manifest_path,
            ),
            patch("shell_configs.agents.is_agent_installed", return_value=False),
        ):
            AgentsComponent().uninstall(self._make_ctx())

        # Manifest should be updated (entry removed since agent wasn't installed)
        reloaded = json.loads(manifest_path.read_text())
        assert "test-agent" not in reloaded["agents"]

    def test_apply_removes_orphaned_agents(self, tmp_path):
        import json

        from shell_configs.cli.components.agents import AgentsComponent
        from shell_configs.cli.context import AgentsPlan

        manifest_path = tmp_path / "installed_agents.json"
        manifest_data = {
            "version": 1,
            "agents": {
                "old-agent": {
                    "command_name": "old-cmd",
                    "install_method": "npm",
                    "package": "@scope/old-agent",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        manifest_path.write_text(json.dumps(manifest_data))

        plan = AgentsPlan(
            has_changes=True, all_agents=[], missing=[], orphaned=["old-agent"]
        )

        with (
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.agents.uninstall_agent_by_manifest_entry",
                return_value=(True, "Uninstalled"),
            ),
        ):
            AgentsComponent().apply(self._make_ctx(), plan)

        reloaded = json.loads(manifest_path.read_text())
        assert "old-agent" not in reloaded["agents"]

    def test_apply_handles_orphan_removal_failure(self, tmp_path):
        import json

        from shell_configs.cli.components.agents import AgentsComponent
        from shell_configs.cli.context import AgentsPlan

        manifest_path = tmp_path / "installed_agents.json"
        manifest_data = {
            "version": 1,
            "agents": {
                "old-agent": {
                    "command_name": "old-cmd",
                    "install_method": "npm",
                    "package": "@scope/old-agent",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        manifest_path.write_text(json.dumps(manifest_data))

        plan = AgentsPlan(
            has_changes=True, all_agents=[], missing=[], orphaned=["old-agent"]
        )

        with (
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.agents.uninstall_agent_by_manifest_entry",
                return_value=(False, "error"),
            ),
        ):
            AgentsComponent().apply(self._make_ctx(), plan)

        reloaded = json.loads(manifest_path.read_text())
        assert "old-agent" in reloaded["agents"]

    def test_apply_removes_deprecated_agents(self, tmp_path):
        import json

        from shell_configs.cli.components.agents import AgentsComponent
        from shell_configs.cli.context import AgentsPlan

        manifest_path = tmp_path / "installed_agents.json"
        manifest_path.write_text(json.dumps({"version": 1, "agents": {}}))

        spec = DeprecatedAgentSpec(agent_id="old-tool", command_name="old-tool")
        plan = AgentsPlan(
            has_changes=True,
            all_agents=[],
            missing=[],
            deprecated_installed=[spec],
        )

        with (
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=manifest_path,
            ),
            patch("shutil.which", return_value="/usr/bin/old-tool"),
            patch(
                "shell_configs.agents.uninstall_agent",
                return_value=(True, "Removed"),
            ) as mock_uninstall,
        ):
            AgentsComponent().apply(self._make_ctx(), plan)

        mock_uninstall.assert_called_once()
        _, kwargs = mock_uninstall.call_args
        assert kwargs.get("dry_run") is False

    def test_apply_passes_dry_run_to_orphan_uninstall(self, tmp_path):
        import json

        from shell_configs.cli.components.agents import AgentsComponent
        from shell_configs.cli.context import AgentsPlan

        manifest_path = tmp_path / "installed_agents.json"
        manifest_data = {
            "version": 1,
            "agents": {
                "old-agent": {
                    "command_name": "old-cmd",
                    "install_method": "npm",
                    "package": "@scope/old-agent",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        manifest_path.write_text(json.dumps(manifest_data))

        plan = AgentsPlan(
            has_changes=True, all_agents=[], missing=[], orphaned=["old-agent"]
        )

        with (
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.agents.uninstall_agent_by_manifest_entry",
                return_value=(True, "Uninstalled"),
            ) as mock_uninstall,
        ):
            AgentsComponent().apply(self._make_ctx(dry_run=True), plan)

        _, kwargs = mock_uninstall.call_args
        assert kwargs.get("dry_run") is True

    def test_uninstall_retains_manifest_on_failure(self, tmp_path):
        import json

        from shell_configs.cli.components.agents import AgentsComponent

        manifest_path = tmp_path / "installed_agents.json"
        manifest_data = {
            "version": 1,
            "agents": {
                "test-agent": {
                    "command_name": "test-cmd",
                    "install_method": "npm",
                    "package": "@scope/test-agent",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        manifest_path.write_text(json.dumps(manifest_data))

        with (
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.agents.uninstall_agent_by_manifest_entry",
                return_value=(False, "error"),
            ),
        ):
            AgentsComponent().uninstall(self._make_ctx())

        reloaded = json.loads(manifest_path.read_text())
        assert "test-agent" in reloaded["agents"]

    def test_uninstall_removes_manifest_on_success(self, tmp_path):
        import json

        from shell_configs.cli.components.agents import AgentsComponent

        manifest_path = tmp_path / "installed_agents.json"
        manifest_data = {
            "version": 1,
            "agents": {
                "test-agent": {
                    "command_name": "test-cmd",
                    "install_method": "npm",
                    "package": "@scope/test-agent",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        manifest_path.write_text(json.dumps(manifest_data))

        with (
            patch(
                "shell_configs.agent_manifest.get_default_agent_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.agents.uninstall_agent_by_manifest_entry",
                return_value=(True, "Removed"),
            ),
        ):
            AgentsComponent().uninstall(self._make_ctx())

        reloaded = json.loads(manifest_path.read_text())
        assert "test-agent" not in reloaded["agents"]


# ---------------------------------------------------------------------------
# TestUninstallAgent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUninstallAgent:
    def test_not_installed_returns_early(self):
        with patch("shell_configs.agents.is_agent_installed", return_value=False):
            ok, msg = uninstall_agent(_make_agent())
        assert ok
        assert "not installed" in msg

    def test_npm_uninstall(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform", lambda p: p.value == "macos"
        )
        agent = _make_agent(
            name="gemini-cli",
            command="gemini",
            macos=AgentInstallConfig(method="npm", package="@google/gemini-cli"),
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=True),
            patch("shell_configs.agents.shutil.which", return_value="/usr/bin/npm"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = uninstall_agent(agent)
        assert ok
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["npm", "uninstall", "-g", "@google/gemini-cli"]

    def test_script_uninstall(self, monkeypatch):
        monkeypatch.setattr("shell_configs.installers.is_platform", lambda p: False)
        agent = _make_agent(uninstall_cmd="rm -rf /tmp/test-agent")
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = uninstall_agent(agent)
        assert ok
        assert mock_run.call_args[1].get("shell") is True

    def test_no_uninstall_method(self, monkeypatch):
        monkeypatch.setattr("shell_configs.installers.is_platform", lambda p: False)
        agent = _make_agent()  # no uninstall_cmd, no platform config
        with patch("shell_configs.agents.is_agent_installed", return_value=True):
            ok, msg = uninstall_agent(agent)
        assert not ok
        assert "No uninstall method" in msg

    def test_dry_run_npm(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform", lambda p: p.value == "macos"
        )
        agent = _make_agent(
            name="gemini-cli",
            command="gemini",
            macos=AgentInstallConfig(method="npm", package="@google/gemini-cli"),
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=True),
            patch("shell_configs.agents.shutil.which", return_value="/usr/bin/npm"),
        ):
            ok, msg = uninstall_agent(agent, dry_run=True)
        assert ok
        assert "Would" in msg

    def test_npm_failure(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform", lambda p: p.value == "macos"
        )
        agent = _make_agent(
            name="gemini-cli",
            command="gemini",
            macos=AgentInstallConfig(method="npm", package="@google/gemini-cli"),
        )
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=True),
            patch("shell_configs.agents.shutil.which", return_value="/usr/bin/npm"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="permission denied"
            )
            ok, msg = uninstall_agent(agent)
        assert not ok
        assert "permission denied" in msg

    def test_timeout(self, monkeypatch):
        monkeypatch.setattr("shell_configs.installers.is_platform", lambda p: False)
        agent = _make_agent(uninstall_cmd="sleep 999")
        with (
            patch("shell_configs.agents.is_agent_installed", return_value=True),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)),
        ):
            ok, msg = uninstall_agent(agent)
        assert not ok
        assert "timed out" in msg


# ---------------------------------------------------------------------------
# TestDeprecatedAgentRegistry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeprecatedAgentRegistry:
    def test_is_tuple(self):
        assert isinstance(DEPRECATED_AGENTS, tuple)

    def test_starts_empty(self):
        assert len(DEPRECATED_AGENTS) == 0

    def test_spec_is_frozen(self):
        spec = DeprecatedAgentSpec(agent_id="test", command_name="test-cmd")
        with pytest.raises(FrozenInstanceError):
            spec.agent_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestGetAgentInstallMethod
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAgentInstallMethod:
    def test_npm_on_macos(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform", lambda p: p.value == "macos"
        )
        agent = _make_agent(
            macos=AgentInstallConfig(method="npm", package="@google/gemini-cli")
        )
        method, pkg = get_agent_install_method(agent)
        assert method == "npm"
        assert pkg == "@google/gemini-cli"

    def test_script_fallback(self, monkeypatch):
        monkeypatch.setattr("shell_configs.installers.is_platform", lambda p: False)
        agent = _make_agent(install_cmd="curl | bash")
        method, pkg = get_agent_install_method(agent)
        assert method == "script"
        assert pkg is None


# ---------------------------------------------------------------------------
# TestUninstallAgentByManifestEntry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUninstallAgentByManifestEntry:
    def test_npm_uninstall(self):
        with (
            patch("shell_configs.agents.shutil.which", return_value="/usr/bin/cmd"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            ok, msg = uninstall_agent_by_manifest_entry(
                "test", "cmd", "npm", "@scope/pkg"
            )
        assert ok
        assert mock_run.call_args[0][0] == ["npm", "uninstall", "-g", "@scope/pkg"]

    def test_not_installed(self):
        with patch("shell_configs.agents.shutil.which", return_value=None):
            ok, msg = uninstall_agent_by_manifest_entry("test", "cmd", "npm", "pkg")
        assert ok
        assert "not installed" in msg

    def test_script_no_reverse(self):
        with patch("shell_configs.agents.shutil.which", return_value="/usr/bin/cmd"):
            ok, msg = uninstall_agent_by_manifest_entry("test", "cmd", "script", None)
        assert ok
        assert "no reverse" in msg

    def test_unknown_method(self):
        with patch("shell_configs.agents.shutil.which", return_value="/usr/bin/cmd"):
            ok, msg = uninstall_agent_by_manifest_entry("test", "cmd", "brew", None)
        assert not ok
