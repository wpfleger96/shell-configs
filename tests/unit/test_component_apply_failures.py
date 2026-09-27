"""Component.apply() must report sub-operation failures via its return value."""

from __future__ import annotations

import io

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rich.console import Console

from shell_configs.cli.context import (
    ConfigsPlan,
    ExtensionsPlan,
    OptionalPackagesPlan,
    RequiredPackagesPlan,
    ScriptsPlan,
    StateDbChange,
)
from shell_configs.display import _console_override, print_batch_summary
from shell_configs.extensions import (
    ExtensionDiff,
    ExtensionResult,
    ExtensionResultStatus,
)
from shell_configs.manager import OperationResult
from shell_configs.packages.packages import Package
from shell_configs.script_manager import InstallResult, ScriptStatus, UninstallResult


@pytest.fixture()
def output() -> Iterator[io.StringIO]:
    """Capture everything printed through the display console."""
    buf = io.StringIO()
    token = _console_override.set(
        Console(file=buf, highlight=False, no_color=True, width=200)
    )
    yield buf
    _console_override.reset(token)


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


@pytest.mark.unit
class TestOptionalPackagesApply:
    def _apply(self, failing: set[str]) -> bool:
        from shell_configs.cli.components.packages import OptionalPackagesComponent

        pkgs = [Package(name="a"), Package(name="b")]
        plan = OptionalPackagesPlan(has_changes=True, total=pkgs, missing=pkgs)
        with patch(
            "shell_configs.packages.get_package_manager",
            return_value=_pkg_manager(failing),
        ):
            return OptionalPackagesComponent().apply(_make_ctx(), plan)

    def test_one_install_fails_returns_false(self, output: io.StringIO) -> None:
        assert self._apply(failing={"b"}) is False
        text = output.getvalue()
        assert "1 installed, 1 failed" in text
        assert "installation complete" not in text

    def test_all_installs_succeed_returns_true(self, output: io.StringIO) -> None:
        assert self._apply(failing=set()) is True
        assert "Package installation complete (2 packages)" in output.getvalue()

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


def _configs_shell() -> MagicMock:
    """A shell that contributes nothing beyond what a test explicitly plans."""
    shell = MagicMock()
    shell.name = "vscode"
    shell.get_config_files.return_value = []
    shell.get_additional_files.return_value = []
    shell.get_preferences_files.return_value = []
    return shell


@pytest.mark.unit
class TestConfigsApplyOrphansAndStateDb:
    def test_orphan_uninstall_error_returns_false(self, mock_home: Path) -> None:
        from shell_configs.cli.components.configs import ConfigsComponent

        ctx = _make_ctx()
        ctx.selected_shells = [_configs_shell()]
        orphan = "/nonexistent/orphan.json"
        manifest = MagicMock(is_new=False, files={orphan: MagicMock(owned_file=True)})
        manager = MagicMock()
        manager.uninstall_additional_file.return_value = (
            OperationResult.ERROR,
            "cannot remove",
        )
        plan = ConfigsPlan(has_changes=True, orphaned_additional_files=[orphan])
        with (
            patch.object(
                ConfigsComponent, "_create_manager", return_value=(MagicMock(), manager)
            ),
            patch(
                "shell_configs.manager.AdditionalFileManifest", return_value=manifest
            ),
        ):
            assert ConfigsComponent().apply(ctx, plan) is False
        manifest.remove.assert_not_called()

    def test_shared_state_db_key_error_in_one_editor_returns_false(
        self, mock_home: Path
    ) -> None:
        from shell_configs.cli.components.configs import ConfigsComponent

        ctx = _make_ctx()
        ctx.selected_shells = [_configs_shell()]
        key = "http.linkProtectionTrustedDomains"
        changes = [
            StateDbChange(shell, "Trusted", f"/{shell}/state.vscdb", key, None, "[]")
            for shell in ("vscode", "cursor")
        ]
        plan = ConfigsPlan(has_changes=True, state_db_changes=changes)

        def fake_write(
            db_path: Path, key: str, value: str
        ) -> tuple[OperationResult, str]:
            if "vscode" in str(db_path):
                return OperationResult.ERROR, "database is locked"
            return OperationResult.UPDATED, "updated"

        with (
            patch.object(
                ConfigsComponent,
                "_create_manager",
                return_value=(MagicMock(), MagicMock()),
            ),
            patch(
                "shell_configs.shells.state_db.write_state_db_value",
                side_effect=fake_write,
            ),
        ):
            assert ConfigsComponent().apply(ctx, plan) is False


@pytest.mark.unit
class TestScriptsApply:
    def _apply(
        self,
        install_result: InstallResult,
        uninstall_result: UninstallResult = UninstallResult.REMOVED,
    ) -> bool:
        from shell_configs.cli.components.scripts import ScriptsComponent

        entry = MagicMock()
        entry.name = "tool"
        plan = ScriptsPlan(
            has_changes=True,
            entries=[(entry, ScriptStatus.MISSING)],
            orphaned=["old-tool"],
        )
        with (
            patch("shell_configs.script_manager.ScriptManifest"),
            patch(
                "shell_configs.script_manager.install_script",
                return_value=(install_result, "install tool failed: disk full"),
            ),
            patch(
                "shell_configs.script_manager.uninstall_script",
                return_value=(uninstall_result, "remove old-tool failed"),
            ),
        ):
            return ScriptsComponent().apply(_make_ctx(), plan)

    def test_install_error_returns_false_and_reports(
        self, mock_home: Path, output: io.StringIO
    ) -> None:
        assert self._apply(InstallResult.ERROR) is False
        assert "install tool failed: disk full" in output.getvalue()

    def test_orphan_uninstall_error_returns_false_and_reports(
        self, mock_home: Path, output: io.StringIO
    ) -> None:
        result = self._apply(InstallResult.INSTALLED, UninstallResult.ERROR)
        assert result is False
        assert "remove old-tool failed" in output.getvalue()

    def test_install_and_orphan_cleanup_succeed_returns_true(
        self, mock_home: Path
    ) -> None:
        assert self._apply(InstallResult.INSTALLED) is True


@pytest.mark.unit
class TestPrintBatchSummary:
    def test_failures_print_counts_warning(self, output: io.StringIO) -> None:
        print_batch_summary("Package installation", "installed", 3, 2)
        text = output.getvalue()
        assert "3 installed, 2 failed" in text
        assert "complete" not in text

    def test_no_failures_print_completion(self, output: io.StringIO) -> None:
        print_batch_summary("Package installation", "installed", 3, 0)
        text = output.getvalue()
        assert "Package installation complete (3 packages)" in text
        assert "failed" not in text


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
