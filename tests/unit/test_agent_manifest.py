"""Unit tests for agent_manifest module."""

from __future__ import annotations

from pathlib import Path

import pytest

from shell_configs.agent_manifest import AgentManifest, find_orphaned_agents
from shell_configs.agents import Agent


def _make_manifest(
    entries: dict[str, tuple[str, str, str | None]], path: Path
) -> AgentManifest:
    """Create a manifest with entries, save it, and reload from disk.

    entries: {name: (command_name, install_method, package)}
    """
    manifest = AgentManifest(path)
    for name, (cmd, method, pkg) in entries.items():
        manifest.record_install(name, cmd, method, pkg)
    manifest.save()
    return AgentManifest(path)  # reload from disk


def _agent(name: str, command: str = "test") -> Agent:
    return Agent(name=name, command=command, description="test agent")


@pytest.mark.unit
class TestAgentManifest:
    def test_load_empty_when_file_missing(self, tmp_path):
        manifest = AgentManifest(tmp_path / "nonexistent.json")
        assert manifest.agents == {}

    def test_save_and_reload_roundtrip(self, tmp_path):
        manifest = _make_manifest(
            {
                "claude-code": ("claude", "npm", "@anthropic-ai/claude-code"),
                "goose": ("goose", "script", None),
            },
            tmp_path / "manifest.json",
        )

        assert "claude-code" in manifest.agents
        entry = manifest.agents["claude-code"]
        assert entry.command_name == "claude"
        assert entry.install_method == "npm"
        assert entry.package == "@anthropic-ai/claude-code"
        assert entry.installed_at  # non-empty ISO timestamp

        goose = manifest.agents["goose"]
        assert goose.command_name == "goose"
        assert goose.install_method == "script"
        assert goose.package is None
        assert goose.installed_at

    def test_record_install_upserts(self, tmp_path):
        path = tmp_path / "manifest.json"
        manifest = AgentManifest(path)
        manifest.record_install(
            "claude-code", "claude", "npm", "@anthropic-ai/claude-code"
        )
        manifest.record_install("claude-code", "claude", "brew", None)
        manifest.save()

        reloaded = AgentManifest(path)
        entry = reloaded.agents["claude-code"]
        assert entry.install_method == "brew"
        assert entry.package is None

    def test_remove(self, tmp_path):
        path = tmp_path / "manifest.json"
        manifest = _make_manifest(
            {"claude-code": ("claude", "npm", "@anthropic-ai/claude-code")},
            path,
        )
        manifest.remove("claude-code")
        assert "claude-code" not in manifest.agents

    def test_corrupt_manifest_returns_empty(self, tmp_path):
        path = tmp_path / "manifest.json"
        path.write_text("not json")
        manifest = AgentManifest(path)
        assert manifest.agents == {}

    def test_is_new_true_when_file_absent(self, tmp_path):
        manifest = AgentManifest(tmp_path / "manifest.json")
        assert manifest.is_new is True

    def test_is_new_false_after_save(self, tmp_path):
        path = tmp_path / "manifest.json"
        manifest = AgentManifest(path)
        manifest.save()
        reloaded = AgentManifest(path)
        assert reloaded.is_new is False

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "dir" / "manifest.json"
        manifest = AgentManifest(path)
        manifest.record_install("claude-code", "claude", "npm", None)
        manifest.save()
        assert path.exists()

    def test_remove_nonexistent_is_noop(self, tmp_path):
        manifest = AgentManifest(tmp_path / "manifest.json")
        manifest.remove("does-not-exist")  # must not raise


@pytest.mark.unit
class TestFindOrphanedAgents:
    def test_no_orphans_when_all_match(self, tmp_path):
        manifest = _make_manifest(
            {"claude-code": ("claude", "npm", "@anthropic-ai/claude-code")},
            tmp_path / "manifest.json",
        )
        agents = [_agent("claude-code", "claude")]
        assert find_orphaned_agents(manifest, agents) == []

    def test_detects_orphans(self, tmp_path):
        manifest = _make_manifest(
            {"old-agent": ("old-agent", "script", None)},
            tmp_path / "manifest.json",
        )
        assert find_orphaned_agents(manifest, []) == ["old-agent"]

    def test_empty_manifest_no_orphans(self, tmp_path):
        manifest = AgentManifest(tmp_path / "manifest.json")
        agents = [_agent("claude-code", "claude"), _agent("goose", "goose")]
        assert find_orphaned_agents(manifest, agents) == []

    def test_sorted_output(self, tmp_path):
        manifest = _make_manifest(
            {
                "zebra": ("zebra", "script", None),
                "alpha": ("alpha", "npm", None),
            },
            tmp_path / "manifest.json",
        )
        assert find_orphaned_agents(manifest, []) == ["alpha", "zebra"]
