"""Tests for config integration with profiles."""

import json

import pytest

from shell_configs.config import ConfigReader
from shell_configs.profiles.profile import Profile
from shell_configs.shells.base import deep_merge, merge_json_with_profile
from shell_configs.shells.bash import BashShell
from shell_configs.shells.git import GitShell


@pytest.mark.unit
class TestDeepMergePublic:
    """Tests for the public deep_merge in shells/base.py."""

    def test_merges_nested_dicts(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 4}, "c": 5}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 4}, "b": 3, "c": 5}

    def test_does_not_mutate_inputs(self):
        base = {"k": {"v": 1}}
        override = {"k": {"v": 2}}
        deep_merge(base, override)
        assert base["k"]["v"] == 1
        assert override["k"]["v"] == 2


@pytest.mark.unit
class TestMergeJsonWithProfile:
    """Tests for merge_json_with_profile."""

    def test_no_profile_overrides_returns_base_merge(self, tmp_path):
        base = tmp_path / "base.json"
        override = tmp_path / "override.json"
        base.write_text(json.dumps({"a": 1, "b": 2}))
        override.write_text(json.dumps({"b": 99, "c": 3}))

        result = merge_json_with_profile(base, override, None)
        data = json.loads(result)
        assert data == {"a": 1, "b": 99, "c": 3}

    def test_profile_overrides_applied_on_top(self, tmp_path):
        base = tmp_path / "base.json"
        override = tmp_path / "override.json"
        base.write_text(json.dumps({"a": 1, "b": 2}))
        override.write_text(json.dumps({"b": 99}))

        result = merge_json_with_profile(base, override, {"profile_key": "profile_val"})
        data = json.loads(result)
        assert data["a"] == 1
        assert data["b"] == 99
        assert data["profile_key"] == "profile_val"

    def test_profile_overrides_win_on_conflict(self, tmp_path):
        base = tmp_path / "base.json"
        override = tmp_path / "override.json"
        base.write_text(json.dumps({"key": "from_base"}))
        override.write_text(json.dumps({"key": "from_override"}))

        result = merge_json_with_profile(base, override, {"key": "from_profile"})
        data = json.loads(result)
        assert data["key"] == "from_profile"

    def test_missing_files_handled_gracefully(self, tmp_path):
        base = tmp_path / "missing_base.json"
        override = tmp_path / "missing_override.json"

        result = merge_json_with_profile(base, override, {"k": "v"})
        data = json.loads(result)
        assert data == {"k": "v"}

    def test_three_layer_merge_order(self, tmp_path):
        base = tmp_path / "base.json"
        override = tmp_path / "override.json"
        base.write_text(json.dumps({"base": 1, "shared": "base"}))
        override.write_text(json.dumps({"override": 2, "shared": "override"}))

        result = merge_json_with_profile(
            base, override, {"profile": 3, "shared": "profile"}
        )
        data = json.loads(result)
        assert data["base"] == 1
        assert data["override"] == 2
        assert data["shared"] == "profile"


@pytest.mark.unit
class TestConfigReaderWithProfile:
    """Tests for ConfigReader methods accepting a profile parameter."""

    def test_get_config_content_no_profile(self, test_repo):
        reader = ConfigReader(config_dir=test_repo / "config")
        content = reader.get_config_content("bash", "bashrc")
        assert content is not None
        assert "### Profile Override" not in content

    def test_get_config_content_with_shell_override(self, test_repo):
        p = Profile(
            name="work",
            shell_overrides={"bash": "export WORK=1"},
        )
        reader = ConfigReader(config_dir=test_repo / "config")
        content = reader.get_config_content("bash", "bashrc", profile=p)
        assert content is not None
        assert "### Profile Override (work) ###" in content
        assert "export WORK=1" in content

    def test_get_config_content_override_appended_after_base(self, test_repo):
        p = Profile(name="work", shell_overrides={"bash": "export WORK=1"})
        reader = ConfigReader(config_dir=test_repo / "config")
        content = reader.get_config_content("bash", "bashrc", profile=p)
        assert content is not None
        base_end = content.find("### Profile Override")
        assert base_end > 0
        assert "Test bash config" in content[:base_end]

    def test_get_config_content_no_override_for_this_shell(self, test_repo):
        p = Profile(name="work", shell_overrides={"zsh": "export ZSH_ONLY=1"})
        reader = ConfigReader(config_dir=test_repo / "config")
        content = reader.get_config_content("bash", "bashrc", profile=p)
        assert content is not None
        assert "### Profile Override" not in content

    def test_get_shared_config_content_with_shared_override(self, test_repo):
        shared_sh = test_repo / "config" / "shared.sh"
        shared_sh.write_text("# Base shared\n")

        p = Profile(name="work", shell_overrides={"shared": "export WORK_SHARED=1"})
        reader = ConfigReader(config_dir=test_repo / "config")
        content = reader.get_shared_config_content(BashShell(), profile=p)
        assert content is not None
        assert "### Profile Override (work) ###" in content
        assert "export WORK_SHARED=1" in content

    def test_get_shared_config_content_git_excludes_shared_override(self, test_repo):
        shared_gitconfig = test_repo / "config" / "shared.gitconfig"
        shared_gitconfig.write_text("[core]\n    autocrlf = input\n")

        p = Profile(name="work", shell_overrides={"shared": "export WORK_SHARED=1"})
        reader = ConfigReader(config_dir=test_repo / "config")
        content = reader.get_shared_config_content(GitShell(), profile=p)
        assert content is not None
        assert "### Profile Override" not in content
        assert "export WORK_SHARED=1" not in content
        assert "[core]" in content

    def test_get_shared_config_content_no_profile_unchanged(self, test_repo):
        shared_sh = test_repo / "config" / "shared.sh"
        shared_sh.write_text("# Base shared\n")

        reader = ConfigReader(config_dir=test_repo / "config")
        content_without = reader.get_shared_config_content(BashShell())
        content_with_empty = reader.get_shared_config_content(
            BashShell(), profile=Profile(name="default")
        )
        assert content_without == content_with_empty

    def test_get_config_content_none_config_name_returns_none(self, test_repo):
        p = Profile(name="work", shell_overrides={"bash": "export WORK=1"})
        reader = ConfigReader(config_dir=test_repo / "config")
        assert reader.get_config_content("bash", None, profile=p) is None
