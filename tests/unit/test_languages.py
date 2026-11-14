"""Tests for language runtime management."""

from __future__ import annotations

import os
import subprocess

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shell_configs.languages import (
    Language,
    LanguageInstallConfig,
    _resolve_check_path,
    ensure_language_paths,
    get_language_version,
    install_language,
    is_language_installed,
    load_languages,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lang(
    name: str = "go",
    command: str = "go",
    description: str = "Go",
    status_only: bool = False,
    check_path: str | None = None,
    install_cmd: str | None = None,
    macos: LanguageInstallConfig | None = None,
    linux: LanguageInstallConfig | None = None,
) -> Language:
    return Language(
        name=name,
        command=command,
        description=description,
        status_only=status_only,
        check_path=check_path,
        install_cmd=install_cmd,
        macos=macos,
        linux=linux,
    )


# ---------------------------------------------------------------------------
# TestLoadLanguages
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadLanguages:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_languages(tmp_path / "nonexistent.yaml")
        assert result == []

    def test_loads_languages(self, tmp_path):
        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n  - name: go\n    command: go\n    description: Go language\n"
        )
        langs = load_languages(manifest)
        assert len(langs) == 1
        assert langs[0].name == "go"
        assert langs[0].command == "go"
        assert langs[0].description == "Go language"

    def test_status_only_flag(self, tmp_path):
        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n"
            "  - name: python\n"
            "    command: uv\n"
            "    description: Python\n"
            "    status_only: true\n"
        )
        langs = load_languages(manifest)
        assert langs[0].status_only is True

    def test_check_path_parsed(self, tmp_path):
        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n"
            "  - name: rust\n"
            "    command: rustup\n"
            "    description: Rust\n"
            "    check_path: ~/.cargo/bin/rustup\n"
        )
        langs = load_languages(manifest)
        assert langs[0].check_path == "~/.cargo/bin/rustup"

    def test_install_configs_parsed(self, tmp_path):
        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n"
            "  - name: go\n"
            "    command: go\n"
            "    description: Go\n"
            "    macos:\n"
            "      method: brew\n"
            "      package: go\n"
            "    linux:\n"
            "      method: apt\n"
            "      package: golang\n"
        )
        langs = load_languages(manifest)
        assert langs[0].macos == LanguageInstallConfig(method="brew", package="go")
        assert langs[0].linux == LanguageInstallConfig(method="apt", package="golang")

    def test_install_cmd_parsed(self, tmp_path):
        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n"
            "  - name: rust\n"
            "    command: rustup\n"
            "    description: Rust\n"
            "    install_cmd: 'curl https://sh.rustup.rs | sh'\n"
        )
        langs = load_languages(manifest)
        assert langs[0].install_cmd == "curl https://sh.rustup.rs | sh"

    def test_skips_entries_missing_required_fields(self, tmp_path):
        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n"
            "  - name: go\n"
            "    description: No command\n"
            "  - name: rust\n"
            "    command: rustup\n"
            "    description: OK\n"
        )
        langs = load_languages(manifest)
        assert len(langs) == 1
        assert langs[0].name == "rust"

    def test_empty_languages_key(self, tmp_path):
        manifest = tmp_path / "languages.yaml"
        manifest.write_text("languages: []\n")
        assert load_languages(manifest) == []

    def test_bundled_check_paths_point_into_bin_dirs(self):
        # ensure_language_paths prepends check_path's parent to PATH, so
        # check_path must live in a bin dir rather than a scripts/data dir
        # like ~/.rvm/scripts.
        langs = [lang for lang in load_languages() if lang.check_path]
        assert langs
        for lang in langs:
            assert lang.check_path is not None
            assert Path(lang.check_path).parent.name == "bin", lang.name


