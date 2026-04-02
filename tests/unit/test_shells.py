"""Unit tests for shell implementations."""

import json

import pytest

from shell_configs.shells import BashShell, GitShell, ShellRegistry, ZshShell
from shell_configs.shells.base import merge_json_files
from shell_configs.shells.cursor import CursorShell
from shell_configs.shells.vscode import VSCodeShell


@pytest.mark.unit
class TestBashShell:
    """Test the BashShell class."""

    def test_validate_syntax_valid(self):
        shell = BashShell()
        valid_script = "echo 'hello'\nalias test='echo test'\n"

        is_valid, message = shell.validate_syntax(valid_script)

        assert is_valid

    def test_validate_syntax_invalid(self):
        shell = BashShell()
        invalid_script = "if [ -f file\necho 'missing fi'\n"

        is_valid, message = shell.validate_syntax(invalid_script)

        assert not is_valid
        assert message != ""

    def test_get_additional_files(self, temp_dir, monkeypatch):
        shell = BashShell()

        config_dir = temp_dir / "config"
        config_dir.mkdir()

        bash_config_dir = config_dir / "bash"
        bash_config_dir.mkdir(parents=True)

        shared_scripts_dir = config_dir / "shared-scripts"
        shared_scripts_dir.mkdir(parents=True)

        (bash_config_dir / "bashrc").write_text("# bash config")

        (bash_config_dir / "bash-helper.sh").write_text("# bash helper")
        (shared_scripts_dir / "git-prompt.sh").write_text("# git prompt")

        monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)
        additional_files = shell.get_additional_files()

        assert len(additional_files) == 2

        bash_helper = next(
            (f for f in additional_files if f.name == "bash-helper.sh"), None
        )
        assert bash_helper is not None
        assert bash_helper.source_path == bash_config_dir / "bash-helper.sh"
        assert bash_helper.target_path.name == "bash-helper.sh"
        assert ".bash" in str(bash_helper.target_path)

        git_prompt = next(
            (f for f in additional_files if f.name == "git-prompt.sh"), None
        )
        assert git_prompt is not None
        assert git_prompt.source_path == shared_scripts_dir / "git-prompt.sh"
        assert git_prompt.target_path.name == "git-prompt.sh"
        assert ".bash" in str(git_prompt.target_path)


@pytest.mark.unit
class TestZshShell:
    """Test the ZshShell class."""

    def test_validate_syntax_valid(self):
        shell = ZshShell()
        valid_script = "echo 'hello'\nalias test='echo test'\n"

        is_valid, message = shell.validate_syntax(valid_script)

        if "Command not found" in message:
            pytest.skip("zsh not installed")
        assert is_valid

    def test_get_additional_files(self, temp_dir, monkeypatch):
        shell = ZshShell()

        config_dir = temp_dir / "config"
        config_dir.mkdir()

        zsh_config_dir = config_dir / "zsh"
        zsh_config_dir.mkdir(parents=True)

        shared_scripts_dir = config_dir / "shared-scripts"
        shared_scripts_dir.mkdir(parents=True)

        (zsh_config_dir / "zshrc").write_text("# zsh config")

        (zsh_config_dir / "zsh-helper.sh").write_text("# zsh helper")
        (shared_scripts_dir / "git-prompt.sh").write_text("# git prompt")

        monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)
        additional_files = shell.get_additional_files()

        assert len(additional_files) == 2

        zsh_helper = next(
            (f for f in additional_files if f.name == "zsh-helper.sh"), None
        )
        assert zsh_helper is not None
        assert zsh_helper.source_path == zsh_config_dir / "zsh-helper.sh"
        assert zsh_helper.target_path.name == "zsh-helper.sh"
        assert ".zsh" in str(zsh_helper.target_path)

        git_prompt = next(
            (f for f in additional_files if f.name == "git-prompt.sh"), None
        )
        assert git_prompt is not None
        assert git_prompt.source_path == shared_scripts_dir / "git-prompt.sh"
        assert git_prompt.target_path.name == "git-prompt.sh"
        assert ".zsh" in str(git_prompt.target_path)


@pytest.mark.unit
class TestGitShell:
    """Test the GitShell class."""

    def test_validate_syntax_valid(self):
        shell = GitShell()
        valid_config = "[user]\n    name = Test User\n    email = test@example.com\n"

        is_valid, message = shell.validate_syntax(valid_config)

        assert is_valid

    def test_validate_syntax_invalid(self):
        shell = GitShell()
        invalid_config = "[user\nname = Test User\n"

        is_valid, message = shell.validate_syntax(invalid_config)

        assert not is_valid
        assert message != ""

    def test_get_additional_files(self, temp_dir, monkeypatch):
        shell = GitShell()

        config_dir = temp_dir / "config"
        config_dir.mkdir()

        git_config_dir = config_dir / "git"
        git_config_dir.mkdir(parents=True)

        (git_config_dir / "ignore").write_text("# global gitignore")
        (git_config_dir / "attributes").write_text("# git attributes")

        monkeypatch.setattr("shell_configs.config.get_config_dir", lambda: config_dir)
        additional_files = shell.get_additional_files()

        assert len(additional_files) == 2

        ignore_file = next((f for f in additional_files if f.name == "ignore"), None)
        assert ignore_file is not None
        assert ignore_file.source_path == git_config_dir / "ignore"
        assert ignore_file.target_path.name == "ignore"
        assert ".config/git" in str(ignore_file.target_path)

        attributes_file = next(
            (f for f in additional_files if f.name == "attributes"), None
        )
        assert attributes_file is not None
        assert attributes_file.source_path == git_config_dir / "attributes"
        assert attributes_file.target_path.name == "attributes"
        assert ".config/git" in str(attributes_file.target_path)


