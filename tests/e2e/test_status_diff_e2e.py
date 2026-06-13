"""Status and diff reflect real on-disk state.

Uses the hermetic `configs status` and `configs install --dry-run` paths (the
latter renders the pending diff without writing), so nothing touches packages or
the network. See test_install_e2e.py for why the top-level `install`/`diff`
commands are avoided here.
"""

from __future__ import annotations

import pytest

from tests.e2e.helpers import strip_ansi


@pytest.mark.e2e
class TestStatus:
    def test_clean_home_reports_not_installed(self, run_cli):
        result = run_cli(["configs", "status", "--shells", "bash,zsh,git"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "Not installed" in output
        assert "Synced" not in output

    def test_synced_after_install(self, installed_home, run_cli):
        result = run_cli(["configs", "status", "--shells", "bash,zsh,git"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "Synced" in output
        assert "Not installed" not in output


@pytest.mark.e2e
class TestDiff:
    def test_dry_run_in_sync_after_install(self, installed_home, run_cli):
        result = run_cli(
            ["configs", "install", "--shells", "bash,zsh,git", "--dry-run", "-y"]
        )
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        assert "already in sync" in output.lower()

    def test_dry_run_shows_diff_when_section_edited(self, installed_home, run_cli):
        home_dir, _ = installed_home
        bashrc = home_dir / ".bashrc"
        bashrc.write_text(
            bashrc.read_text().replace("alias ga='git add'", "alias ga='echo EDITED'")
        )

        result = run_cli(["configs", "install", "--shells", "bash", "--dry-run", "-y"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0
        # The pending diff restores the bundled alias and drops the edit.
        assert "git add" in output
        assert "Would update" in output
        # Nothing was actually written.
        assert "EDITED" in bashrc.read_text()
