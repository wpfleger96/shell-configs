"""Tests for iTerm2 configuration handler."""

import json
import plistlib

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from shell_configs.platform import Platform
from shell_configs.shells.iterm2 import (
    ITERM2_DIFF_FORMATTERS,
    ITERM2_PREFERENCES_DOMAIN,
    ITerm2Shell,
    diff_global_key_map,
)


class TestITerm2ShellMacOS:
    """Test ITerm2Shell behavior on macOS."""

    @pytest.fixture(autouse=True)
    def setup_macos(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.iterm2.is_platform",
            lambda p: p == Platform.MACOS,
        )

    def test_get_config_files_empty(self):
        shell = ITerm2Shell()
        assert shell.get_config_files() == []

    @pytest.mark.unit
    def test_get_additional_files_returns_profile(self, mock_home):
        shell = ITerm2Shell()
        files = shell.get_additional_files()

        assert len(files) == 1
        assert files[0].name == "shell-configs.json"
        assert files[0].source_path.name == "profile.json"
        assert "DynamicProfiles" in str(files[0].target_path)
        assert files[0].target_path.name == "shell-configs.json"

    @pytest.mark.unit
    def test_get_preferences_files_returns_preferences(self):
        shell = ITerm2Shell()
        files = shell.get_preferences_files()

        assert len(files) == 1
        assert files[0].name == "iTerm2 Preferences"
        assert files[0].source_path.name == "preferences.json"
        assert files[0].domain == ITERM2_PREFERENCES_DOMAIN

    @pytest.mark.unit
    def test_validation_command_uses_json_tool(self):
        shell = ITerm2Shell()
        cmd = shell._get_validation_command(Path("/tmp/test.json"))
        assert cmd == ["python3", "-m", "json.tool", "/tmp/test.json"]


class TestITerm2ShellNonMacOS:
    """Test ITerm2Shell is a no-op on non-macOS platforms."""

    @pytest.mark.unit
    def test_additional_files_empty_on_linux(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.iterm2.is_platform",
            lambda p: p == Platform.LINUX,
        )
        shell = ITerm2Shell()
        assert shell.get_additional_files() == []

    @pytest.mark.unit
    def test_preferences_files_empty_on_linux(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.iterm2.is_platform",
            lambda p: p == Platform.LINUX,
        )
        shell = ITerm2Shell()
        assert shell.get_preferences_files() == []


