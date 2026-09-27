"""CLI commands must exit non-zero when an underlying operation fails."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from click.testing import CliRunner

from shell_configs.cli import cli
from shell_configs.cli.context import Component, ComponentPlan, Context
from shell_configs.packages.packages import Package


class _FakePackageManager:
    display_name = "fake"

    def __init__(self, failing: set[str]) -> None:
        self.failing = failing

    def is_installed(self, pkg: Package) -> bool:
        return False

    def install(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        if pkg.name in self.failing:
            return False, "boom"
        return True, "installed"


def _patch_packages(
    monkeypatch: pytest.MonkeyPatch, failing: set[str]
) -> list[Package]:
    pkgs = [Package(name="alpha"), Package(name="beta")]
    monkeypatch.setattr(
        "shell_configs.packages.get_package_manager",
        lambda: _FakePackageManager(failing),
    )
    monkeypatch.setattr(
        "shell_configs.packages.load_packages_for_profile", lambda profile: pkgs
    )
    return pkgs


@pytest.mark.unit
@pytest.mark.cli
class TestPackagesInstallExitCode:
    def test_one_package_fails_exits_nonzero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_packages(monkeypatch, failing={"beta"})

        result = cli_runner.invoke(cli, ["packages", "install", "--yes"])

        assert result.exit_code == 1
        assert "1 installed, 1 failed" in result.output

    def test_all_packages_succeed_exits_zero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_packages(monkeypatch, failing=set())

        result = cli_runner.invoke(cli, ["packages", "install", "--yes"])

        assert result.exit_code == 0
        assert "Package installation complete" in result.output


def _make_component(
    label: str, stage: Literal["pre", "parallel", "post"], succeeds: bool
) -> Component:
    class _Fake(Component):
        apply_stage = stage

        def plan(self, ctx: Context) -> ComponentPlan:
            return ComponentPlan(has_changes=True)

        def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
            return succeeds

    comp = _Fake()
    comp.label = label
    comp.display_name = label
    return comp


@pytest.mark.unit
@pytest.mark.cli
class TestInstallExitCode:
    @pytest.mark.parametrize("stage", ["pre", "parallel", "post"])
    def test_component_apply_returns_false_exits_nonzero(
        self,
        stage: Literal["pre", "parallel", "post"],
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.cli.components.INSTALL_COMPONENTS",
            [
                _make_component("ok", "parallel", succeeds=True),
                _make_component("broken", stage, succeeds=False),
            ],
        )

        result = cli_runner.invoke(cli, ["install", "--yes", "--shells", "bash"])

        assert result.exit_code == 1
        assert "completed with errors" in result.output

    def test_all_components_succeed_exits_zero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.cli.components.INSTALL_COMPONENTS",
            [
                _make_component("a", "pre", succeeds=True),
                _make_component("b", "parallel", succeeds=True),
            ],
        )

        result = cli_runner.invoke(cli, ["install", "--yes", "--shells", "bash"])

        assert result.exit_code == 0
        assert "completed with errors" not in result.output