# ---------------------------------------------------------------------------
# TestResolveCheckPath
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveCheckPath:
    def test_static_path_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        target = tmp_path / ".cargo" / "bin" / "rustup"
        target.parent.mkdir(parents=True)
        target.touch()
        assert _resolve_check_path("~/.cargo/bin/rustup") == target

    def test_static_path_missing(self, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: Path("/nonexistent")))
        assert _resolve_check_path("~/.cargo/bin/rustup") is None

    def test_glob_matches_latest(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        for ver in ("v18.0.0", "v20.20.2", "v22.1.0"):
            node_bin = tmp_path / ".nvm" / "versions" / "node" / ver / "bin"
            node_bin.mkdir(parents=True)
            (node_bin / "node").touch()
        result = _resolve_check_path("~/.nvm/versions/node/v*/bin/node")
        assert result is not None
        assert "v22.1.0" in str(result)

    def test_glob_no_matches(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        assert _resolve_check_path("~/.nvm/versions/node/v*/bin/node") is None


# ---------------------------------------------------------------------------
# TestIsLanguageInstalled
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsLanguageInstalled:
    def test_check_path_exists(self, tmp_path, monkeypatch):
        check = tmp_path / "rustup"
        check.touch()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        lang = _make_lang(command="rustup", check_path="~/.cargo/bin/rustup")
        # check_path resolves via ~ expansion; need the path to actually exist
        # Patch is_language_installed to use our tmp_path
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        (cargo_bin / "rustup").touch()
        assert is_language_installed(lang)

    def test_check_path_missing_falls_back_to_which(self, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: Path("/nonexistent")))
        with patch(
            "shell_configs.bootstrap.detection.shutil.which", return_value="/usr/bin/go"
        ):
            lang = _make_lang(command="go", check_path="~/.go/bin/go")
            assert is_language_installed(lang)

    def test_neither_check_path_nor_which(self, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: Path("/nonexistent")))
        with patch("shell_configs.bootstrap.detection.shutil.which", return_value=None):
            lang = _make_lang(command="go", check_path="~/.nonexistent/go")
            assert not is_language_installed(lang)

    def test_no_check_path_uses_which(self):
        with patch(
            "shell_configs.bootstrap.detection.shutil.which",
            return_value="/usr/local/bin/go",
        ):
            assert is_language_installed(_make_lang(command="go"))

    def test_no_check_path_command_missing(self):
        with patch("shell_configs.bootstrap.detection.shutil.which", return_value=None):
            assert not is_language_installed(_make_lang(command="go"))


