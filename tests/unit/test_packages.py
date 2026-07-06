"""Tests for package management functionality."""

import io
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

    def test_load_packages_filters_linux_only_on_macos(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        manifest_content = """\
packages:
  - name: git
    command: git
    macos:
      method: brew
    linux:
      method: apt
  - name: wl-clipboard
    command: wl-copy
    linux:
      method: apt
"""
        manifest_path = tmp_path / "packages.yaml"
        manifest_path.write_text(manifest_content)
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.MACOS,
        )

        packages = load_packages(manifest_path)

        names = [p.name for p in packages]
        assert "git" in names
        assert "wl-clipboard" not in names


def test_linux_only_packages_excluded_on_macos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Linux-only packages must not appear in the macOS package list."""
    monkeypatch.setattr(
        "shell_configs.packages.packages.is_platform",
        lambda p: p == Platform.MACOS,
    )
    packages = load_packages()
    names = [p.name for p in packages]
    for pkg in (
        "wl-clipboard",
        "enpass",
        "enpass-cli",
        "bzip2",
        "build-essential",
        "docker",
    ):
        assert pkg not in names


def test_platform_detection() -> None:
    """Test that platform detection returns a Platform enum."""
    result = detect_platform()
    assert isinstance(result, Platform)


def test_enpass_cli_available_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """enpass-cli must not be wsl_only — it should be installable on native Linux."""
    monkeypatch.setattr(
        "shell_configs.packages.packages.is_platform",
        lambda p: p == Platform.LINUX,
    )
    packages = load_packages()
    names = [p.name for p in packages]
    assert "enpass-cli" in names


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

    def test_bracket_less_source_gets_signed_by(self):
        source = "deb https://apt.enpass.io/ stable main"
        result = self.inject(source, "/usr/share/keyrings/enpass-archive-keyring.gpg")
        assert result.startswith(
            "deb [signed-by=/usr/share/keyrings/enpass-archive-keyring.gpg]"
        )
        assert "https://apt.enpass.io/ stable main" in result

    def test_bracket_less_noop_when_signed_by_already_present(self):
        # A bracket-less line that already contains signed-by= must be left alone.
        source = "deb signed-by=/usr/share/keyrings/enpass.gpg https://apt.enpass.io/ stable main"
        assert self.inject(source, "/other/path.gpg") == source


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


class TestExtraPackages:
    def test_load_packages_parses_extra_packages(self, tmp_path: Path) -> None:
        manifest_content = """\
packages:
  - name: myapp
    linux:
      method: apt
      package: myapp
      extra_packages:
        - libfoo
        - libbar
