"""Tests for IDE extension management."""

import json
import subprocess

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from shell_configs.extensions import (
    ExtensionDiff,
    ExtensionManager,
    ExtensionResultStatus,
    load_extension_file,
    load_extensions_json,
)
from shell_configs.profiles.loader import ProfileLoader


@pytest.mark.unit
class TestLoadExtensionFile:
    """Tests for parsing extension list files."""

    def test_parses_extension_ids(self, temp_dir):
        path = temp_dir / "extensions.txt"
        path.write_text("golang.go\nrust-lang.rust-analyzer\n")
        result = load_extension_file(path)
        assert result == {"golang.go", "rust-lang.rust-analyzer"}

    def test_skips_comments_and_blanks(self, temp_dir):
        path = temp_dir / "extensions.txt"
        path.write_text("# Comment\n\ngolang.go\n\n# Another comment\n")
        result = load_extension_file(path)
        assert result == {"golang.go"}

    def test_normalizes_to_lowercase(self, temp_dir):
        path = temp_dir / "extensions.txt"
        path.write_text("GitHub.Copilot-Chat\nMS-Python.Python\n")
        result = load_extension_file(path)
        assert result == {"github.copilot-chat", "ms-python.python"}

    def test_strips_whitespace(self, temp_dir):
        path = temp_dir / "extensions.txt"
        path.write_text("  golang.go  \n  rust-lang.rust-analyzer\n")
        result = load_extension_file(path)
        assert result == {"golang.go", "rust-lang.rust-analyzer"}

    def test_missing_file_returns_empty(self, temp_dir):
        result = load_extension_file(temp_dir / "nonexistent.txt")
        assert result == set()

    def test_empty_file_returns_empty(self, temp_dir):
        path = temp_dir / "extensions.txt"
        path.write_text("")
        result = load_extension_file(path)
        assert result == set()

    def test_comments_only_file(self, temp_dir):
        path = temp_dir / "extensions.txt"
        path.write_text("# Only comments\n# Nothing else\n")
        result = load_extension_file(path)
        assert result == set()

    def test_unreadable_file_returns_empty(self, temp_dir):
        path = temp_dir / "extensions.txt"
        path.write_text("golang.go\n")
        path.chmod(0o000)
        result = load_extension_file(path)
        assert result == set()
        path.chmod(0o644)


@pytest.mark.unit
class TestExtensionDiff:
    """Tests for compute_diff."""

    def setup_method(self):
        self.manager = ExtensionManager()

    def test_all_synced(self):
        desired = {"golang.go", "rust-lang.rust-analyzer"}
        installed = {"golang.go", "rust-lang.rust-analyzer"}
        diff = self.manager.compute_diff(desired, installed)
        assert diff.missing == frozenset()
        assert diff.extra == frozenset()
        assert diff.matched == desired

    def test_missing_extensions(self):
        desired = {"golang.go", "rust-lang.rust-analyzer"}
        installed = {"golang.go"}
        diff = self.manager.compute_diff(desired, installed)
        assert diff.missing == frozenset({"rust-lang.rust-analyzer"})
        assert diff.extra == frozenset()

    def test_extra_extensions(self):
        desired = {"golang.go"}
        installed = {"golang.go", "some.extra-ext"}
        diff = self.manager.compute_diff(desired, installed)
        assert diff.extra == frozenset({"some.extra-ext"})
        assert diff.missing == frozenset()

    def test_both_missing_and_extra(self):
        desired = {"golang.go", "hashicorp.terraform"}
        installed = {"golang.go", "some.extra-ext"}
        diff = self.manager.compute_diff(desired, installed)
        assert diff.missing == frozenset({"hashicorp.terraform"})
        assert diff.extra == frozenset({"some.extra-ext"})
        assert diff.matched == frozenset({"golang.go"})

    def test_builtin_extensions_excluded_from_extra(self):
        desired = {"golang.go"}
        installed = {"golang.go", "anysphere.cursorpyright"}
        diff = self.manager.compute_diff(desired, installed, shell_name="cursor")
        assert diff.extra == frozenset()
        assert diff.ignored == frozenset()

    def test_pylance_excluded_from_cursor_extra(self):
        desired = {"golang.go"}
        installed = {"golang.go", "ms-python.vscode-pylance"}
        diff = self.manager.compute_diff(desired, installed, shell_name="cursor")
        assert "ms-python.vscode-pylance" not in diff.extra
        assert not diff.extra

    def test_builtin_exclusion_only_for_matching_shell(self):
        desired = {"golang.go"}
        installed = {"golang.go", "anysphere.cursorpyright"}
        diff = self.manager.compute_diff(desired, installed, shell_name="vscode")
        assert "anysphere.cursorpyright" in diff.extra

    def test_builtin_in_desired_is_ignored(self):
        desired = {"golang.go", "github.copilot-chat"}
        installed = {"golang.go"}
        diff = self.manager.compute_diff(desired, installed, shell_name="vscode")
        assert diff.missing == frozenset()
        assert diff.ignored == frozenset({"github.copilot-chat"})
        assert diff.matched == frozenset({"golang.go"})

    def test_builtin_in_desired_and_installed_is_not_counted_as_matched(self):
        desired = {"golang.go", "anysphere.cursorpyright"}
        installed = {"golang.go", "anysphere.cursorpyright"}
        diff = self.manager.compute_diff(desired, installed, shell_name="cursor")
        assert diff.missing == frozenset()
        assert diff.ignored == frozenset({"anysphere.cursorpyright"})
        assert diff.matched == frozenset({"golang.go"})

    def test_empty_desired_and_installed(self):
        diff = self.manager.compute_diff(set(), set())
        assert diff == ExtensionDiff(
            missing=frozenset(), extra=frozenset(), matched=frozenset()
        )


