"""Real config install to disk, exercised through `configs install`.

These tests perform genuine filesystem writes into an isolated HOME using the
real bundled config. They deliberately drive `configs install` / `scripts
install` rather than the top-level `install` command: the latter iterates every
component (packages, languages, gh auth, signing, …) and on a clean machine
would attempt real apt/brew/gh/network/sudo operations. Do NOT "simplify" these
into `install -y`.
"""

from __future__ import annotations

import sys

import pytest

from tests.e2e.helpers import has_managed_marker, strip_ansi


@pytest.mark.e2e
class TestFreshInstall:
    def test_managed_sections_written(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        result = run_cli(["configs", "install", "--shells", "bash,zsh,git", "-y"])
        assert result.returncode == 0

        bashrc = (home_dir / ".bashrc").read_text()
        zshrc = (home_dir / ".zshrc").read_text()
        gitconfig = (home_dir / ".gitconfig").read_text()

        assert has_managed_marker(bashrc)
        assert has_managed_marker(zshrc)
        assert has_managed_marker(gitconfig)
        # A recognizable real alias from the bundled config/shared.sh.
        assert "alias ga='git add'" in bashrc
        assert "alias ga='git add'" in zshrc

    def test_additional_files_created(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        run_cli(["configs", "install", "--shells", "bash,zsh,git", "-y"])

        assert (home_dir / ".bash" / "git-prompt.sh").exists()
        assert (home_dir / ".bash" / "completions.bash").exists()
        assert (home_dir / ".zsh" / "git-prompt.sh").exists()
        assert (home_dir / ".zsh" / "completions.zsh").exists()
        assert (home_dir / ".config" / "git" / "ignore").exists()

    def test_additional_file_manifest_recorded(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        run_cli(["configs", "install", "--shells", "bash,zsh,git", "-y"])
        assert (
            home_dir / ".shell-configs" / "installed_additional_files.json"
        ).exists()


@pytest.mark.e2e
@pytest.mark.skipif(
    sys.platform == "win32", reason="~/.local/bin + exec bit are POSIX-only"
)
class TestScriptsInstall:
    def test_scripts_installed_executable(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        result = run_cli(["scripts", "install", "-y"])
        assert result.returncode == 0

        bin_dir = home_dir / ".local" / "bin"
        assert bin_dir.is_dir()
        installed = list(bin_dir.iterdir())
        assert installed, "expected at least one script installed"
        for script in installed:
            # Owner-executable bit set.
            assert script.stat().st_mode & 0o100, f"{script.name} not executable"

        assert (home_dir / ".shell-configs" / "installed_scripts.json").exists()


@pytest.mark.e2e
class TestBackupsAndPreservation:
    def test_backup_created_for_existing_rc(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        bashrc = home_dir / ".bashrc"
        original = "# MY CUSTOM LINE\nexport FOO=bar\n"
        bashrc.write_text(original)

        run_cli(["configs", "install", "--shells", "bash", "-y"])

        backups = list(home_dir.glob(".bashrc.shell-configs-backup.*"))
        assert backups, "expected a timestamped backup of the pre-existing .bashrc"
        assert "MY CUSTOM LINE" in backups[0].read_text()

    def test_user_content_preserved(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        bashrc = home_dir / ".bashrc"
        bashrc.write_text("# MY CUSTOM LINE\nexport FOO=bar\n")

        run_cli(["configs", "install", "--shells", "bash", "-y"])

        content = bashrc.read_text()
        assert "MY CUSTOM LINE" in content
        assert has_managed_marker(content)


@pytest.mark.e2e
class TestIdempotency:
    def test_second_install_is_noop(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        run_cli(["configs", "install", "--shells", "bash,zsh,git", "-y"])
        before = (home_dir / ".bashrc").read_text()

        second = run_cli(["configs", "install", "--shells", "bash,zsh,git", "-y"])
        assert second.returncode == 0
        assert "already in sync" in strip_ansi(second.stdout + second.stderr).lower()
        assert (home_dir / ".bashrc").read_text() == before


@pytest.mark.e2e
class TestForceReinstall:
    def test_force_restores_edited_section(self, run_cli, e2e_home):
        home_dir, _ = e2e_home
        bashrc = home_dir / ".bashrc"
        run_cli(["configs", "install", "--shells", "bash", "-y"])

        # Corrupt the managed alias by hand.
        edited = bashrc.read_text().replace(
            "alias ga='git add'", "alias ga='echo HIJACKED'"
        )
        assert "HIJACKED" in edited
        bashrc.write_text(edited)

        result = run_cli(["configs", "install", "--shells", "bash", "--force", "-y"])
        assert result.returncode == 0

        restored = bashrc.read_text()
        assert "alias ga='git add'" in restored
        assert "HIJACKED" not in restored
