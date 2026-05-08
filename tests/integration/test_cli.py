"""Integration tests for CLI commands."""

import pytest

from shell_configs.cli import cli
from shell_configs.manager import ConfigManager


@pytest.mark.integration
@pytest.mark.cli
class TestInstallCommand:
    """Test the install command."""

    def test_install_all_shells(self, test_repo, mock_home, cli_runner, monkeypatch):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["install", "-y"])

        assert result.exit_code == 0

        manager = ConfigManager()
        bashrc = mock_home / ".bashrc"
        zshrc = mock_home / ".zshrc"
        gitconfig = mock_home / ".gitconfig"

        assert manager.has_managed_section(bashrc)
        assert manager.has_managed_section(zshrc)
        assert manager.has_managed_section(gitconfig)

    def test_install_with_shell_filter(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["install", "--shells", "bash,zsh", "-y"])

        assert result.exit_code == 0

        manager = ConfigManager()
        bashrc = mock_home / ".bashrc"
        zshrc = mock_home / ".zshrc"
        gitconfig = mock_home / ".gitconfig"

        assert manager.has_managed_section(bashrc)
        assert manager.has_managed_section(zshrc)
        assert not manager.has_managed_section(gitconfig)

    def test_install_dry_run(self, test_repo, mock_home, cli_runner, monkeypatch):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["install", "--dry-run"])

        assert result.exit_code == 0
        assert "Would create" in result.output

        bashrc = mock_home / ".bashrc"
        assert not bashrc.exists()


@pytest.mark.integration
@pytest.mark.cli
class TestUninstallCommand:
    """Test the uninstall command."""

    def test_uninstall_all_shells(self, test_repo, mock_home, cli_runner, monkeypatch):
        monkeypatch.chdir(test_repo)

        cli_runner.invoke(cli, ["install", "-y"])
        result = cli_runner.invoke(cli, ["uninstall", "-y"])

        assert result.exit_code == 0

        manager = ConfigManager()
        bashrc = mock_home / ".bashrc"
        zshrc = mock_home / ".zshrc"
        gitconfig = mock_home / ".gitconfig"

        assert not manager.has_managed_section(bashrc)
        assert not manager.has_managed_section(zshrc)
        assert not manager.has_managed_section(gitconfig)

    def test_uninstall_preserves_existing_content(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        bashrc = mock_home / ".bashrc"
        existing_content = "# Existing config\nalias old='echo old'\n"
        bashrc.write_text(existing_content)

        cli_runner.invoke(cli, ["install", "-y"])
        cli_runner.invoke(cli, ["uninstall", "-y"])

        final_content = bashrc.read_text()
        assert "Existing config" in final_content
        assert "alias old" in final_content


@pytest.mark.integration
@pytest.mark.cli
class TestStatusCommand:
    """Test the status command."""

    @pytest.mark.parametrize(
        "scenario,setup_action,expected_output",
        [
            ("not_installed", None, "Not installed"),
            ("synced", "install", "Synced"),
            ("outdated", "install_and_modify", "Outdated"),
        ],
    )
    def test_status_scenarios(
        self,
        test_repo,
        mock_home,
        cli_runner,
        monkeypatch,
        scenario,
        setup_action,
        expected_output,
    ):
        monkeypatch.chdir(test_repo)

        if setup_action == "install":
            cli_runner.invoke(cli, ["install", "-y"])
        elif setup_action == "install_and_modify":
            cli_runner.invoke(cli, ["install", "-y"])
            manager = ConfigManager()
            bashrc = mock_home / ".bashrc"
            manager.install_section(bashrc, "# Different content\n")

        result = cli_runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert expected_output in result.output


@pytest.mark.integration
@pytest.mark.cli
class TestDiffCommand:
    """Test the diff command."""

    @pytest.mark.parametrize(
        "scenario,setup_action,expected_in_output,expected_not_in_output",
        [
            ("not_installed", None, "Not installed", None),
            ("synced", "install", None, "Not installed"),
            ("outdated", "install_and_modify", "Bash", None),
        ],
    )
    def test_diff_scenarios(
        self,
        test_repo,
        mock_home,
        cli_runner,
        monkeypatch,
        scenario,
        setup_action,
        expected_in_output,
        expected_not_in_output,
    ):
        monkeypatch.chdir(test_repo)

        if setup_action == "install":
            cli_runner.invoke(cli, ["install", "-y"])
        elif setup_action == "install_and_modify":
            cli_runner.invoke(cli, ["install", "-y"])
            manager = ConfigManager()
            bashrc = mock_home / ".bashrc"
            manager.install_section(bashrc, "# Different content\n")

        result = cli_runner.invoke(cli, ["diff"])

        assert result.exit_code == 0
        if expected_in_output is not None:
            assert expected_in_output in result.output
        if expected_not_in_output is not None:
            assert expected_not_in_output not in result.output


@pytest.mark.integration
@pytest.mark.cli
class TestValidateCommand:
    """Test the validate command."""

    def test_validate_success(self, test_repo, mock_home, cli_runner, monkeypatch):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["validate", "--shells", "bash,git"])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_specific_shell(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["validate", "--shells", "bash"])

        assert result.exit_code == 0
        assert "Bash" in result.output