@pytest.mark.unit
class TestLoadDesiredExtensions:
    """Tests for loading and merging extension lists."""

    def test_merges_base_and_ide_specific(self, temp_dir):
        base = temp_dir / "editor" / "extensions.txt"
        base.parent.mkdir(parents=True)
        base.write_text("golang.go\nms-python.python\n")

        ide = temp_dir / "vscode" / "extensions.txt"
        ide.parent.mkdir(parents=True)
        ide.write_text("ms-python.vscode-pylance\n")

        manager = ExtensionManager()
        result = manager.load_desired_extensions("vscode", [base, ide])
        assert result == {"golang.go", "ms-python.python", "ms-python.vscode-pylance"}

    def test_profile_add(self, temp_dir):
        base = temp_dir / "editor" / "extensions.txt"
        base.parent.mkdir(parents=True)
        base.write_text("golang.go\n")

        from shell_configs.profiles.profile import Profile

        profile = Profile(
            name="work",
            extensions={"vscode": {"add": ["ms-vscode.powershell"]}},
        )

        manager = ExtensionManager()
        result = manager.load_desired_extensions("vscode", [base], profile=profile)
        assert "ms-vscode.powershell" in result
        assert "golang.go" in result

    def test_profile_remove(self, temp_dir):
        base = temp_dir / "editor" / "extensions.txt"
        base.parent.mkdir(parents=True)
        base.write_text("golang.go\npersonal.extension\n")

        from shell_configs.profiles.profile import Profile

        profile = Profile(
            name="work",
            extensions={"vscode": {"remove": ["personal.extension"]}},
        )

        manager = ExtensionManager()
        result = manager.load_desired_extensions("vscode", [base], profile=profile)
        assert "personal.extension" not in result
        assert "golang.go" in result

    def test_profile_for_different_shell_ignored(self, temp_dir):
        base = temp_dir / "editor" / "extensions.txt"
        base.parent.mkdir(parents=True)
        base.write_text("golang.go\n")

        from shell_configs.profiles.profile import Profile

        profile = Profile(
            name="work",
            extensions={"cursor": {"add": ["cursor.only-ext"]}},
        )

        manager = ExtensionManager()
        result = manager.load_desired_extensions("vscode", [base], profile=profile)
        assert "cursor.only-ext" not in result

    def test_case_normalization_in_profile(self, temp_dir):
        base = temp_dir / "editor" / "extensions.txt"
        base.parent.mkdir(parents=True)
        base.write_text("golang.go\n")

        from shell_configs.profiles.profile import Profile

        profile = Profile(
            name="work",
            extensions={"vscode": {"add": ["MS-Python.Pylance"]}},
        )

        manager = ExtensionManager()
        result = manager.load_desired_extensions("vscode", [base], profile=profile)
        assert "ms-python.pylance" in result

    def test_no_extension_files(self, temp_dir):
        manager = ExtensionManager()
        result = manager.load_desired_extensions("vscode", [])
        assert result == set()


@pytest.mark.unit
class TestGetInstalledExtensions:
    """Tests for querying installed extensions via CLI."""

    def test_parses_cli_output(self):
        mock_result = type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "golang.go\nRust-Lang.Rust-Analyzer\nms-python.python\n",
                "stderr": "",
            },
        )()

        manager = ExtensionManager()
        with patch("shell_configs.extensions.subprocess.run", return_value=mock_result):
            result = manager.get_installed_extensions("code")

        assert result == {"golang.go", "rust-lang.rust-analyzer", "ms-python.python"}

    def test_cli_not_found_returns_none(self):
        manager = ExtensionManager()
        with patch(
            "shell_configs.extensions.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = manager.get_installed_extensions("nonexistent")
        assert result is None

    def test_cli_failure_returns_none(self):
        mock_result = type(
            "Result",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "error",
            },
        )()

        manager = ExtensionManager()
        with patch("shell_configs.extensions.subprocess.run", return_value=mock_result):
            result = manager.get_installed_extensions("code")
        assert result is None

    def test_cli_timeout_returns_none(self):
        manager = ExtensionManager()
        with patch(
            "shell_configs.extensions.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="code", timeout=30),
        ):
            result = manager.get_installed_extensions("code")
        assert result is None


