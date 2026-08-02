"""Unit tests for script_manager: orphan detection and profile gating."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shell_configs.platform import Platform
from shell_configs.script_manager import (
    DiscoveredScript,
    InstallResult,
    ScriptManifest,
    ScriptStatus,
    discover_scripts,
    find_orphaned_scripts,
    get_script_status,
    install_script,
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
    name: str,
    platforms: frozenset[Platform] = _ALL_PLATFORMS,
    profiles: frozenset[str] = frozenset(),
) -> DiscoveredScript:
    return DiscoveredScript(
        name=name, rel_path=name, platforms=platforms, profiles=profiles
    )


def _make_source_dir(
    tmp_path: Path,
    scripts: list[str],
    toml_content: str = "",
) -> Path:
    """Create a temp scripts source dir with files and an optional scripts.toml."""
    source_dir = tmp_path / "scripts"
    source_dir.mkdir()
    for name in scripts:
        (source_dir / name).write_text("#!/bin/sh\necho hello\n")
    if toml_content:
        (source_dir / "scripts.toml").write_text(toml_content)
    return source_dir


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


@pytest.mark.unit
class TestDiscoveredScriptProfiles:
    def test_profiles_field_defaults_to_empty_frozenset(self):
        script = DiscoveredScript(name="foo", rel_path="foo", platforms=_ALL_PLATFORMS)
        assert script.profiles == frozenset()

    def test_profiles_field_stored_correctly(self):
        script = _script("bar", profiles=frozenset({"work", "personal"}))
        assert script.profiles == frozenset({"work", "personal"})


@pytest.mark.unit
class TestDiscoverScriptsProfileParsing:
    def test_absent_profiles_key_yields_empty_frozenset(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["my-script"],
            toml_content='[my-script]\nplatforms = ["linux"]\n',
        )
        results = discover_scripts(
            current_platform=Platform.LINUX,
            source_dir=source_dir,
            active_profile="default",
        )
        assert len(results) == 1
        assert results[0].profiles == frozenset()

    def test_profiles_key_parsed_into_discovered_script(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        results = discover_scripts(
            current_platform=Platform.LINUX,
            source_dir=source_dir,
            include_all=True,
        )
        assert len(results) == 1
        assert results[0].profiles == frozenset({"work"})

    def test_multiple_profiles_parsed(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["shared-tool"],
            toml_content='[shared-tool]\nprofiles = ["work", "personal"]\n',
        )
        results = discover_scripts(
            current_platform=Platform.LINUX,
            source_dir=source_dir,
            include_all=True,
        )
        assert results[0].profiles == frozenset({"work", "personal"})


@pytest.mark.unit
class TestDiscoverScriptsProfileFiltering:
    def test_work_only_script_excluded_when_default_profile(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        results = discover_scripts(
            current_platform=Platform.LINUX,
            source_dir=source_dir,
            active_profile="default",
        )
        assert results == []

    def test_work_only_script_excluded_when_personal_profile(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        results = discover_scripts(
            current_platform=Platform.LINUX,
            source_dir=source_dir,
            active_profile="personal",
        )
        assert results == []

    def test_work_only_script_included_when_work_profile(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        results = discover_scripts(
            current_platform=Platform.LINUX,
            source_dir=source_dir,
            active_profile="work",
        )
        assert len(results) == 1
        assert results[0].name == "work-tool"

    def test_script_without_profiles_key_unaffected_by_active_profile(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["common-tool"],
            toml_content="",
        )
        for profile in ("default", "work", "personal"):
            results = discover_scripts(
                current_platform=Platform.LINUX,
                source_dir=source_dir,
                active_profile=profile,
            )
            assert len(results) == 1, f"expected script for profile={profile!r}"

    def test_include_all_returns_profile_gated_scripts_regardless(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool", "common-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        results = discover_scripts(source_dir=source_dir, include_all=True)
        names = {r.name for r in results}
        assert "work-tool" in names
        assert "common-tool" in names

    def test_profile_and_platform_filters_are_both_applied(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["macos-work-tool"],
            toml_content='[macos-work-tool]\nplatforms = ["macos"]\nprofiles = ["work"]\n',
        )
        # Platform mismatch: Linux machine, macOS-only script
        results = discover_scripts(
            current_platform=Platform.LINUX,
            source_dir=source_dir,
            active_profile="work",
        )
        assert results == []

        # Profile mismatch: macOS machine, wrong profile
        results = discover_scripts(
            current_platform=Platform.MACOS,
            source_dir=source_dir,
            active_profile="default",
        )
        assert results == []

        # Both match
        results = discover_scripts(
            current_platform=Platform.MACOS,
            source_dir=source_dir,
            active_profile="work",
        )
        assert len(results) == 1


@pytest.mark.unit
class TestInstallScriptProfileGating:
    def test_install_script_refused_for_profile_mismatch(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        script = _script("work-tool", profiles=frozenset({"work"}))
        manifest = ScriptManifest(tmp_path / "manifest.json")
        target_dir = tmp_path / "bin"
        target_dir.mkdir()

        result, message = install_script(
            script,
            target_dir,
            manifest,
            source_dir=source_dir,
            active_profile="personal",
        )

        assert result == InstallResult.SKIPPED_PROFILE
        assert "personal" in message
        assert not (target_dir / "work-tool").exists()

    def test_install_script_allowed_for_matching_profile(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        script = _script("work-tool", profiles=frozenset({"work"}))
        manifest = ScriptManifest(tmp_path / "manifest.json")
        target_dir = tmp_path / "bin"
        target_dir.mkdir()

        result, _ = install_script(
            script,
            target_dir,
            manifest,
            source_dir=source_dir,
            active_profile="work",
        )

        assert result == InstallResult.INSTALLED
        assert (target_dir / "work-tool").exists()

    def test_install_script_allowed_when_no_profile_restriction(self, tmp_path):
        source_dir = _make_source_dir(tmp_path, scripts=["common-tool"])
        script = _script("common-tool")
        manifest = ScriptManifest(tmp_path / "manifest.json")
        target_dir = tmp_path / "bin"
        target_dir.mkdir()

        result, _ = install_script(
            script,
            target_dir,
            manifest,
            source_dir=source_dir,
            active_profile="any-profile",
        )

        assert result == InstallResult.INSTALLED


@pytest.mark.unit
class TestGetScriptStatusProfileGating:
    def test_returns_skipped_profile_for_profile_mismatch(self, tmp_path):
        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
        )
        script = _script("work-tool", profiles=frozenset({"work"}))
        manifest = ScriptManifest(tmp_path / "manifest.json")
        target_dir = tmp_path / "bin"
        target_dir.mkdir()

        status = get_script_status(
            script,
            target_dir,
            manifest,
            source_dir=source_dir,
            active_profile="personal",
        )

        assert status == ScriptStatus.SKIPPED_PROFILE

    def test_does_not_return_skipped_profile_when_profiles_empty(self, tmp_path):
        source_dir = _make_source_dir(tmp_path, scripts=["common-tool"])
        script = _script("common-tool")
        manifest = ScriptManifest(tmp_path / "manifest.json")
        target_dir = tmp_path / "bin"
        target_dir.mkdir()

        status = get_script_status(
            script,
            target_dir,
            manifest,
            source_dir=source_dir,
            active_profile="any-profile",
        )

        assert status == ScriptStatus.MISSING


def _make_ctx(profile_name: str | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = True
    if profile_name is None:
        ctx.profile = None
    else:
        ctx.profile = MagicMock()
        ctx.profile.name = profile_name
    return ctx


@pytest.mark.unit
class TestScriptsComponentProfileResolution:
    """ScriptsComponent.plan() must use ctx.profile, not the on-disk config."""

    def test_plan_uses_ctx_profile_not_on_disk_config(self, tmp_path):
        """Filtering follows ctx.profile.name even when it differs from the persisted value."""
        from shell_configs.cli.components.scripts import ScriptsComponent

        target_dir = tmp_path / "bin"
        target_dir.mkdir()
        manifest_path = tmp_path / "manifest.json"

        # ctx says "work", but on-disk config says "personal" — filter must follow ctx
        ctx = _make_ctx(profile_name="work")
        work_script = _script("work-tool", profiles=frozenset({"work"}))

        # Lazy imports inside plan() mean patches must target source modules
        with (
            patch(
                "shell_configs.script_manager.discover_scripts",
                return_value=[work_script],
            ),
            patch(
                "shell_configs.script_manager.get_default_target_dir",
                return_value=target_dir,
            ),
            patch(
                "shell_configs.script_manager.get_default_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.script_manager.find_orphaned_scripts",
                return_value=[],
            ),
            patch(
                "shell_configs.platform.detect_platform",
                return_value=Platform.LINUX,
            ),
            # On-disk config reports "personal" — must NOT influence filtering
            patch(
                "shell_configs.bootstrap.config.load_auto_update_config",
                return_value=MagicMock(active_profile="personal"),
            ),
        ):
            plan = ScriptsComponent().plan(ctx)

        # The work-gated script should appear in entries because ctx.profile.name=="work"
        assert len(plan.entries) == 1
        assert plan.entries[0][0].name == "work-tool"

    def test_plan_excludes_script_when_ctx_profile_does_not_match(self, tmp_path):
        """A profile-gated script is excluded when ctx.profile doesn't match."""
        from shell_configs.cli.components.scripts import ScriptsComponent

        target_dir = tmp_path / "bin"
        target_dir.mkdir()
        manifest_path = tmp_path / "manifest.json"

        ctx = _make_ctx(profile_name="personal")
        work_script = _script("work-tool", profiles=frozenset({"work"}))

        with (
            patch(
                "shell_configs.script_manager.discover_scripts",
                return_value=[work_script],
            ),
            patch(
                "shell_configs.script_manager.get_default_target_dir",
                return_value=target_dir,
            ),
            patch(
                "shell_configs.script_manager.get_default_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.script_manager.find_orphaned_scripts",
                return_value=[],
            ),
            patch(
                "shell_configs.platform.detect_platform",
                return_value=Platform.LINUX,
            ),
        ):
            plan = ScriptsComponent().plan(ctx)

        assert plan.entries == []

    def test_plan_passes_active_profile_to_get_script_status(self, tmp_path):
        """get_script_status receives the same active_profile used for filtering.

        A profile-gated script that passes the filter (profile matches ctx) must
        receive the matching profile name and return a real status, not SKIPPED_PROFILE.
        """
        from shell_configs.cli.components.scripts import ScriptsComponent

        source_dir = _make_source_dir(
            tmp_path,
            scripts=["work-tool"],
            toml_content='[work-tool]\nprofiles = ["work"]\n',
        )
        target_dir = tmp_path / "bin"
        target_dir.mkdir()
        manifest_path = tmp_path / "manifest.json"

        ctx = _make_ctx(profile_name="work")
        work_script = _script(
            "work-tool",
            platforms=frozenset({Platform.LINUX}),
            profiles=frozenset({"work"}),
        )

        with (
            patch(
                "shell_configs.script_manager.discover_scripts",
                return_value=[work_script],
            ),
            patch(
                "shell_configs.script_manager.get_default_target_dir",
                return_value=target_dir,
            ),
            patch(
                "shell_configs.script_manager.get_default_manifest_path",
                return_value=manifest_path,
            ),
            patch(
                "shell_configs.script_manager.find_orphaned_scripts",
                return_value=[],
            ),
            patch(
                "shell_configs.platform.detect_platform",
                return_value=Platform.LINUX,
            ),
            patch(
                "shell_configs.bootstrap.config.load_auto_update_config",
                return_value=MagicMock(active_profile="personal"),
            ),
            patch(
                "shell_configs.script_manager.get_script_status",
                wraps=lambda entry, td, mf, active_profile=None, **kw: (
                    get_script_status(
                        entry,
                        td,
                        mf,
                        source_dir=source_dir,
                        active_profile=active_profile,
                    )
                ),
            ) as mock_get_status,
        ):
            plan = ScriptsComponent().plan(ctx)

        # get_script_status must have been called with active_profile="work"
        call_kwargs = mock_get_status.call_args
        assert call_kwargs.kwargs.get("active_profile") == "work"
        # The script passes the profile filter and should not be SKIPPED_PROFILE
        assert len(plan.entries) == 1
        _, status = plan.entries[0]
        assert status != ScriptStatus.SKIPPED_PROFILE
