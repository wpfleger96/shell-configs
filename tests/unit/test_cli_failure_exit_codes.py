"""CLI commands must exit non-zero when an underlying operation fails."""

from __future__ import annotations

import subprocess

from pathlib import Path
from typing import Any, Literal

import pytest

from click.testing import CliRunner

from shell_configs.cli import cli
from shell_configs.cli.context import Component, ComponentPlan, Context
from shell_configs.packages.packages import Package


class _FakePackageManager:
    """Records installs into a shared log; installed packages stay installed."""

    display_name = "fake"

    def __init__(self, failing: set[str], log: list[str] | None = None) -> None:
        self.failing = failing
        self.log = log if log is not None else []

    def is_installed(self, pkg: Package) -> bool:
        return pkg.name in self.log

    def install(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        if pkg.name in self.failing:
            return False, "boom"
        self.log.append(pkg.name)
        return True, "installed"

    def can_uninstall(self, pkg: Package) -> bool:
        return True

    def uninstall(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        if pkg.name in self.failing:
            return False, "boom"
        return True, "uninstalled"


def _patch_packages(
    monkeypatch: pytest.MonkeyPatch,
    failing: set[str],
    pkgs: list[Package] | None = None,
    log: list[str] | None = None,
) -> _FakePackageManager:
    pkgs = pkgs if pkgs is not None else [Package(name="alpha"), Package(name="beta")]
    manager = _FakePackageManager(failing, log)
    monkeypatch.setattr("shell_configs.packages.get_package_manager", lambda: manager)
    monkeypatch.setattr(
        "shell_configs.packages.load_packages_for_profile", lambda profile: pkgs
    )
    return manager


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
        assert "Package installation complete (2 packages)" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestPackagesUninstallExitCode:
    def test_one_uninstall_fails_exits_nonzero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_packages(monkeypatch, failing={"beta"})

        result = cli_runner.invoke(cli, ["packages", "uninstall", "--yes"])

        assert result.exit_code == 1
        assert "1 uninstalled, 1 failed" in result.output

    def test_all_uninstalls_succeed_exits_zero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_packages(monkeypatch, failing=set())

        result = cli_runner.invoke(cli, ["packages", "uninstall", "--yes"])

        assert result.exit_code == 0
        assert "Package uninstall complete (2 packages)" in result.output


def _make_component(
    label: str,
    stage: Literal["pre", "parallel", "post"],
    succeeds: bool,
    raises: bool = False,
    applied: list[str] | None = None,
) -> Component:
    class _Fake(Component):
        apply_stage = stage

        def plan(self, ctx: Context) -> ComponentPlan:
            return ComponentPlan(has_changes=True)

        def apply(self, ctx: Context, plan: ComponentPlan) -> bool:
            if applied is not None:
                applied.append(label)
            if raises:
                raise RuntimeError(f"{label} exploded")
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

    @pytest.mark.parametrize("stage", ["pre", "post"])
    def test_sequential_component_raises_exits_nonzero_and_runs_remaining_stages(
        self,
        stage: Literal["pre", "parallel", "post"],
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        applied: list[str] = []
        monkeypatch.setattr(
            "shell_configs.cli.components.INSTALL_COMPONENTS",
            [
                _make_component("boom", stage, True, raises=True, applied=applied),
                _make_component("pre-ok", "pre", True, applied=applied),
                _make_component("par-ok", "parallel", True, applied=applied),
                _make_component("post-ok", "post", True, applied=applied),
            ],
        )

        result = cli_runner.invoke(cli, ["install", "--yes", "--shells", "bash"])

        assert result.exit_code == 1
        assert result.exception is None or isinstance(result.exception, SystemExit)
        assert "boom exploded" in result.output
        assert "Install completed with errors" in result.output
        assert set(applied) == {"boom", "pre-ok", "par-ok", "post-ok"}

    def test_every_parallel_component_raises_exits_nonzero_with_summary(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "shell_configs.cli.components.INSTALL_COMPONENTS",
            [
                _make_component("p1", "parallel", True, raises=True),
                _make_component("p2", "parallel", True, raises=True),
            ],
        )

        result = cli_runner.invoke(cli, ["install", "--yes", "--shells", "bash"])

        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "p1 exploded" in result.output
        assert "p2 exploded" in result.output
        assert "Install completed with errors" in result.output


@pytest.mark.unit
class TestSpinnerLabel:
    def test_component_returning_false_renders_failed_label(self) -> None:
        from shell_configs.cli.helpers import _finish_task

        class _Progress:
            description = ""

            def update(self, task_id: Any, description: str, completed: bool) -> None:
                self.description = description

        comp = _make_component("broken", "parallel", succeeds=False)
        progress = _Progress()

        _finish_task(progress, 0, comp, ok=False)
        assert "broken (failed)" in progress.description

        _finish_task(progress, 0, comp, ok=None)
        assert "(failed)" not in progress.description


def _patch_setup(
    monkeypatch: pytest.MonkeyPatch,
    test_repo: Path,
    install_components: list[Component],
    log: list[str],
) -> None:
    """Stub the tool-install step and language installs; record language installs in *log*."""
    from shell_configs.languages import Language

    monkeypatch.setattr(
        "shell_configs.bootstrap.updater.get_tool_by_id", lambda _: None
    )
    monkeypatch.setattr(
        "shell_configs.bootstrap.installer.install_tool",
        lambda force, dry_run: (True, "Installed shell-configs"),
    )
    monkeypatch.setattr(
        "shell_configs.bootstrap.installer.get_tool_config_dir",
        lambda _: test_repo / "config",
    )
    monkeypatch.setattr(
        "shell_configs.languages.load_languages",
        lambda: [Language(name="go", command="go", description="Go")],
    )
    monkeypatch.setattr(
        "shell_configs.languages.is_language_installed", lambda lang: lang.name in log
    )

    def _install_language(lang: Language, dry_run: bool = False) -> tuple[bool, str]:
        log.append(lang.name)
        return True, f"Installed {lang.name}"

    monkeypatch.setattr("shell_configs.languages.install_language", _install_language)
    monkeypatch.setattr(
        "shell_configs.languages.ensure_language_paths", lambda languages: None
    )
    monkeypatch.setattr(
        "shell_configs.cli.components.INSTALL_COMPONENTS", install_components
    )


_SETUP_ARGS = ["setup", "--yes", "--skip-completions", "--skip-scripts"]


@pytest.mark.unit
@pytest.mark.cli
class TestSetupExitCode:
    def test_all_steps_succeed_exits_zero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log: list[str] = []
        _patch_packages(
            monkeypatch, set(), [Package(name="req", required=True)], log=log
        )
        _patch_setup(monkeypatch, test_repo, [], log)

        result = cli_runner.invoke(cli, _SETUP_ARGS)

        assert result.exit_code == 0, result.output
        assert "Setup complete!" in result.output

    def test_required_package_fails_exits_nonzero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log: list[str] = []
        _patch_packages(
            monkeypatch, {"req"}, [Package(name="req", required=True)], log=log
        )
        _patch_setup(monkeypatch, test_repo, [], log)

        result = cli_runner.invoke(cli, _SETUP_ARGS)

        assert result.exit_code == 1
        assert "Setup completed with errors" in result.output

    def test_step3_install_fails_exits_nonzero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log: list[str] = []
        _patch_packages(monkeypatch, set(), [], log=log)
        _patch_setup(
            monkeypatch,
            test_repo,
            [_make_component("broken", "parallel", succeeds=False)],
            log,
        )

        result = cli_runner.invoke(cli, _SETUP_ARGS)

        assert result.exit_code == 1
        assert "Setup completed with errors" in result.output

    def test_no_package_manager_aborts_before_step2(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("shell_configs.packages.get_package_manager", lambda: None)
        _patch_setup(monkeypatch, test_repo, [], [])

        result = cli_runner.invoke(cli, _SETUP_ARGS)

        assert result.exit_code == 1
        assert "No package manager available" in result.output
        assert "Step 2/5" not in result.output

    def test_fresh_machine_installs_optional_packages_after_languages(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Optional packages that need a language (enpass-cli needs Go) must not
        be attempted in Step 1, before Step 3 has installed languages."""
        from shell_configs.cli.components.languages import LanguagesComponent
        from shell_configs.cli.components.packages import (
            OptionalPackagesComponent,
            RequiredPackagesComponent,
        )

        log: list[str] = []
        _patch_packages(
            monkeypatch,
            set(),
            [Package(name="req", required=True), Package(name="enpass-cli")],
            log=log,
        )
        _patch_setup(
            monkeypatch,
            test_repo,
            [
                RequiredPackagesComponent(),
                LanguagesComponent(),
                OptionalPackagesComponent(),
            ],
            log,
        )

        result = cli_runner.invoke(cli, _SETUP_ARGS)

        assert result.exit_code == 0, result.output
        assert log == ["req", "go", "enpass-cli"]


def _patch_upgrade(
    monkeypatch: pytest.MonkeyPatch,
    update_result: tuple[bool, str, bool],
    shell_configs_bin: str | None,
    install_returncode: int = 0,
) -> None:
    from shell_configs.bootstrap.updater import ToolSpec, UpdateInfo

    tool = ToolSpec(
        tool_id="shell-configs",
        package_name="shell-configs",
        display_name="shell-configs",
        get_version=lambda: "1.0.0",
        is_installed=lambda: True,
        github_repo="owner/shell-configs",
    )
    monkeypatch.setattr("shell_configs.bootstrap.UPDATABLE_TOOLS", [tool])
    monkeypatch.setattr(
        "shell_configs.bootstrap.check_tool_updates",
        lambda t: UpdateInfo(
            has_update=True,
            current_version="1.0.0",
            latest_version="2.0.0",
            source="github",
        ),
    )
    monkeypatch.setattr(
        "shell_configs.bootstrap.perform_github_update",
        lambda url, is_self, post_upgrade_cmd: update_result,
    )
    monkeypatch.setattr("shutil.which", lambda name: shell_configs_bin)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, *a, **kw: subprocess.CompletedProcess(cmd, install_returncode),
    )


@pytest.mark.unit
@pytest.mark.cli
class TestUpgradeExitCode:
    def test_self_upgrade_fails_exits_nonzero(
        self, cli_runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_upgrade(monkeypatch, (False, "uv exploded", False), "/bin/sc")

        result = cli_runner.invoke(cli, ["upgrade", "-y"])

        assert result.exit_code == 1
        assert "upgrade failed: uv exploded" in result.output
        assert "Upgrade completed with errors" in result.output

    def test_child_install_fails_after_upgrade_exits_nonzero(
        self, cli_runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_upgrade(monkeypatch, (True, "ok", True), "/bin/sc", install_returncode=1)

        result = cli_runner.invoke(cli, ["upgrade", "-y"])

        assert result.exit_code == 1
        assert (
            "Upgrade succeeded, but applying configs reported errors" in result.output
        )
        assert "Upgrade completed with errors" in result.output

    def test_in_process_install_fails_after_upgrade_exits_nonzero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_upgrade(monkeypatch, (True, "ok", True), None)
        monkeypatch.setattr(
            "shell_configs.cli.components.INSTALL_COMPONENTS",
            [_make_component("broken", "parallel", succeeds=False)],
        )

        result = cli_runner.invoke(cli, ["upgrade", "-y"])

        assert result.exit_code == 1
        assert (
            "Upgrade succeeded, but applying configs reported errors" in result.output
        )

    def test_upgrade_and_install_succeed_exits_zero(
        self, cli_runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_upgrade(monkeypatch, (True, "ok", True), "/bin/sc")

        result = cli_runner.invoke(cli, ["upgrade", "-y"])

        assert result.exit_code == 0, result.output
        assert "completed with errors" not in result.output

    def test_update_check_raises_exits_nonzero(
        self, cli_runner: CliRunner, mock_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_upgrade(monkeypatch, (True, "ok", True), "/bin/sc")

        def _raise(tool: Any) -> None:
            raise OSError("network down")

        monkeypatch.setattr("shell_configs.bootstrap.check_tool_updates", _raise)

        result = cli_runner.invoke(cli, ["upgrade", "-y"])

        assert result.exit_code == 1
        assert "network down" in result.output
        assert "All tools are up to date" not in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestConfigsInstallExitCode:
    def test_install_section_errors_exits_nonzero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from shell_configs.manager import OperationResult

        monkeypatch.setattr(
            "shell_configs.manager.core.ConfigManager.install_section",
            lambda self, *a, **kw: (OperationResult.ERROR, "disk full", None),
        )

        result = cli_runner.invoke(
            cli, ["configs", "install", "--yes", "--shells", "bash"]
        )

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.cli
class TestCleanupExitCode:
    def test_partial_backup_removal_exits_nonzero(
        self,
        cli_runner: CliRunner,
        mock_home: Path,
        test_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        bashrc = mock_home / ".bashrc"
        bashrc.write_text("# bashrc\n")
        backups = [mock_home / f".bashrc.backup.{i}" for i in range(3)]

        monkeypatch.setattr(
            "shell_configs.manager.core.ConfigManager.find_backup_files",
            lambda self, path, backup_dir=None: backups if path == bashrc else [],
        )
        monkeypatch.setattr(
            "shell_configs.manager.core.ConfigManager.cleanup_old_backups",
            lambda self, path, keep=5, backup_dir=None: backups[:1],
        )

        result = cli_runner.invoke(cli, ["cleanup", "--yes", "--keep", "0"])

        assert result.exit_code == 1
        assert "2 of 3 backup files could not be removed" in result.output