@pytest.mark.unit
class TestLoadExtensionsJson:
    def test_parses_extension_ids(self, temp_dir):
        path = temp_dir / "extensions.json"
        path.write_text(
            json.dumps(
                [
                    {"identifier": {"id": "golang.go"}, "version": "0.52.2"},
                    {
                        "identifier": {"id": "rust-lang.rust-analyzer"},
                        "version": "0.3.2",
                    },
                ]
            )
        )
        result = load_extensions_json(path)
        assert result == {"golang.go", "rust-lang.rust-analyzer"}

    def test_returns_none_when_file_missing(self, temp_dir):
        result = load_extensions_json(temp_dir / "nonexistent.json")
        assert result is None

    def test_returns_none_on_invalid_json(self, temp_dir):
        path = temp_dir / "extensions.json"
        path.write_text("not valid json{{{")
        result = load_extensions_json(path)
        assert result is None

    def test_skips_entries_without_identifier(self, temp_dir):
        path = temp_dir / "extensions.json"
        path.write_text(
            json.dumps(
                [
                    {"identifier": {"id": "golang.go"}},
                    {"version": "1.0"},
                    {"identifier": {}},
                ]
            )
        )
        result = load_extensions_json(path)
        assert result == {"golang.go"}

    def test_normalizes_to_lowercase(self, temp_dir):
        path = temp_dir / "extensions.json"
        path.write_text(
            json.dumps(
                [
                    {"identifier": {"id": "GitHub.Copilot-Chat"}},
                ]
            )
        )
        result = load_extensions_json(path)
        assert result == {"github.copilot-chat"}

    def test_empty_array_returns_empty_set(self, temp_dir):
        path = temp_dir / "extensions.json"
        path.write_text("[]")
        result = load_extensions_json(path)
        assert result == set()


@pytest.mark.unit
class TestGetInstalledExtensionsFallback:
    def test_cli_success_ignores_filesystem(self, temp_dir):
        mock_result = type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "golang.go\nrust-lang.rust-analyzer\n",
                "stderr": "",
            },
        )()
        fs_path = temp_dir / "extensions.json"
        fs_path.write_text(
            json.dumps(
                [
                    {"identifier": {"id": "different.extension"}},
                ]
            )
        )
        manager = ExtensionManager()
        with patch("shell_configs.extensions.subprocess.run", return_value=mock_result):
            result = manager.get_installed_extensions(
                "code", extensions_json_path=fs_path
            )
        assert result == {"golang.go", "rust-lang.rust-analyzer"}

    def test_cli_empty_falls_back_to_filesystem(self, temp_dir):
        mock_result = type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "Message {}\n",
                "stderr": "",
            },
        )()
        fs_path = temp_dir / "extensions.json"
        fs_path.write_text(
            json.dumps(
                [
                    {"identifier": {"id": "golang.go"}},
                    {"identifier": {"id": "rust-lang.rust-analyzer"}},
                ]
            )
        )
        manager = ExtensionManager()
        with patch("shell_configs.extensions.subprocess.run", return_value=mock_result):
            result = manager.get_installed_extensions(
                "code", extensions_json_path=fs_path
            )
        assert result == {"golang.go", "rust-lang.rust-analyzer"}

    def test_cli_failure_falls_back_to_filesystem(self, temp_dir):
        fs_path = temp_dir / "extensions.json"
        fs_path.write_text(
            json.dumps(
                [
                    {"identifier": {"id": "golang.go"}},
                ]
            )
        )
        manager = ExtensionManager()
        with patch(
            "shell_configs.extensions.subprocess.run", side_effect=FileNotFoundError
        ):
            result = manager.get_installed_extensions(
                "code", extensions_json_path=fs_path
            )
        assert result == {"golang.go"}

    def test_no_cli_no_path_returns_none(self):
        manager = ExtensionManager()
        result = manager.get_installed_extensions(None)
        assert result is None

    def test_cli_empty_no_fallback_returns_empty_set(self):
        mock_result = type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "Message {}\n",
                "stderr": "",
            },
        )()
        manager = ExtensionManager()
        with patch("shell_configs.extensions.subprocess.run", return_value=mock_result):
            result = manager.get_installed_extensions("code")
        assert result == set()


