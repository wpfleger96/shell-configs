"""Tests for package management functionality."""

import shutil
import subprocess

from pathlib import Path

import pytest

from shell_configs.packages import (
    HomebrewManager,
    InstallConfig,
    LinuxInstaller,
    Package,
    get_package_manager,
    load_packages,
)
from shell_configs.packages.packages import WingetManager
from shell_configs.platform import Platform, detect_platform, is_platform


class TestPackageWslOnly:
    """Tests for wsl_only package filtering."""

    def test_wsl_only_skipped_on_non_wsl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.LINUX,
        )
        pkg = Package(
            name="wslu",
            command="wslview",
            wsl_only=True,
            linux=InstallConfig(method="apt"),
        )
        assert pkg.get_config_for_platform() is None

    def test_wsl_only_returns_config_on_wsl(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.WSL,
        )
        linux_config = InstallConfig(method="apt")
        pkg = Package(
            name="wslu",
            command="wslview",
            wsl_only=True,
            linux=linux_config,
        )
        assert pkg.get_config_for_platform() is linux_config

    def test_non_wsl_only_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.LINUX,
        )
        linux_config = InstallConfig(method="apt")
        pkg = Package(
            name="expect",
            linux=linux_config,
        )
        assert pkg.get_config_for_platform() is linux_config

    def test_load_packages_filters_wsl_only(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        manifest_content = """\
packages:
  - name: git
    command: git
    linux:
      method: apt
  - name: wslu
    command: wslview
    wsl_only: true
    linux:
      method: apt
"""
        manifest_path = tmp_path / "packages.yaml"
        manifest_path.write_text(manifest_content)
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.LINUX,
        )

        packages = load_packages(manifest_path)

        names = [p.name for p in packages]
        assert "git" in names
        assert "wslu" not in names


def test_platform_detection() -> None:
    """Test that platform detection returns a Platform enum."""
    result = detect_platform()
    assert isinstance(result, Platform)


def test_load_packages_returns_list(tmp_path: Path) -> None:
    """Test that load_packages parses YAML and returns list of packages."""
    manifest_content = """
packages:
  - name: git
    command: git
    description: "Version control"
    macos:
      method: brew
    linux:
      method: apt
  - name: vim
    command: vim
    macos:
      method: brew
    linux:
      method: apt
"""
    manifest_path = tmp_path / "packages.yaml"
    manifest_path.write_text(manifest_content)

    packages = load_packages(manifest_path)

    assert isinstance(packages, list)
    assert len(packages) == 2
    names = [p.name for p in packages]
    assert "git" in names
    assert "vim" in names


def test_load_packages_includes_common() -> None:
    """Test that load_packages includes packages from default manifest."""
    packages = load_packages()

    names = [p.name for p in packages]
    assert "expect" in names
    assert "sqlite" in names


def test_package_get_command() -> None:
    """Test that Package.get_command returns command or falls back to name."""
    pkg_with_command = Package(
        name="sqlite",
        command="sqlite3",
        macos=InstallConfig(method="brew", package="sqlite"),
    )
    assert pkg_with_command.get_command() == "sqlite3"

    pkg_without_command = Package(
        name="expect",
        macos=InstallConfig(method="brew"),
    )
    assert pkg_without_command.get_command() == "expect"


def test_package_get_config_for_platform() -> None:
    """Test that Package.get_config_for_platform returns correct config."""
    macos_config = InstallConfig(method="brew")
    linux_config = InstallConfig(method="apt")

    pkg = Package(
        name="test",
        macos=macos_config,
        linux=linux_config,
    )

    config = pkg.get_config_for_platform()
    assert config is not None
    assert config.method in ["brew", "apt"]


def test_get_package_manager_returns_manager() -> None:
    """Test that get_package_manager finds available manager."""
    manager = get_package_manager()

    if is_platform(Platform.MACOS) and shutil.which("brew"):
        assert manager is not None
        assert manager.name == "homebrew"
    elif not is_platform(Platform.MACOS) and (
        shutil.which("apt") or shutil.which("pip") or shutil.which("uv")
    ):
        assert manager is not None
        assert manager.name == "linux"


def test_homebrew_manager_detects_availability() -> None:
    """Test that Homebrew manager correctly reports availability."""
    homebrew = HomebrewManager()

    has_brew = shutil.which("brew") is not None
    assert homebrew.is_available() == has_brew


