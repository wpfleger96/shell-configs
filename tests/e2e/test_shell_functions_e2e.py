"""Test shell function *behavior* across bash and zsh.

The sourcing tests in test_shell_sourcing_e2e.py verify that functions are
*defined* after sourcing the rc.  These tests go further: they call functions
with arguments and assert on stdout, catching bash/zsh portability bugs like
BASH_REMATCH (bash-only) silently producing wrong output in zsh.
"""

from __future__ import annotations

import sys

import pytest

from tests.e2e.helpers import shell_available

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="bash/zsh require WSL on Windows"
)

SHELLS = ["bash", "zsh"]


def _source_cmd(shell: str) -> str:
    rc = ".bashrc" if shell == "bash" else ".zshrc"
    return f'source "$HOME/{rc}"'


def _skip_unless(shell: str) -> None:
    if not shell_available(shell):
        pytest.skip(f"{shell} not installed")


@pytest.mark.e2e
class TestParseDurationSeconds:
    @pytest.mark.parametrize("shell", SHELLS)
    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("30s", "30"),
            ("10m", "600"),
            ("3h", "10800"),
            ("1d", "86400"),
            ("60", "60"),
        ],
    )
    def test_valid_input(self, installed_home, run_shell, shell, input_val, expected):
        _skip_unless(shell)
        result = run_shell(
            shell,
            f"{_source_cmd(shell)}; _parse_duration_seconds {input_val}",
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == expected

    @pytest.mark.parametrize("shell", SHELLS)
    @pytest.mark.parametrize("input_val", ["abc", "3x"])
    def test_rejects_invalid(self, installed_home, run_shell, shell, input_val):
        _skip_unless(shell)
        result = run_shell(
            shell,
            f"{_source_cmd(shell)}; _parse_duration_seconds {input_val}",
        )
        assert result.returncode != 0

    @pytest.mark.parametrize("shell", SHELLS)
    def test_rejects_empty(self, installed_home, run_shell, shell):
        _skip_unless(shell)
        result = run_shell(
            shell,
            f'{_source_cmd(shell)}; _parse_duration_seconds ""',
        )
        assert result.returncode != 0


@pytest.mark.e2e
class TestWtSanitizeDirname:
    @pytest.mark.parametrize("shell", SHELLS)
    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("feat/my-branch", "feat-my-branch"),
            ("user\\branch", "user-branch"),
            ("scope:name", "scope-name"),
            ("wpfleger/feat/nested", "wpfleger-feat-nested"),
            ("already-clean", "already-clean"),
        ],
    )
    def test_sanitizes(self, installed_home, run_shell, shell, input_val, expected):
        _skip_unless(shell)
        result = run_shell(
            shell,
            f"{_source_cmd(shell)}; _wt_sanitize_dirname '{input_val}'",
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == expected


@pytest.mark.e2e
class TestWtRepoRoot:
    @pytest.mark.parametrize("shell", SHELLS)
    def test_inside_repo(self, installed_home, run_shell, shell, git_repo):
        _skip_unless(shell)
        result = run_shell(
            shell,
            f'{_source_cmd(shell)}; cd "{git_repo}" && _wt_repo_root',
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == str(git_repo)

    @pytest.mark.parametrize("shell", SHELLS)
    def test_outside_repo(self, installed_home, run_shell, shell, tmp_path):
        _skip_unless(shell)
        result = run_shell(
            shell,
            f'{_source_cmd(shell)}; cd "{tmp_path}" && _wt_repo_root',
        )
        assert result.returncode != 0


@pytest.mark.e2e
class TestExtract:
    @pytest.mark.parametrize("shell", SHELLS)
    def test_nonexistent_file(self, installed_home, run_shell, shell):
        _skip_unless(shell)
        result = run_shell(
            shell,
            f"{_source_cmd(shell)}; extract /no/such/file.tar.gz",
        )
        assert "is not a valid file" in result.stdout