@pytest.mark.unit
class TestInstallExtensions:
    """Tests for extension install/uninstall operations."""

    def test_install_dry_run(self):
        manager = ExtensionManager()
        results = manager.install_extensions(
            "code", {"golang.go", "rust-lang.rust-analyzer"}, dry_run=True
        )
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all("Would install" in r.message for r in results)

    def test_install_calls_cli(self):
        mock_result = type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "Extension installed\n",
                "stderr": "",
            },
        )()

        manager = ExtensionManager()
        with patch(
            "shell_configs.extensions.subprocess.run", return_value=mock_result
        ) as mock_run:
            results = manager.install_extensions("code", {"golang.go"})

        assert len(results) == 1
        assert results[0].success
        mock_run.assert_called_once_with(
            ["code", "--install-extension", "golang.go", "--force"],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_install_continues_on_failure(self):
        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return type(
                    "Result",
                    (),
                    {
                        "returncode": 1,
                        "stdout": "",
                        "stderr": "Not found",
                    },
                )()
            return type(
                "Result",
                (),
                {
                    "returncode": 0,
                    "stdout": "OK",
                    "stderr": "",
                },
            )()

        manager = ExtensionManager()
        with patch("shell_configs.extensions.subprocess.run", side_effect=mock_run):
            results = manager.install_extensions("code", {"aaa.first", "zzz.second"})

        assert len(results) == 2
        assert not results[0].success
        assert results[1].success

    def test_builtin_install_error_is_skipped(self):
        mock_result = type(
            "Result",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": (
                    "Error while installing extension github.copilot-chat: "
                    "Extension 'github.copilot-chat' is a built-in extension"
                ),
            },
        )()

        manager = ExtensionManager()
        with patch("shell_configs.extensions.subprocess.run", return_value=mock_result):
            results = manager.install_extensions("code", {"github.copilot-chat"})

        assert len(results) == 1
        assert results[0].success
        assert results[0].status == ExtensionResultStatus.SKIPPED_BUILTIN

    def test_uninstall_dry_run(self):
        manager = ExtensionManager()
        results = manager.uninstall_extensions("code", {"golang.go"}, dry_run=True)
        assert len(results) == 1
        assert results[0].success
        assert "Would uninstall" in results[0].message


@pytest.mark.unit
class TestProfileExtensionInheritance:
    """Tests for extension overrides in profile inheritance."""

    def _make_loader(self, temp_dir: Path, profiles: dict[str, Any]) -> "ProfileLoader":
        import yaml

        from shell_configs.profiles.loader import ProfileLoader

        profiles_dir = temp_dir / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        for name, data in profiles.items():
            (profiles_dir / f"{name}.yaml").write_text(yaml.dump(data))
        return ProfileLoader(temp_dir)

    def test_extension_overrides_inherited(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "extensions": {
                        "vscode": {"add": ["base.ext"]},
                    },
                },
                "work": {
                    "name": "work",
                    "extends": "default",
                    "extensions": {
                        "vscode": {"add": ["work.ext"]},
                    },
                },
            },
        )
        p = loader.resolve_profile("work")
        assert "base.ext" in p.extensions["vscode"]["add"]
        assert "work.ext" in p.extensions["vscode"]["add"]

    def test_child_remove_wins_over_parent_add(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "extensions": {
                        "vscode": {"add": ["personal.ext", "shared.ext"]},
                    },
                },
                "work": {
                    "name": "work",
                    "extends": "default",
                    "extensions": {
                        "vscode": {"remove": ["personal.ext"]},
                    },
                },
            },
        )
        p = loader.resolve_profile("work")
        assert "personal.ext" not in p.extensions["vscode"].get("add", [])
        assert "personal.ext" in p.extensions["vscode"]["remove"]
        assert "shared.ext" in p.extensions["vscode"]["add"]

    def test_multiple_shells_merged_independently(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "extensions": {
                        "vscode": {"add": ["vscode.ext"]},
                        "cursor": {"add": ["cursor.ext"]},
                    },
                },
                "work": {
                    "name": "work",
                    "extends": "default",
                    "extensions": {
                        "vscode": {"add": ["work-vscode.ext"]},
                    },
                },
            },
        )
        p = loader.resolve_profile("work")
        assert "vscode.ext" in p.extensions["vscode"]["add"]
        assert "work-vscode.ext" in p.extensions["vscode"]["add"]
        assert "cursor.ext" in p.extensions["cursor"]["add"]

    def test_case_normalized_during_merge(self, temp_dir):
        loader = self._make_loader(
            temp_dir,
            {
                "default": {
                    "name": "default",
                    "extensions": {
                        "vscode": {"remove": ["Personal.Ext"]},
                    },
                },
                "work": {
                    "name": "work",
                    "extends": "default",
                    "extensions": {
                        "vscode": {"add": ["personal.ext", "other.ext"]},
                    },
                },
            },
        )
        p = loader.resolve_profile("work")
        assert "personal.ext" not in p.extensions["vscode"].get("add", [])
        assert "other.ext" in p.extensions["vscode"]["add"]