class TestITerm2Registry:
    """Test ITerm2Shell is registered."""

    @pytest.mark.unit
    def test_iterm2_registered_on_macos(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.MACOS,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        shell = registry.get("iterm2")
        assert shell is not None
        assert isinstance(shell, ITerm2Shell)

    @pytest.mark.unit
    def test_iterm2_not_registered_on_linux(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("iterm2") is None


class TestConfigManagerPreferences:
    """Test ConfigManager preferences methods."""

    @pytest.fixture
    def manager(self):
        from shell_configs.manager import ConfigManager

        return ConfigManager()

    @pytest.fixture
    def prefs_file(self, tmp_path):
        prefs = {
            "AllowClipboardAccess": True,
            "PromptOnQuit": False,
            "TabStyleWithAutomaticOption": 4,
        }
        path = tmp_path / "preferences.json"
        path.write_text(json.dumps(prefs))
        return path

    @pytest.fixture
    def mock_subprocess(self, monkeypatch):
        """Returns a factory to control defaults command behavior."""

        def setup(domain_data=None, import_ok=True):
            def fake_run(cmd, **kwargs):
                result = MagicMock()
                if cmd[0] == "defaults" and cmd[1] == "export":
                    if domain_data is not None:
                        result.returncode = 0
                        result.stdout = plistlib.dumps(domain_data)
                    else:
                        result.returncode = 1
                        result.stdout = b""
                elif cmd[0] == "defaults" and cmd[1] == "import":
                    result.returncode = 0 if import_ok else 1
                    result.stderr = "" if import_ok else "import failed"
                elif cmd[0] == "defaults" and cmd[1] == "delete":
                    result.returncode = 0
                elif cmd[0] == "pgrep":
                    result.returncode = 1
                else:
                    result.returncode = 0
                return result

            monkeypatch.setattr("shell_configs.manager.core.subprocess.run", fake_run)

        return setup

    @pytest.mark.unit
    def test_install_already_synced(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": False,
                "TabStyleWithAutomaticOption": 4,
                "SomeOtherKey": "unmanaged",
            }
        )

        from shell_configs.manager import OperationResult

        result, message, diff = manager.install_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert result == OperationResult.ALREADY_SYNCED

    @pytest.mark.unit
    def test_install_creates_new(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(domain_data=None)

        from shell_configs.manager import OperationResult

        result, message, diff = manager.install_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert result == OperationResult.CREATED
        assert "3 preference(s)" in message

    @pytest.mark.unit
    def test_install_updates_existing(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": True,
                "TabStyleWithAutomaticOption": 3,
            }
        )

        from shell_configs.manager import OperationResult

        result, message, diff = manager.install_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert result == OperationResult.UPDATED
        assert diff is not None
        assert "PromptOnQuit" in diff
        assert "TabStyleWithAutomaticOption" in diff

    @pytest.mark.unit
    def test_install_update_counts_only_changed_keys(
        self, manager, prefs_file, mock_subprocess
    ):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": True,
                "TabStyleWithAutomaticOption": 4,
            }
        )

        result, message, diff = manager.install_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert message == "Updated 1 of 3 preference(s) in com.test.domain"
        assert diff == "  ~ PromptOnQuit: True → False"

    @pytest.mark.unit
    def test_install_nested_dict_diff_shows_changed_leaves(
        self, manager, tmp_path, mock_subprocess
    ):
        expected = {
            "GlobalKeyMap": {
                "0x54-0x120000-0x11": {"Action": 61, "Text": "x"},
                "0xd-0x20000-0x24": {"Action": 12, "Text": "\\n"},
                "0x4e-0x120000-0x2d": {"Action": 25},
            },
            "PromptOnQuit": False,
        }
        prefs = tmp_path / "preferences.json"
        prefs.write_text(json.dumps(expected))
        mock_subprocess(
            domain_data={
                "GlobalKeyMap": {
                    "0x54-0x120000-0x11": {"Action": 61, "Text": ""},
                    "0xd-0x20000-0x24": {"Action": 12, "Text": "\\n"},
                    "0x99-0x0-0x0": {"Action": 1},
                },
                "PromptOnQuit": False,
            }
        )

        result, message, diff = manager.install_preferences_file(
            prefs, "com.test.domain"
        )
        assert message == "Updated 1 of 2 preference(s) in com.test.domain"
        assert diff == "\n".join(
            [
                "  + GlobalKeyMap.0x4e-0x120000-0x2d.Action: 25",
                '  ~ GlobalKeyMap.0x54-0x120000-0x11.Text: "" → "x"',
                "  - GlobalKeyMap.0x99-0x0-0x0.Action: 1",
            ]
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("current", "expected", "sign"),
        [
            ({}, {"0x54": {"Action": 12, "Text": "x"}}, "+"),
            ({"0x54": {"Action": 12, "Text": "x"}}, {}, "-"),
        ],
    )
    def test_install_added_or_removed_binding_shows_its_leaves(
        self, manager, tmp_path, mock_subprocess, current, expected, sign
    ):
        prefs = tmp_path / "preferences.json"
        prefs.write_text(json.dumps({"GlobalKeyMap": expected}))
        mock_subprocess(domain_data={"GlobalKeyMap": current})

        _, _, diff = manager.install_preferences_file(prefs, "com.test.domain")
        assert diff == "\n".join(
            [
                f"  {sign} GlobalKeyMap.0x54.Action: 12",
                f'  {sign} GlobalKeyMap.0x54.Text: "x"',
            ]
        )

    @pytest.mark.unit
    def test_install_added_empty_dict_keeps_marker(
        self, manager, tmp_path, mock_subprocess
    ):
        prefs = tmp_path / "preferences.json"
        prefs.write_text(json.dumps({"Map": {"a": 1, "b": {}}}))
        mock_subprocess(domain_data={"Map": {"a": 1}})

        _, _, diff = manager.install_preferences_file(prefs, "com.test.domain")
        assert diff == "  + Map.b: <dict with 0 key(s)>"

    @pytest.mark.unit
    def test_install_key_containing_dot_is_quoted(
        self, manager, tmp_path, mock_subprocess
    ):
        prefs = tmp_path / "preferences.json"
        prefs.write_text(json.dumps({"Map": {"a.b": 2, "a": {"b": 2}}}))
        mock_subprocess(domain_data={"Map": {"a.b": 1, "a": {"b": 1}}})

        _, _, diff = manager.install_preferences_file(prefs, "com.test.domain")
        assert diff == '  ~ Map.a.b: 1 → 2\n  ~ Map."a.b": 1 → 2'

    @pytest.mark.unit
    def test_install_type_change_from_dict_is_a_single_line(
        self, manager, tmp_path, mock_subprocess
    ):
        prefs = tmp_path / "preferences.json"
        prefs.write_text(json.dumps({"Map": {"a": 1}}))
        mock_subprocess(domain_data={"Map": "flat"})

        _, _, diff = manager.install_preferences_file(prefs, "com.test.domain")
        assert diff == '  ~ Map: "flat" → <dict with 1 key(s)>'

    @pytest.mark.unit
    def test_install_force_with_nothing_changed_keeps_total_count(
        self, manager, prefs_file, mock_subprocess
    ):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": False,
                "TabStyleWithAutomaticOption": 4,
            }
        )

        _, message, diff = manager.install_preferences_file(
            prefs_file, "com.test.domain", force=True
        )
        assert message == "Updated 3 preference(s) in com.test.domain"
        assert diff is None

    @pytest.mark.unit
    def test_install_dry_run(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(domain_data={"AllowClipboardAccess": False})

        from shell_configs.manager import OperationResult

        result, message, diff = manager.install_preferences_file(
            prefs_file, "com.test.domain", dry_run=True
        )
        assert result == OperationResult.UPDATED
        assert "Would update" in message

    @pytest.mark.unit
    def test_uninstall_deletes_keys(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": False,
                "TabStyleWithAutomaticOption": 4,
            }
        )

        from shell_configs.manager import OperationResult

        result, message = manager.uninstall_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert result == OperationResult.REMOVED
        assert "3 preference(s)" in message

    @pytest.mark.unit
    def test_uninstall_domain_not_found(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(domain_data=None)

        from shell_configs.manager import OperationResult

        result, message = manager.uninstall_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert result == OperationResult.NOT_FOUND

    @pytest.mark.unit
    def test_uninstall_dry_run(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": False,
                "TabStyleWithAutomaticOption": 4,
            }
        )

        from shell_configs.manager import OperationResult

        result, message = manager.uninstall_preferences_file(
            prefs_file, "com.test.domain", dry_run=True
        )
        assert result == OperationResult.REMOVED
        assert "Would delete" in message

    @pytest.mark.unit
    def test_check_status_synced(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": False,
                "TabStyleWithAutomaticOption": 4,
            }
        )

        exists, synced = manager.check_preferences_file_status(
            prefs_file, "com.test.domain"
        )
        assert exists is True
        assert synced is True

    @pytest.mark.unit
    def test_check_status_outdated(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": True,
                "TabStyleWithAutomaticOption": 4,
            }
        )

        exists, synced = manager.check_preferences_file_status(
            prefs_file, "com.test.domain"
        )
        assert exists is True
        assert synced is False

    @pytest.mark.unit
    def test_check_status_not_installed(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(domain_data=None)

        exists, synced = manager.check_preferences_file_status(
            prefs_file, "com.test.domain"
        )
        assert exists is False
        assert synced is False

    @pytest.mark.unit
    def test_diff_returns_none_when_synced(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": False,
                "TabStyleWithAutomaticOption": 4,
            }
        )

        diff = manager.diff_preferences_file(prefs_file, "com.test.domain")
        assert diff is None

    @pytest.mark.unit
    def test_diff_returns_changes(self, manager, prefs_file, mock_subprocess):
        mock_subprocess(
            domain_data={
                "AllowClipboardAccess": True,
                "PromptOnQuit": True,
            }
        )

        diff = manager.diff_preferences_file(prefs_file, "com.test.domain")
        assert diff is not None
        assert "PromptOnQuit" in diff
        assert "TabStyleWithAutomaticOption" in diff

    @pytest.mark.unit
    def test_install_missing_source_file(self, manager, tmp_path, mock_subprocess):
        mock_subprocess()

        from shell_configs.manager import OperationResult

        result, message, diff = manager.install_preferences_file(
            tmp_path / "nonexistent.json", "com.test.domain"
        )
        assert result == OperationResult.ERROR

    @pytest.mark.unit
    def test_install_rejects_null_values(self, manager, tmp_path, mock_subprocess):
        mock_subprocess()
        prefs_file = tmp_path / "prefs_with_null.json"
        prefs_file.write_text(json.dumps({"GoodKey": True, "BadKey": None}))

        from shell_configs.manager import OperationResult

        result, message, diff = manager.install_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert result == OperationResult.ERROR
        assert "BadKey" in message

    @pytest.mark.unit
    def test_uninstall_reports_failed_deletes(self, manager, prefs_file, monkeypatch):
        """Test that uninstall reports keys that failed to delete."""
        call_count = 0

        def fake_run(cmd, **kwargs):
            nonlocal call_count
            from unittest.mock import MagicMock

            m = MagicMock()
            if cmd[0] == "defaults" and cmd[1] == "export":
                import plistlib

                m.returncode = 0
                m.stdout = plistlib.dumps(
                    {
                        "AllowClipboardAccess": True,
                        "PromptOnQuit": False,
                        "TabStyleWithAutomaticOption": 4,
                    }
                )
            elif cmd[0] == "defaults" and cmd[1] == "delete":
                call_count += 1
                m.returncode = 1 if cmd[3] == "PromptOnQuit" else 0
                m.stderr = "failed" if m.returncode else ""
            elif cmd[0] == "pgrep":
                m.returncode = 1
            else:
                m.returncode = 0
            return m

        monkeypatch.setattr("shell_configs.manager.core.subprocess.run", fake_run)

        from shell_configs.manager import OperationResult

        result, message = manager.uninstall_preferences_file(
            prefs_file, "com.test.domain"
        )
        assert result == OperationResult.REMOVED
        assert "1 failed" in message
        assert "PromptOnQuit" in message


