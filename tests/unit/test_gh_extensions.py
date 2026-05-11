"""Tests for gh CLI extension management."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shell_configs.gh_extensions import (
    GhExtension,
    install_extension,
    list_installed,
    load_extensions,
)


@pytest.mark.unit
class TestLoadExtensions:
    def test_load_extensions(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text(
            "extensions:\n  - repo: babarot/gh-infra\n  - repo: github/gh-copilot\n"
        )
        result = load_extensions(manifest)
        assert result == [
            GhExtension(repo="babarot/gh-infra"),
            GhExtension(repo="github/gh-copilot"),
        ]

    def test_load_extensions_empty(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text("{}\n")
        result = load_extensions(manifest)
        assert result == []

    def test_load_extensions_missing_file(self, tmp_path: Path) -> None:
        manifest = tmp_path / "nonexistent.yaml"
        result = load_extensions(manifest)
        assert result == []

    def test_load_extensions_none_value(self, tmp_path: Path) -> None:
        # YAML `extensions:` with no value safe_load returns {"extensions": None}
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text("extensions:\n")
        result = load_extensions(manifest)
        assert result == []

    def test_load_extensions_invalid_names(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text(
            "extensions:\n"
            "  - https://github.com/owner/repo\n"
            "  - /absolute/path\n"
            "  - just-a-name\n"
            "  - 42\n"
            "  - repo: valid/extension\n"
        )
        result = load_extensions(manifest)
        assert result == [GhExtension(repo="valid/extension")]

    def test_load_extensions_string_shorthand(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text("extensions:\n  - babarot/gh-infra\n")
        result = load_extensions(manifest)
        assert result == [GhExtension(repo="babarot/gh-infra", pin=None)]

    def test_load_extensions_dict_with_pin(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text(
            "extensions:\n  - repo: babarot/gh-infra\n    pin: v0.13.0\n"
        )
        result = load_extensions(manifest)
        assert result == [GhExtension(repo="babarot/gh-infra", pin="v0.13.0")]


@pytest.mark.unit
class TestListInstalled:
    def test_list_installed_parses_output(self) -> None:
        stdout = "gh infra\tbabarot/gh-infra\tv0.13.0\ngh copilot\tgithub/gh-copilot\tv1.0.0\n"
        mock_result = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ):
            result = list_installed()
        assert result == {"babarot/gh-infra": "v0.13.0", "github/gh-copilot": "v1.0.0"}

    def test_list_installed_empty(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ):
            result = list_installed()
        assert result == {}

    def test_list_installed_command_fails(self) -> None:
        mock_result = MagicMock(returncode=1, stdout="", stderr="error")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ):
            result = list_installed()
        assert result == {}

    def test_list_installed_timeout(self) -> None:
        import subprocess as _subprocess

        with patch(
            "shell_configs.gh_extensions.subprocess.run",
            side_effect=_subprocess.TimeoutExpired(cmd=["gh"], timeout=30),
        ):
            result = list_installed()
        assert result == {}


@pytest.mark.unit
class TestInstallExtension:
    def test_install_extension_success(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ) as mock_run:
            success, msg = install_extension("babarot/gh-infra")
        assert success is True
        assert msg == "Installed babarot/gh-infra"
        mock_run.assert_called_once_with(
            ["gh", "extension", "install", "babarot/gh-infra"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_install_extension_with_pin(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ) as mock_run:
            success, msg = install_extension("babarot/gh-infra", pin="v0.13.0")
        assert success is True
        mock_run.assert_called_once_with(
            ["gh", "extension", "install", "babarot/gh-infra", "--pin", "v0.13.0"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_install_extension_failure(self) -> None:
        mock_result = MagicMock(returncode=1, stdout="", stderr="not found")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ):
            success, msg = install_extension("babarot/gh-infra")
        assert success is False
        assert "Failed to install babarot/gh-infra" in msg
        assert "not found" in msg

    def test_install_extension_dry_run(self) -> None:
        with patch("shell_configs.gh_extensions.subprocess.run") as mock_run:
            success, msg = install_extension("babarot/gh-infra", dry_run=True)
        mock_run.assert_not_called()
        assert success is True
        assert msg == "Would install babarot/gh-infra"

    def test_install_extension_invalid_name(self) -> None:
        with patch("shell_configs.gh_extensions.subprocess.run") as mock_run:
            success, msg = install_extension("https://github.com/owner/repo")
        mock_run.assert_not_called()
        assert success is False
        assert "Rejected invalid extension name" in msg

    def test_install_extension_gh_not_found(self) -> None:
        with patch(
            "shell_configs.gh_extensions.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            success, msg = install_extension("babarot/gh-infra")
        assert success is False
        assert "gh CLI not found" in msg

    def test_install_extension_timeout(self) -> None:
        import subprocess as _subprocess

        with patch(
            "shell_configs.gh_extensions.subprocess.run",
            side_effect=_subprocess.TimeoutExpired(cmd=["gh"], timeout=30),
        ):
            success, msg = install_extension("babarot/gh-infra")
        assert success is False
        assert "timed out" in msg


@pytest.mark.unit
class TestGhExtensionsComponent:
    def _make_ctx(self, dry_run: bool = False) -> MagicMock:
        ctx = MagicMock()
        ctx.dry_run = dry_run
        return ctx

    def test_component_install_all_synced(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]
        installed = {"babarot/gh-infra": "v0.13.0"}

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch(
                "shell_configs.gh_extensions.list_installed", return_value=installed
            ):
                component = GhExtensionsComponent()
                result = component.install(self._make_ctx())
        assert result is True

    def test_component_install_missing(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]
        install_result = MagicMock(returncode=0, stdout="", stderr="")

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch("shell_configs.gh_extensions.list_installed", return_value={}):
                with patch(
                    "shell_configs.gh_extensions.subprocess.run",
                    return_value=install_result,
                ) as mock_run:
                    component = GhExtensionsComponent()
                    result = component.install(self._make_ctx())
        assert result is True
        mock_run.assert_called_once_with(
            ["gh", "extension", "install", "babarot/gh-infra"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_component_install_failure(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]
        fail_result = MagicMock(returncode=1, stdout="", stderr="error")

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch("shell_configs.gh_extensions.list_installed", return_value={}):
                with patch(
                    "shell_configs.gh_extensions.subprocess.run",
                    return_value=fail_result,
                ):
                    component = GhExtensionsComponent()
                    result = component.install(self._make_ctx())
        assert result is False

    def test_component_install_dry_run(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch("shell_configs.gh_extensions.list_installed", return_value={}):
                with patch("shell_configs.gh_extensions.subprocess.run") as mock_run:
                    component = GhExtensionsComponent()
                    result = component.install(self._make_ctx(dry_run=True))
        mock_run.assert_not_called()
        # dry_run path still returns True (no failures, just skipped)
        assert result is True

    def test_component_status_all_installed(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]
        installed = {"babarot/gh-infra": "v0.13.0"}

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch(
                "shell_configs.gh_extensions.list_installed", return_value=installed
            ):
                component = GhExtensionsComponent()
                component.status(self._make_ctx())

    def test_component_status_missing(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch("shell_configs.gh_extensions.list_installed", return_value={}):
                component = GhExtensionsComponent()
                # Verify it runs without error
                component.status(self._make_ctx())

    def test_component_status_with_extra(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]
        installed = {
            "babarot/gh-infra": "v0.13.0",
            "cli/cli": "v2.0.0",  # unmanaged
        }

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch(
                "shell_configs.gh_extensions.list_installed", return_value=installed
            ):
                component = GhExtensionsComponent()
                # Should not raise; extra extensions noted in output
                component.status(self._make_ctx())

    def test_component_diff_no_diff(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]
        installed = {"babarot/gh-infra": "v0.13.0"}

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch(
                "shell_configs.gh_extensions.list_installed", return_value=installed
            ):
                component = GhExtensionsComponent()
                result = component.diff(self._make_ctx())
        assert result is False

    def test_component_diff_with_missing(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch("shell_configs.gh_extensions.list_installed", return_value={}):
                component = GhExtensionsComponent()
                result = component.diff(self._make_ctx())
        assert result is True

    def test_component_diff_with_extra(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]
        installed = {
            "babarot/gh-infra": "v0.13.0",
            "cli/cli": "v2.0.0",  # unmanaged extra
        }

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch(
                "shell_configs.gh_extensions.list_installed", return_value=installed
            ):
                component = GhExtensionsComponent()
                result = component.diff(self._make_ctx())
        assert result is True
