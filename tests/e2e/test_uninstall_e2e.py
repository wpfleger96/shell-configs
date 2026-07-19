"""Uninstall-after-install round trips.

Drives `configs uninstall` / `scripts uninstall` so the round trip stays
hermetic (no package/gh/network components). Verifies managed sections and
managed files are removed.
"""

from __future__ import annotations

import json
import sys

import pytest

from tests.e2e.helpers import has_managed_marker


@pytest.mark.e2e
class TestUninstallRoundTrip:
    def test_managed_sections_removed(self, installed_home, run_cli):
        home_dir, _ = installed_home
        result = run_cli(["configs", "uninstall", "--shells", "bash,zsh,git", "-y"])
        assert result.returncode == 0

        assert not has_managed_marker((home_dir / ".bashrc").read_text())
        assert not has_managed_marker((home_dir / ".zshrc").read_text())
        assert not has_managed_marker((home_dir / ".gitconfig").read_text())

    def test_additional_files_removed(self, installed_home, run_cli):
        home_dir, _ = installed_home
        run_cli(["configs", "uninstall", "--shells", "bash,zsh,git", "-y"])
        assert not (home_dir / ".bash" / "git-prompt.sh").exists()
        assert not (home_dir / ".zsh" / "git-prompt.sh").exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="~/.local/bin is POSIX-only")
    def test_scripts_removed(self, installed_home, run_cli):
        home_dir, _ = installed_home
        bin_dir = home_dir / ".local" / "bin"
        assert any(bin_dir.iterdir())  # installed by the fixture

        result = run_cli(["scripts", "uninstall", "-y"])
        assert result.returncode == 0

        manifest_path = home_dir / ".shell-configs" / "installed_scripts.json"
        manifest = json.loads(manifest_path.read_text())
        # Manifest tracks scripts under a "scripts" mapping; it should be empty.
        assert not manifest.get("scripts", manifest)
