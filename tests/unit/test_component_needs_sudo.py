"""Tests for Component.needs_sudo() implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from shell_configs.cli.context import (
    Component,
    ComponentPlan,
    LanguagesPlan,
    OptionalPackagesPlan,
    RequiredPackagesPlan,
)
from shell_configs.platform import Platform

if TYPE_CHECKING:
    from shell_configs.packages.packages import Package


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = True
    ctx.profile = None
    return ctx


def _linux_pkg(method: str = "apt", install_cmd: str | None = None) -> Package:
    """Build a Package with a linux InstallConfig using the given method."""
    from shell_configs.packages.packages import InstallConfig, Package

    return Package(
        name="testpkg",
        linux=InstallConfig(method=method, install_cmd=install_cmd),
    )


def _language(
    install_cmd: str | None = None,
    linux_method: str | None = None,
) -> MagicMock:
    """Build a minimal Language-like object."""
    from shell_configs.installers import PlatformInstallConfig

    lang = MagicMock()
    lang.status_only = False
    lang.install_cmd = install_cmd
    lang.linux = PlatformInstallConfig(method=linux_method) if linux_method else None
    return lang


@pytest.mark.unit
class TestComponentBaseNeedsSudo:
    def test_base_component_returns_false(self) -> None:
        ctx = _make_ctx()
        assert Component().needs_sudo(ctx, ComponentPlan()) is False


@pytest.mark.unit
class TestRequiredPackagesNeedsSudo:
    def test_apt_pkg_missing_on_linux_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import RequiredPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        pkg = _linux_pkg(method="apt")
        plan = RequiredPackagesPlan(has_changes=True, missing=[pkg])
        assert RequiredPackagesComponent().needs_sudo(_make_ctx(), plan) is True

    def test_apt_pkg_missing_on_wsl_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import RequiredPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.WSL,
        )
        pkg = _linux_pkg(method="apt")
        plan = RequiredPackagesPlan(has_changes=True, missing=[pkg])
        assert RequiredPackagesComponent().needs_sudo(_make_ctx(), plan) is True

    def test_nothing_missing_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import RequiredPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        plan = RequiredPackagesPlan(has_changes=False, missing=[])
        assert RequiredPackagesComponent().needs_sudo(_make_ctx(), plan) is False

    def test_apt_pkg_on_macos_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import RequiredPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.MACOS,
        )
        pkg = _linux_pkg(method="apt")
        plan = RequiredPackagesPlan(has_changes=True, missing=[pkg])
        assert RequiredPackagesComponent().needs_sudo(_make_ctx(), plan) is False

    def test_non_sudo_pkg_on_linux_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import RequiredPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        pkg = _linux_pkg(
            method="script", install_cmd="curl -fsSL https://example.com | bash"
        )
        plan = RequiredPackagesPlan(has_changes=True, missing=[pkg])
        assert RequiredPackagesComponent().needs_sudo(_make_ctx(), plan) is False


@pytest.mark.unit
class TestOptionalPackagesNeedsSudo:
    def test_apt_pkg_missing_on_linux_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import OptionalPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        pkg = _linux_pkg(method="apt")
        plan = OptionalPackagesPlan(has_changes=True, missing=[pkg], total=[pkg])
        assert OptionalPackagesComponent().needs_sudo(_make_ctx(), plan) is True

    def test_nothing_missing_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import OptionalPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        plan = OptionalPackagesPlan(has_changes=False, missing=[], total=[])
        assert OptionalPackagesComponent().needs_sudo(_make_ctx(), plan) is False

    def test_apt_pkg_on_macos_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.packages import OptionalPackagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.MACOS,
        )
        pkg = _linux_pkg(method="apt")
        plan = OptionalPackagesPlan(has_changes=True, missing=[pkg], total=[pkg])
        assert OptionalPackagesComponent().needs_sudo(_make_ctx(), plan) is False


@pytest.mark.unit
class TestLanguagesNeedsSudo:
    def test_install_cmd_with_sudo_on_linux_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.languages import LanguagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        lang = _language(install_cmd="sudo rm -rf /usr/local/go && sudo tar ...")
        plan = LanguagesPlan(has_changes=True, missing=[lang], all_languages=[lang])
        assert LanguagesComponent().needs_sudo(_make_ctx(), plan) is True

    def test_linux_apt_method_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.languages import LanguagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        lang = _language(linux_method="apt")
        plan = LanguagesPlan(has_changes=True, missing=[lang], all_languages=[lang])
        assert LanguagesComponent().needs_sudo(_make_ctx(), plan) is True

    def test_nothing_missing_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.languages import LanguagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        plan = LanguagesPlan(has_changes=False, missing=[], all_languages=[])
        assert LanguagesComponent().needs_sudo(_make_ctx(), plan) is False

    def test_install_cmd_with_sudo_on_macos_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.languages import LanguagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.MACOS,
        )
        lang = _language(install_cmd="sudo rm -rf /usr/local/go && sudo tar ...")
        plan = LanguagesPlan(has_changes=True, missing=[lang], all_languages=[lang])
        assert LanguagesComponent().needs_sudo(_make_ctx(), plan) is False

    def test_install_cmd_without_sudo_on_linux_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.languages import LanguagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        lang = _language(install_cmd="curl -fsSL https://sh.rustup.rs | sh -s -- -y")
        plan = LanguagesPlan(has_changes=True, missing=[lang], all_languages=[lang])
        assert LanguagesComponent().needs_sudo(_make_ctx(), plan) is False

    def test_install_cmd_with_sudo_on_wsl_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.languages import LanguagesComponent

        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.WSL,
        )
        lang = _language(install_cmd="sudo rm -rf /usr/local/go && sudo tar ...")
        plan = LanguagesPlan(has_changes=True, missing=[lang], all_languages=[lang])
        assert LanguagesComponent().needs_sudo(_make_ctx(), plan) is True
