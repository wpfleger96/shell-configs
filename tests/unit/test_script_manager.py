"""Unit tests for script_manager orphan detection."""

from pathlib import Path

import pytest

from shell_configs.platform import Platform
from shell_configs.script_manager import (
    DiscoveredScript,
    ScriptManifest,
    find_orphaned_scripts,
)

_ALL_PLATFORMS = frozenset({Platform.MACOS, Platform.LINUX, Platform.WSL})


def _make_manifest(entries: dict[str, str], manifest_path: Path) -> ScriptManifest:
    """Create a ScriptManifest with given script-name→source-path entries."""
    manifest = ScriptManifest(manifest_path)
    for name, source_path in entries.items():
        manifest.record_install(name, "abc123", source_path)
    manifest.save()
    return ScriptManifest(manifest_path)  # reload from disk


def _script(
    name: str, platforms: frozenset[Platform] = _ALL_PLATFORMS
) -> DiscoveredScript:
    return DiscoveredScript(name=name, rel_path=name, platforms=platforms)


@pytest.mark.unit
class TestFindOrphanedScripts:
    def test_empty_manifest_returns_no_orphans(self, temp_dir):
        manifest = ScriptManifest(temp_dir / "manifest.json")
        scripts = [_script("check-pr-release-status"), _script("transcribe")]
        assert find_orphaned_scripts(manifest, scripts) == []

    def test_all_manifest_entries_present_returns_no_orphans(self, temp_dir):
        manifest = _make_manifest(
            {
                "check-pr-release-status": "git/check-pr-release-status",
                "transcribe": "transcription/transcribe",
            },
            temp_dir / "manifest.json",
        )
        scripts = [_script("check-pr-release-status"), _script("transcribe")]
        assert find_orphaned_scripts(manifest, scripts) == []

    def test_removed_script_detected_as_orphan(self, temp_dir):
        manifest = _make_manifest(
            {
                "check-pr-release-status": "git/check-pr-release-status",
                "old-script": "git/old-script",
                "transcribe": "transcription/transcribe",
            },
            temp_dir / "manifest.json",
        )
        scripts = [_script("check-pr-release-status"), _script("transcribe")]
        assert find_orphaned_scripts(manifest, scripts) == ["old-script"]

    def test_all_scripts_removed_all_orphaned(self, temp_dir):
        manifest = _make_manifest(
            {"alpha": "git/alpha", "beta": "git/beta"},
            temp_dir / "manifest.json",
        )
        assert find_orphaned_scripts(manifest, []) == ["alpha", "beta"]

    def test_orphans_returned_sorted(self, temp_dir):
        manifest = _make_manifest(
            {"zebra": "z", "apple": "a", "mango": "m"},
            temp_dir / "manifest.json",
        )
        assert find_orphaned_scripts(manifest, []) == ["apple", "mango", "zebra"]

    def test_platform_filtered_script_not_flagged_as_orphan(self, temp_dir):
        """A macOS-only script in the manifest should NOT be an orphan on any platform
        when the caller passes discover_scripts(include_all=True) results."""
        manifest = _make_manifest(
            {"fix-git-case-conflicts": "macos/fix-git-case-conflicts"},
            temp_dir / "manifest.json",
        )
        # Simulate include_all=True — the macOS-only script is in the list
        macos_only = _script("fix-git-case-conflicts", frozenset({Platform.MACOS}))
        assert find_orphaned_scripts(manifest, [macos_only]) == []

    def test_manifest_not_on_disk_returns_no_orphans(self, temp_dir):
        manifest = ScriptManifest(temp_dir / "nonexistent.json")
        scripts = [_script("check-pr-release-status")]
        assert find_orphaned_scripts(manifest, scripts) == []
