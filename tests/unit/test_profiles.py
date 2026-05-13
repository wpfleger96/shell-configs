"""Tests for profile loading, inheritance, and state resolution."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from shell_configs.profiles.loader import ProfileLoader
from shell_configs.profiles.profile import (
    CircularInheritanceError,
    ProfileNotFoundError,
)
from shell_configs.profiles.state import resolve_active_profile
from shell_configs.shells.base import deep_merge as _deep_merge


@pytest.mark.unit
class TestDeepMerge:
    """Tests for the _deep_merge utility."""

    def test_disjoint_keys_combined(self):
        result = _deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_override_wins_on_scalar(self):
        result = _deep_merge({"key": "base"}, {"key": "override"})
        assert result["key"] == "override"

    def test_nested_dict_merged_recursively(self):
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 99, "c": 3}}
        result = _deep_merge(base, override)
        assert result["outer"] == {"a": 1, "b": 99, "c": 3}

    def test_none_override_replaces_dict(self):
        result = _deep_merge({"k": {"nested": 1}}, {"k": None})
        assert result["k"] is None

    def test_base_dict_not_mutated(self):
        base = {"a": {"x": 1}}
        _deep_merge(base, {"a": {"y": 2}})
        assert base == {"a": {"x": 1}}

    def test_empty_override_returns_base_copy(self):
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == base
        assert result is not base


@pytest.mark.unit
class TestProfileLoader:
    """Tests for ProfileLoader scanning and parsing."""

    def test_list_profiles_returns_sorted_names(self, temp_dir):
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "work.yaml").write_text("name: work\n")
        (profiles_dir / "personal.yaml").write_text("name: personal\n")
        config_dir = temp_dir
        (config_dir / "profiles").resolve()

        loader = ProfileLoader(config_dir)
        names = loader.list_profiles()
        assert names == ["default", "personal", "work"]

    def test_list_profiles_includes_default_when_no_file(self, temp_dir):
        config_dir = temp_dir
        loader = ProfileLoader(config_dir)
        assert "default" in loader.list_profiles()

    def test_list_profiles_empty_dir(self, temp_dir):
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir()
        loader = ProfileLoader(temp_dir)
        assert loader.list_profiles() == ["default"]

    def test_load_profile_parses_yaml(self, temp_dir):
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "work.yaml").write_text(
            "name: work\ndescription: Work laptop\nextends: personal\n"
        )
        loader = ProfileLoader(temp_dir)
        p = loader.load_profile("work")
        assert p.name == "work"
        assert p.description == "Work laptop"
        assert p.extends == "personal"

    def test_load_default_profile_without_file(self, temp_dir):
        loader = ProfileLoader(temp_dir)
        p = loader.load_profile("default")
        assert p.name == "default"
        assert p.settings_overrides == {}
        assert p.shell_overrides == {}

    def test_load_profile_not_found_raises(self, temp_dir):
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir()
        loader = ProfileLoader(temp_dir)
        with pytest.raises(ProfileNotFoundError, match="nonexistent"):
            loader.load_profile("nonexistent")

    def test_load_profile_invalid_yaml_raises(self, temp_dir):
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "bad.yaml").write_text("invalid: yaml: content: :")
        loader = ProfileLoader(temp_dir)
        from shell_configs.profiles.profile import ProfileError

        with pytest.raises(ProfileError):
            loader.load_profile("bad")

    def test_load_profile_settings_overrides(self, temp_dir):
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir()
        content = yaml.dump(
            {"name": "work", "settings_overrides": {"vscode": {"key": "value"}}}
        )
        (profiles_dir / "work.yaml").write_text(content)
        loader = ProfileLoader(temp_dir)
        p = loader.load_profile("work")
        assert p.settings_overrides == {"vscode": {"key": "value"}}

    def test_load_profile_shell_overrides(self, temp_dir):
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir()
        content = yaml.dump(
            {"name": "work", "shell_overrides": {"shared": "export FOO=1"}}
        )
        (profiles_dir / "work.yaml").write_text(content)
        loader = ProfileLoader(temp_dir)
        p = loader.load_profile("work")
        assert p.shell_overrides == {"shared": "export FOO=1"}


@pytest.mark.unit
class TestProfileInheritance:
    """Tests for resolve_profile walking the extends chain."""

    def _make_loader(self, temp_dir: Path, profiles: dict[str, Any]) -> ProfileLoader:
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        for name, data in profiles.items():
            (profiles_dir / f"{name}.yaml").write_text(yaml.dump(data))
        return ProfileLoader(temp_dir)

    def test_single_level_inheritance(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {"name": "default", "description": "base"},
                "personal": {
                    "name": "personal",
                    "extends": "default",
                    "description": "personal",
                },
            },
        )
        p = loader.resolve_profile("personal")
        assert p.name == "personal"
        assert p.description == "personal"

    def test_multi_level_settings_merge(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "settings_overrides": {"vscode": {"base_key": "base"}},
                },
                "personal": {
                    "name": "personal",
                    "extends": "default",
                    "settings_overrides": {"vscode": {"personal_key": "personal"}},
                },
                "work": {
                    "name": "work",
                    "extends": "personal",
                    "settings_overrides": {"vscode": {"work_key": "work"}},
                },
            },
        )
        p = loader.resolve_profile("work")
        assert p.settings_overrides["vscode"]["base_key"] == "base"
        assert p.settings_overrides["vscode"]["personal_key"] == "personal"
        assert p.settings_overrides["vscode"]["work_key"] == "work"

    def test_child_wins_on_key_conflict(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "settings_overrides": {"vscode": {"key": "from_default"}},
                },
                "work": {
                    "name": "work",
                    "extends": "default",
                    "settings_overrides": {"vscode": {"key": "from_work"}},
                },
            },
        )
        p = loader.resolve_profile("work")
        assert p.settings_overrides["vscode"]["key"] == "from_work"

    def test_shell_overrides_appended(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "shell_overrides": {"shared": "export BASE=1"},
                },
                "work": {
                    "name": "work",
                    "extends": "default",
                    "shell_overrides": {"shared": "export WORK=1"},
                },
            },
        )
        p = loader.resolve_profile("work")
        assert "export BASE=1" in p.shell_overrides["shared"]
        assert "export WORK=1" in p.shell_overrides["shared"]
        base_pos = p.shell_overrides["shared"].find("export BASE=1")
        work_pos = p.shell_overrides["shared"].find("export WORK=1")
        assert base_pos < work_pos

    def test_packages_union(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "packages": {"add": ["pkg-a"], "remove": ["pkg-x"]},
                },
                "work": {
                    "name": "work",
                    "extends": "default",
                    "packages": {"add": ["pkg-b"], "remove": ["pkg-y"]},
                },
            },
        )
        p = loader.resolve_profile("work")
        assert "pkg-a" in p.packages["add"]
        assert "pkg-b" in p.packages["add"]
        assert "pkg-x" in p.packages["remove"]
        assert "pkg-y" in p.packages["remove"]

    def test_child_remove_wins_over_parent_add(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "base": {
                    "name": "base",
                    "packages": {"add": ["corp-tool", "shared-tool"]},
                },
                "child": {
                    "name": "child",
                    "extends": "base",
                    "packages": {"remove": ["corp-tool"]},
                },
            },
        )
        p = loader.resolve_profile("child")
        assert "corp-tool" not in p.packages.get("add", [])
        assert "corp-tool" in p.packages.get("remove", [])
        assert "shared-tool" in p.packages.get("add", [])

    def test_bare_yaml_keys_parsed_as_none(self, temp_dir):
        """Bare YAML keys (e.g. `extensions:` with no value) parse as None."""
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        (profiles_dir / "default.yaml").write_text(
            yaml.dump(
                {
                    "name": "default",
                    "settings_overrides": {"vscode": {"key": "val"}},
                    "shell_overrides": {"shared": "export A=1"},
                    "packages": {"add": ["pkg-a"]},
                    "extensions": {"vscode": {"add": ["ext-a"]}},
                }
            )
        )
        (profiles_dir / "child.yaml").write_text(
            "name: child\nextends: default\n"
            "settings_overrides:\nshell_overrides:\npackages:\nextensions:\n"
        )
        loader = ProfileLoader(temp_dir)
        p = loader.resolve_profile("child")
        assert p.settings_overrides == {"vscode": {"key": "val"}}
        assert p.shell_overrides == {"shared": "export A=1"}
        assert "pkg-a" in p.packages.get("add", [])
        assert "ext-a" in p.extensions.get("vscode", {}).get("add", [])

    def test_default_fallback_no_file(self, temp_dir):
        loader = ProfileLoader(temp_dir)
        p = loader.resolve_profile("default")
        assert p.name == "default"
        assert p.settings_overrides == {}

    def test_profile_not_found_in_chain_raises(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "work": {"name": "work", "extends": "nonexistent"},
            },
        )
        with pytest.raises(ProfileNotFoundError):
            loader.resolve_profile("work")


@pytest.mark.unit
class TestCycleDetection:
    """Tests for circular inheritance detection."""

    def _make_loader(self, temp_dir: Path, profiles: dict[str, Any]) -> ProfileLoader:
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        for name, data in profiles.items():
            (profiles_dir / f"{name}.yaml").write_text(yaml.dump(data))
        return ProfileLoader(temp_dir)

    def test_direct_self_reference_raises(self, temp_dir):
        loader = self._make_loader(
            temp_dir, {"cycle": {"name": "cycle", "extends": "cycle"}}
        )
        with pytest.raises(CircularInheritanceError):
            loader.resolve_profile("cycle")

    def test_two_node_cycle_raises(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "a": {"name": "a", "extends": "b"},
                "b": {"name": "b", "extends": "a"},
            },
        )
        with pytest.raises(CircularInheritanceError):
            loader.resolve_profile("a")

    def test_three_node_cycle_raises(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "a": {"name": "a", "extends": "b"},
                "b": {"name": "b", "extends": "c"},
                "c": {"name": "c", "extends": "a"},
            },
        )
        with pytest.raises(CircularInheritanceError):
            loader.resolve_profile("a")


@pytest.mark.unit
class TestResolveActiveProfile:
    """Tests for resolve_active_profile priority logic."""

    def _make_loader(self, temp_dir: Path) -> ProfileLoader:
        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        import yaml

        for name in ("default", "personal", "work"):
            (profiles_dir / f"{name}.yaml").write_text(
                yaml.dump({"name": name, "description": f"{name} profile"})
            )
        return ProfileLoader(temp_dir)

    def test_flag_value_takes_priority(self, temp_dir, mock_home):
        loader = self._make_loader(temp_dir)
        p = resolve_active_profile("work", loader)
        assert p.name == "work"

    def test_auto_config_used_when_no_flag(self, temp_dir, mock_home, monkeypatch):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 5\nactive_profile: personal\n")
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        loader = self._make_loader(temp_dir)
        p = resolve_active_profile(None, loader)
        assert p.name == "personal"

    def test_default_fallback_when_no_flag_no_state(
        self, temp_dir, mock_home, monkeypatch
    ):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        loader = self._make_loader(temp_dir)
        p = resolve_active_profile(None, loader)
        assert p.name == "default"

    def test_flag_overrides_auto_config(self, temp_dir, mock_home, monkeypatch):
        config_file = mock_home / ".shell-configs" / "update_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("backup_retention: 5\nactive_profile: personal\n")
        monkeypatch.setattr(
            "shell_configs.bootstrap.config.get_config_path",
            lambda pkg="shell-configs": config_file,
        )
        loader = self._make_loader(temp_dir)
        p = resolve_active_profile("work", loader)
        assert p.name == "work"