# ---------------------------------------------------------------------------
# TestInstallLanguage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallLanguage:
    def test_status_only_returns_success_without_installing(self):
        lang = _make_lang(status_only=True)
        ok, msg = install_language(lang)
        assert ok
        assert "status-only" in msg

    def test_already_installed_returns_success(self):
        with patch("shell_configs.languages.is_language_installed", return_value=True):
            ok, msg = install_language(_make_lang())
        assert ok
        assert "already installed" in msg

    def test_brew_install_on_macos(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform",
            lambda p: p.value == "macos",
        )
        lang = _make_lang(
            macos=LanguageInstallConfig(method="brew", package="go"),
        )
        with (
            patch("shell_configs.languages.is_language_installed", return_value=False),
            patch(
                "shell_configs.bootstrap.detection.shutil.which",
                return_value="/usr/local/bin/brew",
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = install_language(lang)
        assert ok
        assert "go" in msg
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["brew", "install", "go"]

    def test_apt_install_on_linux(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform",
            lambda p: p.value == "linux",
        )
        lang = _make_lang(
            linux=LanguageInstallConfig(method="apt", package="golang"),
        )
        with (
            patch("shell_configs.languages.is_language_installed", return_value=False),
            patch(
                "shell_configs.bootstrap.detection.shutil.which",
                return_value="/usr/bin/apt",
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = install_language(lang)
        assert ok
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["sudo", "-n", "apt-get", "install", "-y", "golang"]

    def test_script_install_fallback(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform",
            lambda p: False,
        )
        lang = _make_lang(install_cmd="curl https://sh.rustup.rs | sh -s -- -y")
        with (
            patch("shell_configs.languages.is_language_installed", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            ok, msg = install_language(lang)
        assert ok
        assert mock_run.call_args[1].get("shell") is True

    def test_dry_run_brew(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform",
            lambda p: p.value == "macos",
        )
        lang = _make_lang(macos=LanguageInstallConfig(method="brew", package="go"))
        with (
            patch("shell_configs.languages.is_language_installed", return_value=False),
            patch(
                "shell_configs.bootstrap.detection.shutil.which",
                return_value="/usr/local/bin/brew",
            ),
        ):
            ok, msg = install_language(lang, dry_run=True)
        assert ok
        assert "Would" in msg

    def test_no_install_method_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform",
            lambda p: False,
        )
        lang = _make_lang()  # no macos, linux, or install_cmd
        with patch("shell_configs.languages.is_language_installed", return_value=False):
            ok, msg = install_language(lang)
        assert not ok
        assert "No install method" in msg

    def test_apt_unavailable_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.installers.is_platform",
            lambda p: p.value == "linux",
        )
        lang = _make_lang(linux=LanguageInstallConfig(method="apt", package="golang"))
        with (
            patch("shell_configs.languages.is_language_installed", return_value=False),
            patch("shell_configs.bootstrap.detection.shutil.which", return_value=None),
        ):
            ok, msg = install_language(lang)
        assert not ok
        assert "apt is not available" in msg


# ---------------------------------------------------------------------------
# TestGetLanguageVersion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetLanguageVersion:
    def test_returns_version_string(self):
        with (
            patch(
                "shell_configs.bootstrap.detection.shutil.which",
                return_value="/usr/local/bin/go",
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="go version go1.22.3 linux/amd64",
                stderr="",
            )
            version = get_language_version(_make_lang(command="go"))
        assert version == "go version go1.22.3 linux/amd64"

    def test_returns_none_when_command_not_found(self):
        with patch("shell_configs.bootstrap.detection.shutil.which", return_value=None):
            assert get_language_version(_make_lang(command="go")) is None


# ---------------------------------------------------------------------------
# TestLanguagesComponent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLanguagesComponent:
    def _make_ctx(self, dry_run: bool = False, yes: bool = True) -> MagicMock:
        ctx = MagicMock()
        ctx.dry_run = dry_run
        ctx.yes = yes
        return ctx

    def test_plan_identifies_missing(self, tmp_path):
        from shell_configs.cli.components.languages import LanguagesComponent

        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n  - name: go\n    command: go\n    description: Go\n"
        )
        with (
            patch("shell_configs.languages.get_config_dir", return_value=tmp_path),
            patch("shell_configs.languages.is_language_installed", return_value=False),
        ):
            plan = LanguagesComponent().plan(self._make_ctx())

        assert plan.has_changes
        assert len(plan.missing) == 1
        assert plan.missing[0].name == "go"

    def test_plan_no_changes_when_all_installed(self, tmp_path):
        from shell_configs.cli.components.languages import LanguagesComponent

        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n  - name: go\n    command: go\n    description: Go\n"
        )
        with (
            patch("shell_configs.languages.get_config_dir", return_value=tmp_path),
            patch("shell_configs.languages.is_language_installed", return_value=True),
        ):
            plan = LanguagesComponent().plan(self._make_ctx())

        assert not plan.has_changes
        assert plan.missing == []

    def test_status_only_excluded_from_managed_count(self, tmp_path):
        from shell_configs.cli.components.languages import LanguagesComponent

        manifest = tmp_path / "languages.yaml"
        manifest.write_text(
            "languages:\n"
            "  - name: python\n"
            "    command: uv\n"
            "    description: Python\n"
            "    status_only: true\n"
            "  - name: go\n"
            "    command: go\n"
            "    description: Go\n"
        )
        with (
            patch("shell_configs.languages.get_config_dir", return_value=tmp_path),
            patch(
                "shell_configs.languages.is_language_installed",
                side_effect=lambda l: l.name != "go",
            ),
        ):
            plan = LanguagesComponent().plan(self._make_ctx())

        assert plan.has_changes
        assert len(plan.status_only) == 1
        assert plan.status_only[0].name == "python"
        # python is status-only so even though is_language_installed returns False for it,
        # it should not appear in missing
        assert all(l.name != "python" for l in plan.missing)

    def test_apply_installs_missing(self, tmp_path):
        from shell_configs.cli.components.languages import LanguagesComponent
        from shell_configs.cli.context import LanguagesPlan

        lang = _make_lang(name="go", command="go", description="Go")
        plan = LanguagesPlan(has_changes=True, all_languages=[lang], missing=[lang])

        with (
            patch(
                "shell_configs.languages.install_language",
                return_value=(True, "Installed go"),
            ) as mock_install,
            patch(
                "shell_configs.languages.ensure_language_paths",
            ) as mock_paths,
        ):
            LanguagesComponent().apply(self._make_ctx(), plan)

        mock_install.assert_called_once_with(lang, dry_run=False)
        mock_paths.assert_called_once_with([lang])


# ---------------------------------------------------------------------------
# TestEnsureLanguagePaths
# ---------------------------------------------------------------------------


def _install_binary(bin_dir: Path, name: str = "go") -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    binary = bin_dir / name
    binary.touch()
    return binary


@pytest.mark.unit
class TestEnsureLanguagePaths:
    def test_installed_language_bin_dir_is_prepended(self, tmp_path, monkeypatch):
        binary = _install_binary(tmp_path / "go" / "bin")
        monkeypatch.setenv("PATH", "/usr/bin")
        ensure_language_paths([_make_lang(check_path=str(binary))])
        assert os.environ["PATH"].split(os.pathsep) == [
            str(binary.parent),
            "/usr/bin",
        ]

    def test_bin_dir_already_in_path_is_not_duplicated(self, tmp_path, monkeypatch):
        binary = _install_binary(tmp_path / "go" / "bin")
        original = os.pathsep.join(["/usr/bin", str(binary.parent)])
        monkeypatch.setenv("PATH", original)
        ensure_language_paths([_make_lang(check_path=str(binary))])
        assert os.environ["PATH"] == original

    def test_bin_dir_prefix_of_existing_entry_is_prepended(self, tmp_path, monkeypatch):
        binary = _install_binary(tmp_path / "go" / "bin")
        longer = str(tmp_path / "go" / "bin2")
        monkeypatch.setenv("PATH", os.pathsep.join([longer, "/usr/bin"]))
        ensure_language_paths([_make_lang(check_path=str(binary))])
        assert os.environ["PATH"].split(os.pathsep) == [
            str(binary.parent),
            longer,
            "/usr/bin",
        ]

    def test_uninstalled_language_leaves_path_unchanged(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", "/usr/bin")
        ensure_language_paths([_make_lang(check_path=str(tmp_path / "missing"))])
        assert os.environ["PATH"] == "/usr/bin"

    def test_empty_path_has_no_trailing_separator(self, tmp_path, monkeypatch):
        binary = _install_binary(tmp_path / "go" / "bin")
        monkeypatch.setenv("PATH", "")
        ensure_language_paths([_make_lang(check_path=str(binary))])
        assert os.environ["PATH"] == str(binary.parent)


# ---------------------------------------------------------------------------
# TestLanguagePathsBeforePackageInstalls
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestLanguagePathsBeforePackageInstalls:
    """Installed languages' bin dirs reach PATH before any package recipe runs."""

    @pytest.fixture
    def go_bin_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        binary = _install_binary(tmp_path / "go" / "bin")
        monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
        monkeypatch.setattr(
            "shell_configs.languages.load_languages",
            lambda: [_make_lang(check_path=str(binary))],
        )
        return binary.parent

    def test_install_with_no_missing_languages_puts_bin_dir_on_path(
        self, go_bin_dir, cli_runner, mock_home, test_repo, monkeypatch
    ):
        from shell_configs.cli import cli
        from shell_configs.cli.components.languages import LanguagesComponent
        from shell_configs.cli.context import Component, ComponentPlan

        seen_paths: list[str] = []

        class _Recorder(Component):
            label = display_name = "recorder"

            def plan(self, ctx):
                return ComponentPlan(has_changes=True)

            def apply(self, ctx, plan):
                seen_paths.append(os.environ["PATH"])
                return True

        monkeypatch.setattr(
            "shell_configs.cli.components.INSTALL_COMPONENTS",
            [LanguagesComponent(), _Recorder()],
        )

        result = cli_runner.invoke(cli, ["install", "--yes", "--shells", "bash"])

        assert result.exit_code == 0, result.output
        assert len(seen_paths) == 1
        assert str(go_bin_dir) in seen_paths[0].split(os.pathsep)

    def test_packages_install_puts_bin_dir_on_path(
        self, go_bin_dir, cli_runner, mock_home, test_repo, monkeypatch
    ):
        from shell_configs.cli import cli
        from shell_configs.packages.packages import Package

        seen_paths: list[str] = []

        class _Manager:
            display_name = "fake"

            def is_installed(self, pkg):
                return False

            def install(self, pkg, dry_run=False):
                seen_paths.append(os.environ["PATH"])
                return True, "installed"

        monkeypatch.setattr("shell_configs.packages.get_package_manager", _Manager)
        monkeypatch.setattr(
            "shell_configs.packages.load_packages_for_profile",
            lambda profile: [Package(name="needs-go")],
        )

        result = cli_runner.invoke(cli, ["packages", "install", "--yes"])

        assert result.exit_code == 0, result.output
        assert len(seen_paths) == 1
        assert str(go_bin_dir) in seen_paths[0].split(os.pathsep)
