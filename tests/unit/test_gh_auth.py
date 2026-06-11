"""Tests for gh CLI OAuth scope configuration and GhAuthComponent."""

from __future__ import annotations

import subprocess
import sys

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from shell_configs.gh_auth import _DEFAULT_SCOPES, load_desired_scopes


def _make_result(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.mark.unit
class TestLoadDesiredScopes:
    def test_loads_scopes_from_valid_yaml(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text("scopes:\n  - admin:public_key\n  - workflow\n")

        result = load_desired_scopes(manifest)

        assert result == ["admin:public_key", "workflow"]

    def test_falls_back_when_file_missing(self, tmp_path: Path) -> None:
        manifest = tmp_path / "nonexistent.yaml"

        result = load_desired_scopes(manifest)

        assert result == list(_DEFAULT_SCOPES)

    def test_falls_back_when_yaml_is_none(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text("")

        result = load_desired_scopes(manifest)

        assert result == list(_DEFAULT_SCOPES)

    def test_falls_back_when_scopes_not_list(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text('scopes: "not a list"\n')

        result = load_desired_scopes(manifest)

        assert result == list(_DEFAULT_SCOPES)

    def test_filters_non_string_entries(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text("scopes:\n  - valid\n  - 123\n  - null\n")

        result = load_desired_scopes(manifest)

        assert result == ["valid"]

    def test_falls_back_when_all_entries_non_string(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text("scopes:\n  - 123\n  - 456\n")

        result = load_desired_scopes(manifest)

        assert result == list(_DEFAULT_SCOPES)

    def test_fallback_returns_independent_copies(self, tmp_path: Path) -> None:
        manifest = tmp_path / "nonexistent.yaml"

        result1 = load_desired_scopes(manifest)
        result2 = load_desired_scopes(manifest)

        assert result1 is not result2


@pytest.mark.unit
class TestGetCurrentGhScopes:
    def test_parses_scopes_from_stdout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.gh_auth import get_current_gh_scopes

        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: _make_result(
                0,
                stdout="  - Token scopes: 'admin:public_key', 'workflow'\n",
            ),
        )

        result = get_current_gh_scopes()

        assert result == {"admin:public_key", "workflow"}

    def test_parses_scopes_from_stderr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.gh_auth import get_current_gh_scopes

        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: _make_result(
                0,
                stdout="",
                stderr="  - Token scopes: 'admin:public_key', 'admin:ssh_signing_key'\n",
            ),
        )

        result = get_current_gh_scopes()

        assert result == {"admin:public_key", "admin:ssh_signing_key"}

    def test_returns_empty_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.gh_auth import get_current_gh_scopes

        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: _make_result(1, stderr="not logged in"),
        )

        result = get_current_gh_scopes()

        assert result == set()

    def test_returns_empty_when_no_scopes_line(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.gh_auth import get_current_gh_scopes

        monkeypatch.setattr(
            "shell_configs.fsio.run_quiet",
            lambda *a, **kw: _make_result(0, stdout="Logged in\n"),
        )

        result = get_current_gh_scopes()

        assert result == set()


@pytest.mark.unit
class TestGhAuthComponent:
    def _make_ctx(self, dry_run: bool = False, yes: bool = False) -> MagicMock:
        ctx = MagicMock()
        ctx.dry_run = dry_run
        ctx.yes = yes
        return ctx

    def test_plan_gh_not_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.bootstrap.is_command_available",
            lambda cmd: False,
        )

        component = GhAuthComponent()
        plan = component.plan(self._make_ctx())

        assert plan.has_changes is True
        assert plan.gh_available is False

    def test_plan_not_authed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.bootstrap.is_command_available",
            lambda cmd: True,
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (False, "not logged in"),
        )
        monkeypatch.setattr(
            "shell_configs.gh_auth.load_desired_scopes",
            lambda manifest_path=None: ["admin:public_key", "workflow"],
        )

        component = GhAuthComponent()
        plan = component.plan(self._make_ctx())

        assert plan.has_changes is True
        assert plan.auth_ok is False
        assert plan.missing_scopes == ["admin:public_key", "workflow"]

    def test_plan_all_scopes_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.bootstrap.is_command_available",
            lambda cmd: True,
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.gh_auth.load_desired_scopes",
            lambda manifest_path=None: ["admin:public_key", "workflow"],
        )
        monkeypatch.setattr(
            "shell_configs.gh_auth.get_current_gh_scopes",
            lambda: {"admin:public_key", "workflow", "repo"},
        )

        component = GhAuthComponent()
        plan = component.plan(self._make_ctx())

        assert plan.has_changes is False
        assert plan.auth_ok is True

    def test_plan_partial_scopes_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.bootstrap.is_command_available",
            lambda cmd: True,
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.gh_auth.load_desired_scopes",
            lambda manifest_path=None: [
                "admin:public_key",
                "admin:ssh_signing_key",
                "workflow",
            ],
        )
        monkeypatch.setattr(
            "shell_configs.gh_auth.get_current_gh_scopes",
            lambda: {"admin:public_key", "admin:ssh_signing_key"},
        )

        component = GhAuthComponent()
        plan = component.plan(self._make_ctx())

        assert plan.has_changes is True
        assert plan.auth_ok is True
        assert plan.missing_scopes == ["workflow"]

    def test_apply_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent
        from shell_configs.cli.context import GhAuthPlan

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_scopes",
            lambda **kw: (True, "scopes granted"),
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

        component = GhAuthComponent()
        plan = GhAuthPlan(has_changes=True, missing_scopes=["workflow"])
        result = component.apply(self._make_ctx(), plan)

        assert result is True

    def test_apply_no_changes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent
        from shell_configs.cli.context import GhAuthPlan

        auth_called = False

        def mock_auth(**kw: object) -> tuple[bool, str]:
            nonlocal auth_called
            auth_called = True
            return (True, "ok")

        monkeypatch.setattr("shell_configs.signing.ensure_gh_auth", mock_auth)

        component = GhAuthComponent()
        plan = GhAuthPlan(has_changes=False)
        result = component.apply(self._make_ctx(), plan)

        assert result is True
        assert auth_called is False

    def test_apply_auth_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent
        from shell_configs.cli.context import GhAuthPlan

        scopes_called = False

        def mock_scopes(**kw: object) -> tuple[bool, str]:
            nonlocal scopes_called
            scopes_called = True
            return (True, "ok")

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (False, "not authed"),
        )
        monkeypatch.setattr("shell_configs.signing.ensure_gh_scopes", mock_scopes)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

        component = GhAuthComponent()
        plan = GhAuthPlan(has_changes=True, auth_ok=False, missing_scopes=["workflow"])
        result = component.apply(self._make_ctx(), plan)

        assert result is False
        assert scopes_called is False

    def test_apply_scope_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent
        from shell_configs.cli.context import GhAuthPlan

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_scopes",
            lambda **kw: (False, "missing scopes"),
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

        component = GhAuthComponent()
        plan = GhAuthPlan(has_changes=True, missing_scopes=["workflow"])
        result = component.apply(self._make_ctx(), plan)

        assert result is False

    def test_apply_interactive_depends_on_tty_not_yes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent
        from shell_configs.cli.context import GhAuthPlan

        captured_interactive = None

        def mock_auth(**kw: object) -> tuple[bool, str]:
            nonlocal captured_interactive
            captured_interactive = kw.get("interactive")
            return (True, "ok")

        monkeypatch.setattr("shell_configs.signing.ensure_gh_auth", mock_auth)
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_scopes",
            lambda **kw: (True, "ok"),
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        component = GhAuthComponent()
        plan = GhAuthPlan(has_changes=True, missing_scopes=["workflow"])
        component.apply(self._make_ctx(yes=True), plan)

        assert captured_interactive is True

    def test_status_not_authed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        scopes_called = False

        def mock_scopes(**kw: object) -> tuple[bool, str]:
            nonlocal scopes_called
            scopes_called = True
            return (True, "ok")

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (False, "not logged in"),
        )
        monkeypatch.setattr("shell_configs.signing.ensure_gh_scopes", mock_scopes)

        component = GhAuthComponent()
        component.status(self._make_ctx())

        assert scopes_called is False

    def test_status_scopes_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_scopes",
            lambda **kw: (True, "scopes present"),
        )
        monkeypatch.setattr(
            "shell_configs.gh_auth.load_desired_scopes",
            lambda manifest_path=None: ["admin:public_key"],
        )

        component = GhAuthComponent()
        component.status(self._make_ctx())
