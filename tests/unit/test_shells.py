"""Unit tests for shell implementations."""

import pytest

from shell_configs.shells import BashShell, GitShell, ShellRegistry, ZshShell


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

    def test_get_additional_files(self, temp_dir):
        shell = BashShell()

        bash_config_dir = temp_dir / "config" / "bash"
        bash_config_dir.mkdir(parents=True)

        shared_scripts_dir = temp_dir / "config" / "shared-scripts"
        shared_scripts_dir.mkdir(parents=True)

        (bash_config_dir / "bashrc").write_text("# bash config")

        (bash_config_dir / "bash-helper.sh").write_text("# bash helper")
        (shared_scripts_dir / "git-prompt.sh").write_text("# git prompt")

        additional_files = shell.get_additional_files(temp_dir)

        assert len(additional_files) == 2

        bash_helper = next((f for f in additional_files if f.name == "bash-helper.sh"), None)
        assert bash_helper is not None
        assert bash_helper.source_path == bash_config_dir / "bash-helper.sh"
        assert bash_helper.target_path.name == "bash-helper.sh"
        assert ".bash" in str(bash_helper.target_path)

        git_prompt = next((f for f in additional_files if f.name == "git-prompt.sh"), None)
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

    def test_get_additional_files(self, temp_dir):
        shell = ZshShell()

        zsh_config_dir = temp_dir / "config" / "zsh"
        zsh_config_dir.mkdir(parents=True)

        shared_scripts_dir = temp_dir / "config" / "shared-scripts"
        shared_scripts_dir.mkdir(parents=True)

        (zsh_config_dir / "zshrc").write_text("# zsh config")

        (zsh_config_dir / "zsh-helper.sh").write_text("# zsh helper")
        (shared_scripts_dir / "git-prompt.sh").write_text("# git prompt")

        additional_files = shell.get_additional_files(temp_dir)

        assert len(additional_files) == 2

        zsh_helper = next((f for f in additional_files if f.name == "zsh-helper.sh"), None)
        assert zsh_helper is not None
        assert zsh_helper.source_path == zsh_config_dir / "zsh-helper.sh"
        assert zsh_helper.target_path.name == "zsh-helper.sh"
        assert ".zsh" in str(zsh_helper.target_path)

        git_prompt = next((f for f in additional_files if f.name == "git-prompt.sh"), None)
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

    def test_get_additional_files(self, temp_dir):
        shell = GitShell()

        git_config_dir = temp_dir / "config" / "git"
        git_config_dir.mkdir(parents=True)

        (git_config_dir / "ignore").write_text("# global gitignore")
        (git_config_dir / "attributes").write_text("# git attributes")

        additional_files = shell.get_additional_files(temp_dir)

        assert len(additional_files) == 2

        ignore_file = next((f for f in additional_files if f.name == "ignore"), None)
        assert ignore_file is not None
        assert ignore_file.source_path == git_config_dir / "ignore"
        assert ignore_file.target_path.name == "ignore"
        assert ".config/git" in str(ignore_file.target_path)

        attributes_file = next((f for f in additional_files if f.name == "attributes"), None)
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
