"""Component.apply() must report sub-operation failures via its return value."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shell_configs.cli.context import (
    ConfigsPlan,
    ExtensionsPlan,
    OptionalPackagesPlan,
    RequiredPackagesPlan,
)
from shell_configs.extensions import (
    ExtensionDiff,
    ExtensionResult,
    ExtensionResultStatus,
)
from shell_configs.manager import OperationResult
from shell_configs.packages.packages import Package


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.force = False
    ctx.yes = True
    ctx.profile = None
    ctx.profile_name = None
    return ctx


def _pkg_manager(failing: set[str]) -> MagicMock:
    manager = MagicMock()
    manager.install.side_effect = lambda pkg, dry_run: (
        (False, "boom") if pkg.name in failing else (True, "ok")
    )
    return manager


def _success_messages(mock_print_success: MagicMock) -> list[str]:
    return [str(c.args[0]) for c in mock_print_success.call_args_list]


@pytest.mark.unit
class TestOptionalPackagesApply:
    def _apply(self, failing: set[str]) -> tuple[bool, list[str]]:
        from shell_configs.cli.components.packages import OptionalPackagesComponent

        pkgs = [Package(name="a"), Package(name="b")]
        plan = OptionalPackagesPlan(has_changes=True, total=pkgs, missing=pkgs)
        with (
            patch(
                "shell_configs.packages.get_package_manager",
                return_value=_pkg_manager(failing),
            ),
            patch("shell_configs.display.print_success") as mock_success,
        ):
            result = OptionalPackagesComponent().apply(_make_ctx(), plan)
        return result, _success_messages(mock_success)

    def test_one_install_fails_returns_false(self) -> None:
        result, messages = self._apply(failing={"b"})
        assert result is False
        assert not any("installation complete" in m for m in messages)

    def test_all_installs_succeed_returns_true(self) -> None:
        result, messages = self._apply(failing=set())
        assert result is True
        assert any("installation complete" in m for m in messages)

    def test_package_manager_raises_returns_false(self) -> None:
        from shell_configs.cli.components.packages import OptionalPackagesComponent

        manager = MagicMock()
        manager.install.side_effect = RuntimeError("kaboom")
        pkgs = [Package(name="a")]
        plan = OptionalPackagesPlan(has_changes=True, total=pkgs, missing=pkgs)
        with patch("shell_configs.packages.get_package_manager", return_value=manager):
            assert OptionalPackagesComponent().apply(_make_ctx(), plan) is False


@pytest.mark.unit
class TestRequiredPackagesApply:
    def _apply(self, failing: set[str]) -> bool:
        from shell_configs.cli.components.packages import RequiredPackagesComponent

        pkgs = [Package(name="a", required=True), Package(name="b", required=True)]
        plan = RequiredPackagesPlan(has_changes=True, missing=pkgs)
        with patch(
            "shell_configs.packages.get_package_manager",
            return_value=_pkg_manager(failing),
        ):
            return RequiredPackagesComponent().apply(_make_ctx(), plan)

    def test_one_install_fails_returns_false(self) -> None:
        assert self._apply(failing={"a"}) is False

    def test_all_installs_succeed_returns_true(self) -> None:
        assert self._apply(failing=set()) is True


@pytest.mark.unit
class TestConfigsApply:
    def _apply(self, install_result: OperationResult) -> bool:
        from shell_configs.cli.components.configs import ConfigsComponent

        config_file = MagicMock(repo_config_name=None, path=Path("/nonexistent/rc"))
        shell = MagicMock()
        shell.name = "zsh"
        shell.get_config_files.return_value = [config_file]
        shell.supports_shared_config.return_value = True
        shell.get_additional_files.return_value = []
        shell.get_preferences_files.return_value = []

        ctx = _make_ctx()
        ctx.selected_shells = [shell]
        ctx.config_reader.get_shared_config_content.return_value = "export X=1"

        manager = MagicMock()
        manager.install_section.return_value = (install_result, "msg", None)
        with patch.object(
            ConfigsComponent,
            "_create_manager",
            return_value=(MagicMock(), manager),
        ):
            return ConfigsComponent().apply(ctx, ConfigsPlan(has_changes=True))

    def test_install_error_returns_false(self, mock_home: Path) -> None:
        assert self._apply(OperationResult.ERROR) is False

    def test_install_created_returns_true(self, mock_home: Path) -> None:
        assert self._apply(OperationResult.CREATED) is True


@pytest.mark.unit
class TestExtensionsApply:
    def _apply(self, results: list[ExtensionResult]) -> bool:
        from shell_configs.cli.components.extensions import ExtensionsComponent

        shell = MagicMock()
        shell.name = "vscode"
        shell.display_name = "VS Code"
        diff = ExtensionDiff(
            missing=frozenset({"pub.ext"}),
            extra=frozenset(),
            matched=frozenset(),
        )
        plan = ExtensionsPlan(has_changes=True, per_shell={"vscode": diff})
        with (
            patch(
                "shell_configs.cli.helpers._get_extension_shells",
                return_value=[shell],
            ),
            patch("shell_configs.extensions.ExtensionManager") as mock_manager_cls,
        ):
            mock_manager_cls.return_value.install_extensions.return_value = results
            return ExtensionsComponent().apply(_make_ctx(), plan)

    def test_extension_install_fails_returns_false(self) -> None:
        failed = ExtensionResult(
            "pub.ext", False, "failed", status=ExtensionResultStatus.FAILED
        )
        assert self._apply([failed]) is False

    def test_extension_install_succeeds_returns_true(self) -> None:
        ok = ExtensionResult("pub.ext", True, "installed")
        assert self._apply([ok]) is True
