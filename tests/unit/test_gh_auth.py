"""Tests for gh CLI OAuth scope configuration and GhAuthComponent."""

from __future__ import annotations

import sys

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from shell_configs.gh_auth import _DEFAULT_SCOPES, load_desired_scopes


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

        assert result == _DEFAULT_SCOPES

    def test_falls_back_when_yaml_is_none(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text("")

        result = load_desired_scopes(manifest)

        assert result == _DEFAULT_SCOPES

    def test_falls_back_when_scopes_not_list(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text('scopes: "not a list"\n')

        result = load_desired_scopes(manifest)

        assert result == _DEFAULT_SCOPES

    def test_filters_non_string_entries(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_auth.yaml"
        manifest.write_text("scopes:\n  - valid\n  - 123\n  - null\n")

        result = load_desired_scopes(manifest)

        assert result == ["valid"]


@pytest.mark.unit
class TestGhAuthComponent:
    def _make_ctx(self, dry_run: bool = False) -> MagicMock:
        ctx = MagicMock()
        ctx.dry_run = dry_run
        return ctx

    def test_install_dry_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        auth_called = False

        def mock_auth(**kw: object) -> tuple[bool, str]:
            nonlocal auth_called
            auth_called = True
            return (True, "ok")

        monkeypatch.setattr("shell_configs.signing.ensure_gh_auth", mock_auth)

        component = GhAuthComponent()
        result = component.install(self._make_ctx(dry_run=True))

        assert result is True
        assert auth_called is False

    def test_install_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_scopes",
            lambda **kw: (True, "scopes present"),
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

        component = GhAuthComponent()
        result = component.install(self._make_ctx())

        assert result is True

    def test_install_auth_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

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
        result = component.install(self._make_ctx())

        assert result is False
        assert scopes_called is False

    def test_install_scope_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

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
        result = component.install(self._make_ctx())

        assert result is False

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

        component = GhAuthComponent()
        component.status(self._make_ctx())

    def test_diff_missing_scope(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_scopes",
            lambda **kw: (False, "missing scopes"),
        )
        monkeypatch.setattr(
            "shell_configs.gh_auth.load_desired_scopes",
            lambda manifest_path=None: ["admin:public_key", "admin:ssh_signing_key"],
        )

        # guard_subprocess stubs gh → returncode=0, stdout="", stderr=""
        # so current_scopes will be empty → all desired scopes are missing → True
        component = GhAuthComponent()
        result = component.diff(self._make_ctx())

        assert result is True

    def test_diff_all_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (True, "authenticated"),
        )
        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_scopes",
            lambda **kw: (True, "scopes present"),
        )

        component = GhAuthComponent()
        result = component.diff(self._make_ctx())

        assert result is False

    def test_diff_not_authed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from shell_configs.cli.components.gh_auth import GhAuthComponent

        monkeypatch.setattr(
            "shell_configs.signing.ensure_gh_auth",
            lambda **kw: (False, "not logged in"),
        )

        component = GhAuthComponent()
        result = component.diff(self._make_ctx())

        assert result is False