"""
        manifest_path = tmp_path / "packages.yaml"
        manifest_path.write_text(manifest_content)

        packages = load_packages(manifest_path)

        assert len(packages) == 1
        config = packages[0].linux
        assert config is not None
        assert config.extra_packages == ["libfoo", "libbar"]

    def test_install_dry_run_mentions_extra_packages(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/apt" if name == "apt" else None,
        )
        installer = LinuxInstaller()
        monkeypatch.setattr(installer, "is_installed", lambda pkg: False)
        pkg = Package(
            name="myapp",
            linux=InstallConfig(
                method="apt", package="myapp", extra_packages=["libfoo", "libbar"]
            ),
        )
        success, msg = installer.install(pkg, dry_run=True)
        assert success is True
        assert "libfoo" in msg
        assert "libbar" in msg

    def test_install_includes_extra_packages_in_apt_command(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/apt" if name == "apt" else None,
        )
        installer = LinuxInstaller()
        monkeypatch.setattr(installer, "is_installed", lambda pkg: False)
        captured: list[list[str]] = []

        def fake_run(*a, **kw):
            captured.append(a[0])
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr("shell_configs.packages.packages.subprocess.run", fake_run)
        pkg = Package(
            name="myapp",
            linux=InstallConfig(
                method="apt", package="myapp", extra_packages=["libfoo", "libbar"]
            ),
        )
        installer.install(pkg)
        assert len(captured) == 1
        cmd = captured[0]
        assert "myapp" in cmd
        assert "libfoo" in cmd
        assert "libbar" in cmd

    def test_uninstall_includes_extra_packages_in_apt_command(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/apt" if name == "apt" else None,
        )
        installer = LinuxInstaller()
        monkeypatch.setattr(installer, "is_installed", lambda pkg: True)
        captured: list[list[str]] = []

        def fake_run(*a, **kw):
            captured.append(a[0])
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr("shell_configs.packages.packages.subprocess.run", fake_run)
        pkg = Package(
            name="myapp",
            linux=InstallConfig(
                method="apt", package="myapp", extra_packages=["libfoo", "libbar"]
            ),
        )
        installer.uninstall(pkg)
        assert len(captured) == 1
        cmd = captured[0]
        assert "myapp" in cmd
        assert "libfoo" in cmd
        assert "libbar" in cmd

    def test_extra_packages_ignored_for_non_apt_method(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/uv" if name == "uv" else None,
        )
        installer = LinuxInstaller()
        monkeypatch.setattr(installer, "is_installed", lambda pkg: False)
        pkg = Package(
            name="myapp",
            linux=InstallConfig(
                method="uv_tool", package="myapp", extra_packages=["libfoo"]
            ),
        )
        success, msg = installer.install(pkg, dry_run=True)
        assert success is True
        assert "libfoo" not in msg


class TestWslExclude:
    """Tests for wsl_exclude package filtering (mirror of TestPackageWslOnly)."""

    def test_wsl_exclude_returns_none_on_wsl(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.WSL,
        )
        pkg = Package(
            name="enpass",
            command="Enpass",
            wsl_exclude=True,
            linux=InstallConfig(method="apt"),
        )
        assert pkg.get_config_for_platform() is None

    def test_wsl_exclude_returns_config_on_native_linux(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.LINUX,
        )
        linux_config = InstallConfig(method="apt")
        pkg = Package(
            name="enpass",
            command="Enpass",
            wsl_exclude=True,
            linux=linux_config,
        )
        assert pkg.get_config_for_platform() is linux_config

    def test_wsl_exclude_does_not_affect_macos(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.MACOS,
        )
        macos_config = InstallConfig(method="brew")
        pkg = Package(
            name="enpass",
            command="Enpass",
            wsl_exclude=True,
            macos=macos_config,
        )
        assert pkg.get_config_for_platform() is macos_config

    def test_load_packages_filters_wsl_exclude_on_wsl(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        manifest_content = """\
packages:
  - name: git
    command: git
    linux:
      method: apt
  - name: enpass
    command: Enpass
    wsl_exclude: true
    linux:
      method: apt