@pytest.mark.integration
@pytest.mark.cli
class TestListShellsCommand:
    """Test the list-shells command."""

    def test_list_shells(self, test_repo, cli_runner, monkeypatch):
        monkeypatch.chdir(test_repo)

        result = cli_runner.invoke(cli, ["list-shells"])

        assert result.exit_code == 0
        assert "Bash" in result.output
        assert "Zsh" in result.output
        assert "Git" in result.output


@pytest.mark.integration
@pytest.mark.cli
class TestAdditionalFiles:
    """Test CLI commands with additional files."""

    def test_install_with_additional_files(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        shared_scripts_dir = test_repo / "config" / "shared-scripts"
        shared_scripts_dir.mkdir()
        git_prompt_file = shared_scripts_dir / "git-prompt.sh"
        git_prompt_file.write_text("# Git prompt script")

        bash_helper_file = test_repo / "config" / "bash" / "bash-helper.sh"
        bash_helper_file.write_text("# Bash helper script")

        result = cli_runner.invoke(cli, ["install", "--shells", "bash", "-y"])

        assert result.exit_code == 0

        assert (mock_home / ".bash" / "git-prompt.sh").exists()
        assert (mock_home / ".bash" / "bash-helper.sh").exists()

        assert (
            mock_home / ".bash" / "git-prompt.sh"
        ).read_text() == "# Git prompt script"
        assert (
            mock_home / ".bash" / "bash-helper.sh"
        ).read_text() == "# Bash helper script"

    def test_status_with_additional_files(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        shared_scripts_dir = test_repo / "config" / "shared-scripts"
        shared_scripts_dir.mkdir()
        git_prompt_file = shared_scripts_dir / "git-prompt.sh"
        git_prompt_file.write_text("# Git prompt script")

        cli_runner.invoke(cli, ["install", "--shells", "bash", "-y"])

        result = cli_runner.invoke(cli, ["status", "--shells", "bash"])

        assert result.exit_code == 0
        assert "git-prompt.sh" in result.output


@pytest.mark.integration
@pytest.mark.cli
class TestSharedConfigSupport:
    """Test CLI commands with shared config support."""

    def test_install_with_shared_config(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        shared_sh = test_repo / "config" / "shared.sh"
        shared_sh.write_text("# Shared config\nalias ll='ls -la'")

        result = cli_runner.invoke(cli, ["install", "--shells", "bash", "-y"])

        assert result.exit_code == 0

        bashrc = mock_home / ".bashrc"
        assert bashrc.exists()

        content = bashrc.read_text()
        assert "### Shared Config ###" in content
        assert "### Shell-Specific Config ###" in content
        assert "alias ll='ls -la'" in content

    def test_shared_config_in_multiple_shells(
        self, test_repo, mock_home, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(test_repo)

        shared_sh = test_repo / "config" / "shared.sh"
        shared_sh.write_text("# Shared\nalias shared='echo shared'")

        result = cli_runner.invoke(cli, ["install", "--shells", "bash,zsh", "-y"])

        assert result.exit_code == 0

        bashrc = mock_home / ".bashrc"
        bash_content = bashrc.read_text()
        assert "alias shared='echo shared'" in bash_content
        assert "### Shared Config ###" in bash_content

        zshrc = mock_home / ".zshrc"
        zsh_content = zshrc.read_text()
        assert "alias shared='echo shared'" in zsh_content
        assert "### Shared Config ###" in zsh_content
