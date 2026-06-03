import sys

import pytest

from tests.e2e.helpers import strip_ansi


@pytest.mark.e2e
class TestHelp:
    def test_top_level_help(self, run_cli):
        result = run_cli(["--help"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "Usage:" in output
        for cmd in (
            "install",
            "status",
            "validate",
            "list-shells",
            "diff",
            "info",
            "completions",
        ):
            assert cmd in output

    def test_install_help(self, run_cli):
        result = run_cli(["install", "--help"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "--dry-run" in output


@pytest.mark.e2e
class TestListShells:
    def test_list_shells_output(self, run_cli):
        result = run_cli(["list-shells"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "Bash" in output
        assert "Zsh" in output
        assert "Git" in output


@pytest.mark.e2e
class TestValidate:
    def test_validate_bundled_config(self, run_cli):
        result = run_cli(["validate", "--shells", "bash"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "valid" in output.lower()


@pytest.mark.e2e
class TestDiff:
    def test_diff_exit_0(self, run_cli):
        result = run_cli(["diff"])
        assert result.returncode == 0


@pytest.mark.e2e
class TestStatus:
    def test_status_runs(self, run_cli):
        result = run_cli(["status"])
        assert result.returncode == 0


@pytest.mark.e2e
class TestInstallDryRun:
    def test_dry_run_no_files_created(self, run_cli, e2e_home, e2e_config_dir):
        home_dir, _ = e2e_home
        run_cli(["install", "--dry-run", "-y", "--config-dir", str(e2e_config_dir)])
        assert not (home_dir / ".bashrc").exists()
        assert not (home_dir / ".zshrc").exists()

    def test_dry_run_with_config_dir(self, run_cli, e2e_config_dir):
        result = run_cli(
            ["install", "--dry-run", "-y", "--config-dir", str(e2e_config_dir)]
        )
        assert result.returncode == 0


@pytest.mark.e2e
class TestInfo:
    def test_info_output(self, run_cli):
        result = run_cli(["info"])
        assert result.returncode == 0


@pytest.mark.e2e
class TestCompletionsStatus:
    def test_completions_shows_shells(self, run_cli):
        result = run_cli(["completions", "status"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "bash" in output.lower()
        assert "zsh" in output.lower()


@pytest.mark.e2e
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsSpecific:
    def test_powershell_listed(self, run_cli):
        result = run_cli(["list-shells"])
        output = strip_ansi(result.stdout + result.stderr)
        assert "PowerShell" in output

    def test_completions_powershell(self, run_cli):
        result = run_cli(["completions", "status"])
        output = strip_ansi(result.stdout + result.stderr)
        assert "powershell" in output.lower()