"""
        manifest_path = tmp_path / "packages.yaml"
        manifest_path.write_text(manifest_content)
        monkeypatch.setattr(
            "shell_configs.packages.packages.is_platform",
            lambda p: p == Platform.WSL,
        )

        packages = load_packages(manifest_path)

        names = [p.name for p in packages]
        assert "git" in names
        assert "enpass" not in names


class TestEnsureSudoAuth:
    """Tests for ensure_sudo_auth()."""

    def _call(self) -> tuple[bool, str]:
        from shell_configs.packages.packages import ensure_sudo_auth

        return ensure_sudo_auth()

    def test_root_user_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shell_configs.packages.packages.os.geteuid", lambda: 0)
        ok, msg = self._call()
        assert ok is True
        assert msg == ""

    def test_no_sudo_binary_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shell_configs.packages.packages.os.geteuid", lambda: 1000)
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which", lambda name: None
        )
        ok, msg = self._call()
        assert ok is True
        assert msg == ""

    def test_cached_credentials_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("shell_configs.packages.packages.os.geteuid", lambda: 1000)
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/sudo" if name == "sudo" else None,
        )
        probe_cmds: list[list[str]] = []

        def fake_run(*args, **kwargs):
            probe_cmds.append(list(args[0]))
            return subprocess.CompletedProcess(args=args[0], returncode=0)

        monkeypatch.setattr("shell_configs.packages.packages.subprocess.run", fake_run)
        ok, msg = self._call()
        assert ok is True
        assert msg == ""
        assert probe_cmds[0] == ["sudo", "-n", "-v"]

    def test_no_cached_no_tty_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("shell_configs.packages.packages.os.geteuid", lambda: 1000)
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/sudo" if name == "sudo" else None,
        )
        monkeypatch.setattr(
            "shell_configs.packages.packages.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(args=a[0], returncode=1),
        )
        monkeypatch.setattr("shell_configs.packages.packages.sys.stdin", io.StringIO())
        ok, msg = self._call()
        assert ok is False
        assert "TTY" in msg

    def test_no_cached_tty_interactive_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("shell_configs.packages.packages.os.geteuid", lambda: 1000)
        monkeypatch.setattr(
            "shell_configs.packages.packages.shutil.which",
            lambda name: "/usr/bin/sudo" if name == "sudo" else None,
        )

        calls: list[tuple[list[str], dict]] = []

        def fake_run(*args, **kwargs):
            cmd = list(args[0])
            calls.append((cmd, kwargs))
            # Probe returns rc=1 (not cached); interactive sudo -v succeeds.
            if cmd == ["sudo", "-n", "-v"]:
                return subprocess.CompletedProcess(args=cmd, returncode=1)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr("shell_configs.packages.packages.subprocess.run", fake_run)

        class _FakeTTYStdin:
            def isatty(self) -> bool:
                return True

        monkeypatch.setattr(
            "shell_configs.packages.packages.sys.stdin", _FakeTTYStdin()
        )
        ok, msg = self._call()
        assert ok is True
        assert msg == ""
        assert len(calls) == 2
        assert calls[1][0] == ["sudo", "-v"]
        # Interactive call must not capture output.
        assert not calls[1][1].get("capture_output", False)


class TestLinuxNeedsSudo:
    """Tests for _linux_needs_sudo()."""

    def setup_method(self):
        from shell_configs.packages.packages import _linux_needs_sudo

        self._needs_sudo = _linux_needs_sudo

    def test_apt_method_needs_sudo(self) -> None:
        pkg = Package(name="git", linux=InstallConfig(method="apt"))
        assert self._needs_sudo(pkg) is True

    def test_script_with_sudo_in_cmd_needs_sudo(self) -> None:
        pkg = Package(
            name="enpass-cli",
            linux=InstallConfig(
                method="script", install_cmd="sudo dpkg -i /tmp/pkg.deb"
            ),
        )
        assert self._needs_sudo(pkg) is True

    def test_script_without_sudo_does_not_need_sudo(self) -> None:
        pkg = Package(
            name="enpass-cli",
            linux=InstallConfig(
                method="script", install_cmd="curl -sS https://webi.sh/delta | sh"
            ),
        )
        assert self._needs_sudo(pkg) is False

    def test_pip_method_does_not_need_sudo(self) -> None:
        pkg = Package(name="myapp", linux=InstallConfig(method="pip"))
        assert self._needs_sudo(pkg) is False

    def test_uv_tool_method_does_not_need_sudo(self) -> None:
        pkg = Package(name="myapp", linux=InstallConfig(method="uv_tool"))
        assert self._needs_sudo(pkg) is False

    def test_no_linux_config_does_not_need_sudo(self) -> None:
        pkg = Package(name="git", macos=InstallConfig(method="brew"))
        assert self._needs_sudo(pkg) is False


def test_enpass_absent_on_wsl(monkeypatch: pytest.MonkeyPatch) -> None:
    """enpass must not appear in the WSL package list (wsl_exclude=true)."""
    monkeypatch.setattr(
        "shell_configs.packages.packages.is_platform",
        lambda p: p == Platform.WSL,
    )
    packages = load_packages()
    names = [p.name for p in packages]
    assert "enpass" not in names


def test_enpass_present_on_native_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """enpass must appear in the native Linux package list."""
    monkeypatch.setattr(
        "shell_configs.packages.packages.is_platform",
        lambda p: p == Platform.LINUX,
    )
    packages = load_packages()
    names = [p.name for p in packages]
    assert "enpass" in names