@pytest.mark.unit
class TestShellRegistry:
    """Test the ShellRegistry class."""

    @pytest.mark.parametrize(
        "input_names,expected_shell_count,expected_invalid",
        [
            (["bash", "zsh"], 2, []),
            (["bash", "invalid", "zsh"], 2, ["invalid"]),
            (["invalid1", "invalid2"], 0, ["invalid1", "invalid2"]),
        ],
    )
    def test_filter_by_names(self, input_names, expected_shell_count, expected_invalid):
        registry = ShellRegistry()
        shells, invalid = registry.filter_by_names(input_names)

        assert len(shells) == expected_shell_count
        assert set(invalid) == set(expected_invalid)
        if expected_shell_count > 0:
            valid_names = [name for name in input_names if name not in expected_invalid]
            assert {s.name for s in shells} == set(valid_names)


@pytest.mark.unit
class TestMergeJsonFiles:
    """Test merge_json_files shallow merge behavior."""

    def test_merge_base_with_empty_override(self, temp_dir):
        base = temp_dir / "base.json"
        override = temp_dir / "override.json"
        base.write_text('{"a": 1, "b": 2}')
        override.write_text("{}")

        result = json.loads(merge_json_files(base, override))

        assert result == {"a": 1, "b": 2}

    def test_override_keys_win(self, temp_dir):
        base = temp_dir / "base.json"
        override = temp_dir / "override.json"
        base.write_text('{"theme": "dark", "font": 14}')
        override.write_text('{"theme": "light"}')

        result = json.loads(merge_json_files(base, override))

        assert result["theme"] == "light"
        assert result["font"] == 14

    def test_override_adds_new_keys(self, temp_dir):
        base = temp_dir / "base.json"
        override = temp_dir / "override.json"
        base.write_text('{"shared": true}')
        override.write_text('{"cursor.specific": false}')

        result = json.loads(merge_json_files(base, override))

        assert result == {"shared": True, "cursor.specific": False}

    def test_output_ends_with_newline(self, temp_dir):
        base = temp_dir / "base.json"
        override = temp_dir / "override.json"
        base.write_text('{"a": 1}')
        override.write_text("{}")

        result = merge_json_files(base, override)

        assert result.endswith("\n")

    def test_output_is_valid_json(self, temp_dir):
        base = temp_dir / "base.json"
        override = temp_dir / "override.json"
        base.write_text('{"nested": {"a": 1}, "list": [1, 2]}')
        override.write_text('{"extra": "value"}')

        result = merge_json_files(base, override)

        parsed = json.loads(result)
        assert parsed["nested"] == {"a": 1}
        assert parsed["list"] == [1, 2]
        assert parsed["extra"] == "value"


@pytest.mark.unit
class TestVSCodeShell:
    """Test VSCodeShell additional files configuration."""

    def test_settings_has_base_source_path(self, temp_dir, monkeypatch):
        shell = VSCodeShell()
        config_dir = temp_dir / "config"
        (config_dir / "editor").mkdir(parents=True)
        (config_dir / "vscode").mkdir(parents=True)
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_config_dir", lambda: config_dir
        )

        files = shell.get_additional_files()
        settings = next(f for f in files if f.name == "settings.json")

        assert settings.base_source_path == config_dir / "editor" / "settings.json"

    def test_keybindings_uses_shared_editor_source(self, temp_dir, monkeypatch):
        shell = VSCodeShell()
        config_dir = temp_dir / "config"
        (config_dir / "editor").mkdir(parents=True)
        (config_dir / "vscode").mkdir(parents=True)
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_config_dir", lambda: config_dir
        )

        files = shell.get_additional_files()
        keybindings = next(f for f in files if f.name == "keybindings.json")

        assert keybindings.source_path == config_dir / "editor" / "keybindings.json"
        assert keybindings.base_source_path is None


@pytest.mark.unit
class TestCursorShell:
    """Test CursorShell additional files configuration."""

    def test_settings_has_base_source_path(self, temp_dir, monkeypatch):
        shell = CursorShell()
        config_dir = temp_dir / "config"
        (config_dir / "editor").mkdir(parents=True)
        (config_dir / "cursor").mkdir(parents=True)
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_config_dir", lambda: config_dir
        )

        files = shell.get_additional_files()
        settings = next(f for f in files if f.name == "settings.json")

        assert settings.base_source_path == config_dir / "editor" / "settings.json"

    def test_keybindings_uses_shared_editor_source(self, temp_dir, monkeypatch):
        shell = CursorShell()
        config_dir = temp_dir / "config"
        (config_dir / "editor").mkdir(parents=True)
        (config_dir / "cursor").mkdir(parents=True)
        monkeypatch.setattr(
            "shell_configs.shells.cursor.get_config_dir", lambda: config_dir
        )

        files = shell.get_additional_files()
        keybindings = next(f for f in files if f.name == "keybindings.json")

        assert keybindings.source_path == config_dir / "editor" / "keybindings.json"
        assert keybindings.base_source_path is None