def test_homebrew_manager_binary_check_fallback() -> None:
    """Test that HomebrewManager uses binary check as fast path."""
    homebrew = HomebrewManager()

    if not is_platform(Platform.MACOS):
        return

    pkg = Package(
        name="sh",
        command="sh",
        macos=InstallConfig(method="brew"),
    )

    result = homebrew.is_installed(pkg)
    assert result is True


def test_linux_installer_binary_check_fallback() -> None:
    """Test that LinuxInstaller uses binary check as fast path."""
    if is_platform(Platform.MACOS):
        return

    linux_installer = LinuxInstaller()

    pkg = Package(
        name="sh",
        command="sh",
        linux=InstallConfig(method="apt"),
    )

    result = linux_installer.is_installed(pkg)
    assert result is True


@pytest.mark.unit
class TestWingetManager:
    """Tests for WingetManager Windows package manager."""

    def test_is_available_when_winget_on_path(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/winget" if name == "winget" else None,
        )
        manager = WingetManager()
        assert manager.is_available() is True

    def test_is_available_when_winget_missing(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: None,
        )
        manager = WingetManager()
        assert manager.is_available() is False

    def test_install_dry_run(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: None,
        )
        manager = WingetManager()
        monkeypatch.setattr(manager, "is_installed", lambda pkg: False)
        pkg = Package(
            name="git",
            windows=InstallConfig(method="winget", package="Git.Git"),
        )
        success, msg = manager.install(pkg, dry_run=True)
        assert success is True
        assert "Git.Git" in msg

    def test_install_already_installed(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/git" if name == "git" else None,
        )
        manager = WingetManager()
        pkg = Package(
            name="git",
            command="git",
            windows=InstallConfig(method="winget", package="Git.Git"),
        )
        success, msg = manager.install(pkg, dry_run=False)
        assert success is True
        assert "already installed" in msg

    def test_install_timeout(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: None,
        )
        monkeypatch.setattr(
            "shell_configs.packages.packages.subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(
                subprocess.TimeoutExpired("winget", 300)
            ),
        )
        manager = WingetManager()
        pkg = Package(
            name="git",
            windows=InstallConfig(method="winget", package="Git.Git"),
        )
        success, msg = manager.install(pkg, dry_run=False)
        assert success is False
        assert "timed out" in msg


class TestInjectSignedBy:
    """Tests for _inject_signed_by."""

    def setup_method(self):
        from shell_configs.packages.packages import _inject_signed_by

        self.inject = _inject_signed_by

    def test_adds_signed_by_inside_bracket(self):
        source = "deb [arch=amd64] https://example.com stable main"
        result = self.inject(source, "/usr/share/keyrings/test.gpg")
        assert "signed-by=/usr/share/keyrings/test.gpg" in result
        assert result.startswith("deb [arch=amd64 signed-by=")

    def test_noop_when_signed_by_already_present(self):
        source = "deb [arch=amd64 signed-by=/usr/share/keyrings/test.gpg] https://example.com stable main"
        assert self.inject(source, "/other/path.gpg") == source

    def test_preserves_url_and_suite(self):
        source = "deb [arch=amd64] https://apt.releases.hashicorp.com resolute main"
        result = self.inject(
            source, "/usr/share/keyrings/hashicorp-archive-keyring.gpg"
        )
        assert "https://apt.releases.hashicorp.com resolute main" in result


class TestRunPkgCmdFallback:
    """Tests for _run_pkg_cmd stdout/stderr fallback chain."""

    def _run(
        self, monkeypatch: pytest.MonkeyPatch, stdout: str, stderr: str
    ) -> tuple[bool, str]:
        import subprocess as sp

        from shell_configs.packages.packages import _run_pkg_cmd

        monkeypatch.setattr(
            "shell_configs.packages.packages.subprocess.run",
            lambda *a, **kw: sp.CompletedProcess(
                args=[], returncode=1, stdout=stdout, stderr=stderr
            ),
        )
        return _run_pkg_cmd(
            ["cmd"],
            timeout=10,
            success_msg="ok",
            failure_msg="generic",
            timeout_msg="timeout",
        )

    def test_stderr_preferred(self, monkeypatch):
        ok, msg = self._run(monkeypatch, stdout="stdout msg", stderr="stderr msg")
        assert not ok
        assert msg == "stderr msg"

    def test_stdout_fallback_when_stderr_empty(self, monkeypatch):
        ok, msg = self._run(monkeypatch, stdout="error on stdout", stderr="")
        assert not ok
        assert msg == "error on stdout"

    def test_generic_fallback_when_both_empty(self, monkeypatch):
        ok, msg = self._run(monkeypatch, stdout="", stderr="")
        assert not ok
        assert msg == "generic"