_REPO_KEY_MAP = json.loads(
    (
        Path(__file__).parents[2] / "src/shell_configs/config/iterm2/preferences.json"
    ).read_text()
)["GlobalKeyMap"]


class TestGlobalKeyMapDiff:
    """GlobalKeyMap diffs name key combos and actions instead of raw IDs."""

    @pytest.mark.unit
    def test_repo_bindings_render_as_key_combos(self):
        assert diff_global_key_map({}, _REPO_KEY_MAP) == [
            '  + Key binding ⇧⌘N: Select Menu Item "Duplicate Window\\nDuplicate Window"',
            "  + Key binding ⇧⌘T: Duplicate Tab",
            '  + Key binding ⇧Return: Send Text "\\n"',
        ]

    @pytest.mark.unit
    def test_removed_binding_is_one_line(self):
        current = {"0x9-0x40000-0x30": {"Action": 0, "Version": 1}}
        assert diff_global_key_map(current, {}) == ["  - Key binding ⌃Tab: Next Tab"]

    @pytest.mark.unit
    def test_changed_fields_get_one_line_each_and_hide_redundant_fields(self):
        current = {"0x54-0x120000-0x11": {"Action": 12, "Text": "a", "Version": 1}}
        expected = {"0x54-0x120000-0x11": {"Action": 25, "Text": "b", "Version": 2}}
        assert diff_global_key_map(current, expected) == [
            "  ~ Key binding ⇧⌘T: action: Send Text → Select Menu Item",
            '  ~ Key binding ⇧⌘T: text: "a" → "b"',
        ]

    @pytest.mark.unit
    def test_change_only_in_hidden_field_is_still_shown(self):
        current = {"0xd-0x20000-0x24": {"Action": 12, "Version": 1}}
        expected = {"0xd-0x20000-0x24": {"Action": 12, "Version": 2}}
        assert diff_global_key_map(current, expected) == [
            "  ~ Key binding ⇧Return: version: 1 → 2"
        ]

    @pytest.mark.unit
    def test_non_hex_key_and_unknown_action_fall_back(self):
        expected = {
            "custom.key": {"Action": 99},
            "0xf704-0xa00000-0x7a": {"Action": 13},
        }
        assert diff_global_key_map({}, expected) == [
            "  + Key binding F1: Ignore",
            '  + Key binding "custom.key": action 99',
        ]

    @pytest.mark.unit
    def test_install_uses_formatter_for_global_key_map_only(self, tmp_path):
        from shell_configs.manager.core import ConfigManager

        expected = {"GlobalKeyMap": _REPO_KEY_MAP, "PromptOnQuit": False}
        current = {
            "GlobalKeyMap": {
                **{k: v for k, v in _REPO_KEY_MAP.items() if k != "0xd-0x20000-0x24"},
                "0x54-0x120000-0x11": {
                    **_REPO_KEY_MAP["0x54-0x120000-0x11"],
                    "Text": "gurney old value",
                },
                "gurney.extra.binding": {"Action": 12, "Text": "remove me"},
            },
            "PromptOnQuit": True,
        }
        diff = ConfigManager(tmp_path / "rc")._build_preferences_diff(
            expected, current, ITERM2_DIFF_FORMATTERS
        )
        assert diff == "\n".join(
            [
                '  ~ Key binding ⇧⌘T: text: "gurney old value" → ""',
                '  + Key binding ⇧Return: Send Text "\\n"',
                '  - Key binding "gurney.extra.binding": Send Text "remove me"',
                "  ~ PromptOnQuit: True → False",
            ]
        )
