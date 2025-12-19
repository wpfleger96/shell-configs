"""Tests for package management functionality."""

import shutil

from pathlib import Path

from shell_configs.packages import (
    HomebrewManager,
    InstallConfig,
    LinuxInstaller,
    Package,
    get_package_manager,
    is_macos,
    load_packages,
)


def test_platform_detection() -> None:
    """Test that platform detection returns a boolean."""
    result = is_macos()
    assert isinstance(result, bool)


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

    if is_macos() and shutil.which("brew"):
        assert manager is not None
        assert manager.name == "homebrew"
    elif not is_macos() and (shutil.which("apt") or shutil.which("pip")):
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

    if not is_macos():
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
    if is_macos():
        return

    linux_installer = LinuxInstaller()

    pkg = Package(
        name="sh",
        command="sh",
        linux=InstallConfig(method="apt"),
    )

    result = linux_installer.is_installed(pkg)
    assert result is True
