"""Tests for component uninstall() methods."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = True
    ctx.profile = None
    ctx.registry = MagicMock()
    return ctx


@pytest.mark.unit
class TestExtensionsComponentUninstall:
    def test_skips_shell_without_cli(self):
        from shell_configs.cli.components.extensions import ExtensionsComponent

        mock_shell = MagicMock()
        mock_shell.get_extension_invoker.return_value = None
        mock_shell.get_extension_cli.return_value = None

        ctx = _make_ctx()
        with (
            patch(
                "shell_configs.cli.helpers._get_extension_shells",
                return_value=[mock_shell],
            ),
            patch("shell_configs.extensions.ExtensionManager") as MockEM,
        ):
            ExtensionsComponent().uninstall(ctx)
            MockEM.return_value.uninstall_extensions.assert_not_called()

    def test_skips_shell_with_empty_desired_extensions(self):
        from shell_configs.cli.components.extensions import ExtensionsComponent

        mock_shell = MagicMock()
        mock_shell.get_extension_invoker.return_value = MagicMock()
        mock_shell.get_extension_cli.return_value = "code"
        mock_shell.name = "vscode"
        mock_shell.get_extension_list_paths.return_value = []

        ctx = _make_ctx()
        with (
            patch(
                "shell_configs.cli.helpers._get_extension_shells",
                return_value=[mock_shell],
            ),
            patch("shell_configs.extensions.ExtensionManager") as MockEM,
        ):
            mock_em = MockEM.return_value
            mock_em.load_desired_extensions.return_value = set()
            ExtensionsComponent().uninstall(ctx)

        mock_em.uninstall_extensions.assert_not_called()


@pytest.mark.unit
class TestGhExtensionsComponentUninstall:
    def test_skips_when_gh_not_available(self):
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        ctx = _make_ctx()
        with (
            patch("shell_configs.bootstrap.is_command_available", return_value=False),
            patch("shell_configs.display.print_warning") as mock_warn,
        ):
            GhExtensionsComponent().uninstall(ctx)

        mock_warn.assert_called_once()

    def test_skips_extension_not_in_installed(self):
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        mock_ext = MagicMock()
        mock_ext.repo = "owner/gh-test"

        ctx = _make_ctx()
        with (
            patch("shell_configs.bootstrap.is_command_available", return_value=True),
            patch(
                "shell_configs.gh_extensions.load_extensions", return_value=[mock_ext]
            ),
            patch(
                "shell_configs.gh_extensions.list_installed",
                return_value={"unrelated": None},
            ),
            patch("shell_configs.gh_extensions.command_name", return_value="test"),
            patch(
                "shell_configs.gh_extensions._remove_extension", return_value=True
            ) as mock_remove,
        ):
            GhExtensionsComponent().uninstall(ctx)

        mock_remove.assert_not_called()

    def test_uninstall_matches_by_repo_key(self):
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        mock_ext = MagicMock()
        mock_ext.repo = "owner/gh-test"

        ctx = _make_ctx()
        with (
            patch("shell_configs.bootstrap.is_command_available", return_value=True),
            patch(
                "shell_configs.gh_extensions.load_extensions", return_value=[mock_ext]
            ),
            patch(
                "shell_configs.gh_extensions.list_installed",
                return_value={"owner/gh-test": None},
            ),
            patch(
                "shell_configs.gh_extensions.command_name",
                return_value="test",
            ),
            patch(
                "shell_configs.gh_extensions._remove_extension",
                return_value=True,
            ) as mock_remove,
        ):
            GhExtensionsComponent().uninstall(ctx)

        mock_remove.assert_called_once_with("test")


@pytest.mark.unit
class TestCompletionsComponentUninstall:
    def test_no_shell_detected_returns_early(self):
        from shell_configs.cli.components.completions import CompletionsComponent

        ctx = _make_ctx()
        with (
            patch("shell_configs.completions.detect_shell", return_value=None),
            patch("shell_configs.completions.find_config_file") as mock_find,
        ):
            CompletionsComponent().uninstall(ctx)

        mock_find.assert_not_called()

    def test_no_config_file_returns_early(self):
        from shell_configs.cli.components.completions import CompletionsComponent

        ctx = _make_ctx()
        with (
            patch("shell_configs.completions.detect_shell", return_value="zsh"),
            patch("shell_configs.completions.find_config_file", return_value=None),
            patch("shell_configs.completions.uninstall_completion") as mock_uninstall,
        ):
            CompletionsComponent().uninstall(ctx)

        mock_uninstall.assert_not_called()
