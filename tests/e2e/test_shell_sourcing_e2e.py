"""Source the installed rc in a real shell and assert it actually works.

This is the closest thing to real-world usage: spawn bash/zsh, source the rc that
`configs install` wrote, and confirm the bundled aliases, functions, exported
variables, and git-prompt all load. Guarded off Windows (bash/zsh require WSL)
and skipped per-shell when the binary is absent (e.g. zsh on a bare Ubuntu
runner — CI installs it; see .github/workflows/e2e.yml).
"""

from __future__ import annotations

import sys

import pytest

from tests.e2e.helpers import shell_available

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="bash/zsh require WSL on Windows"
)


@pytest.mark.e2e
class TestBashSourcing:
    def test_sources_without_error(self, installed_home, run_shell):
        result = run_shell("bash", 'source "$HOME/.bashrc"')
        assert result.returncode == 0, result.stderr
        assert "command not found" not in result.stderr.lower()
        assert "syntax error" not in result.stderr.lower()

    def test_alias_ga_defined(self, installed_home, run_shell):
        result = run_shell("bash", 'source "$HOME/.bashrc"; alias ga')
        assert result.returncode == 0
        assert "git add" in result.stdout

    def test_function_wt_defined(self, installed_home, run_shell):
        result = run_shell("bash", 'source "$HOME/.bashrc"; type wt')
        assert result.returncode == 0
        assert "wt is a function" in result.stdout

    def test_shell_configs_dir_exported(self, installed_home, run_shell):
        result = run_shell(
            "bash",
            'source "$HOME/.bashrc"; '
            '[ -d "$SHELL_CONFIGS_DIR" ] && echo "DIR_OK:$SHELL_CONFIGS_DIR"',
        )
        assert result.returncode == 0
        assert "DIR_OK:" in result.stdout

    def test_git_prompt_loads_in_repo(self, installed_home, run_shell, git_repo):
        result = run_shell(
            "bash",
            f'source "$HOME/.bashrc"; cd "{git_repo}"; __git_ps1 "%s"',
        )
        assert result.returncode == 0, result.stderr
        assert "main" in result.stdout

    @pytest.mark.parametrize(
        "cmd,func",
        [
            ("disk-cleanup", "_disk_cleanup_completion"),
            ("transcribe", "_transcribe_completion"),
            ("db-helper", "_db_helper_completion"),
            ("backup-resmed", "_backup_resmed_completion"),
            ("wt", "_wt_completion"),
        ],
    )
    def test_completion_registered(self, installed_home, run_shell, cmd, func):
        result = run_shell("bash", f'source "$HOME/.bashrc"; complete -p {cmd}')
        assert result.returncode == 0, f"no completion for {cmd}"
        assert func in result.stdout


@pytest.mark.e2e
@pytest.mark.skipif(not shell_available("zsh"), reason="zsh not installed")
class TestZshSourcing:
    def test_sources_without_error(self, installed_home, run_shell):
        result = run_shell("zsh", 'source "$HOME/.zshrc"')
        assert result.returncode == 0, result.stderr
        assert "syntax error" not in result.stderr.lower()
        # `compinit` needs a terminal, so a non-interactive shell skips it and
        # later `compdef` calls warn "command not found" — expected here and not
        # a real failure. Any *other* missing command is a genuine problem.
        missing = [
            line
            for line in result.stderr.splitlines()
            if "command not found" in line.lower() and "compdef" not in line.lower()
        ]
        assert not missing, result.stderr

    def test_alias_ga_defined(self, installed_home, run_shell):
        result = run_shell("zsh", 'source "$HOME/.zshrc"; alias ga')
        assert result.returncode == 0
        assert "git add" in result.stdout

    def test_function_wt_defined(self, installed_home, run_shell):
        result = run_shell("zsh", 'source "$HOME/.zshrc"; whence -w wt')
        assert result.returncode == 0
        assert "function" in result.stdout

    @pytest.mark.parametrize(
        "func",
        ["_wt", "_disk_cleanup", "_transcribe", "_db_helper", "_backup_resmed"],
    )
    def test_completion_function_defined(self, installed_home, run_shell, func):
        result = run_shell("zsh", f'source "$HOME/.zshrc"; whence -w {func}')
        assert result.returncode == 0, f"{func} not defined"
        assert "function" in result.stdout

    def test_compdef_before_compinit_no_error(self, e2e_home, run_cli, run_shell):
        """Regression: compdef call placed above the managed section (e.g. by
        ai-agent-rules) must NOT produce 'command not found: compdef'.

        The preamble block is pinned to the very top of ~/.zshrc so the stub
        is defined before any foreign compdef call in the file body.
        """
        home_dir, _ = e2e_home
        zshrc = home_dir / ".zshrc"
        # Simulate a tool that wrote a compdef call before shell-configs installs
        zshrc.write_text("compdef _foo foo\n", encoding="utf-8")

        result = run_cli(["configs", "install", "--shells", "zsh", "-y"])
        assert result.returncode == 0, f"configs install failed: {result.stderr}"

        text = zshrc.read_text()
        preamble_pos = text.find("shell-configs Preamble")
        compdef_call_pos = text.find("compdef _foo foo")
        assert preamble_pos != -1, "Preamble block not found in zshrc"
        assert compdef_call_pos != -1, "Pre-existing compdef call disappeared"
        assert preamble_pos < compdef_call_pos, (
            "Preamble block must appear before the pre-existing compdef call"
        )

        result = run_shell("zsh", 'source "$HOME/.zshrc"')
        assert result.returncode == 0, result.stderr
        compdef_errors = [
            line
            for line in result.stderr.splitlines()
            if "command not found" in line.lower() and "compdef" in line.lower()
        ]
        assert not compdef_errors, f"Unexpected compdef error(s):\n{result.stderr}"
