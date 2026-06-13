"""Tests for gh CLI extension management."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shell_configs.gh_extensions import (
    GhExtension,
    command_name,
    install_extension,
    install_from_source,
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

    def test_load_extensions_dict_with_build_path(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text(
            "extensions:\n"
            "  - repo: wpfleger96/gh-infra\n"
            "    build_path: ./cmd/gh-infra/\n"
        )
        result = load_extensions(manifest)
        assert result == [
            GhExtension(repo="wpfleger96/gh-infra", build_path="./cmd/gh-infra/")
        ]

    def test_load_extensions_dict_with_pin_and_build_path(self, tmp_path: Path) -> None:
        manifest = tmp_path / "gh_extensions.yaml"
        manifest.write_text(
            "extensions:\n"
            "  - repo: wpfleger96/gh-infra\n"
            "    pin: main\n"
            "    build_path: ./cmd/gh-infra/\n"
        )
        result = load_extensions(manifest)
        assert result == [
            GhExtension(
                repo="wpfleger96/gh-infra", pin="main", build_path="./cmd/gh-infra/"
            )
        ]


@pytest.mark.unit
class TestCommandName:
    def test_gh_prefix_stripped(self) -> None:
        assert command_name("wpfleger96/gh-infra") == "infra"

    def test_no_gh_prefix(self) -> None:
        assert command_name("github/copilot") == "copilot"

    def test_bare_repo_name(self) -> None:
        assert command_name("owner/gh-dash") == "dash"


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

    def test_list_installed_local_extension(self) -> None:
        stdout = "gh infra\t\t\n"
        mock_result = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ):
            result = list_installed()
        assert result == {"infra": None}

    def test_list_installed_mixed_local_and_standard(self) -> None:
        stdout = "gh infra\t\t\ngh copilot\tgithub/gh-copilot\tv1.0.0\n"
        mock_result = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch(
            "shell_configs.gh_extensions.subprocess.run", return_value=mock_result
        ):
            result = list_installed()
        assert result == {"infra": None, "github/gh-copilot": "v1.0.0"}

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
class TestInstallFromSource:
    def test_invalid_build_path_rejected(self) -> None:
        success, msg = install_from_source("wpfleger96/gh-infra", "../evil/path")
        assert success is False
        assert "Rejected invalid build_path" in msg

    def test_flag_injection_build_path_rejected(self) -> None:
        success, msg = install_from_source("wpfleger96/gh-infra", "-buildmode=plugin")
        assert success is False
        assert "Rejected invalid build_path" in msg

    def test_dry_run(self) -> None:
        with patch("shell_configs.gh_extensions._get_extensions_dir") as mock_dir:
            mock_dir.return_value = Path("/fake/extensions")
            success, msg = install_from_source(
                "wpfleger96/gh-infra", "./cmd/gh-infra/", dry_run=True
            )
        assert success is True
        assert "Would build" in msg

    def test_go_missing(self) -> None:
        with (
            patch("shell_configs.gh_extensions._get_extensions_dir") as mock_dir,
            patch("shell_configs.gh_extensions.shutil.which", return_value=None),
        ):
            mock_dir.return_value = Path("/fake/extensions")
            success, msg = install_from_source("wpfleger96/gh-infra", "./cmd/gh-infra/")
        assert success is False
        assert "go not found" in msg

    def test_clone_failure(self) -> None:
        clone_fail = MagicMock(returncode=1, stdout="", stderr="clone error")
        with (
            patch("shell_configs.gh_extensions._get_extensions_dir") as mock_dir,
            patch(
                "shell_configs.gh_extensions.shutil.which", return_value="/usr/bin/go"
            ),
            patch(
                "shell_configs.gh_extensions.tempfile.mkdtemp",
                return_value="/tmp/gh-ext-build-xxx",
            ),
            patch(
                "shell_configs.gh_extensions.subprocess.run", return_value=clone_fail
            ),
            patch("shell_configs.gh_extensions.shutil.rmtree"),
        ):
            mock_dir.return_value = Path("/fake/extensions")
            success, msg = install_from_source("wpfleger96/gh-infra", "./cmd/gh-infra/")
        assert success is False
        assert "Failed to clone" in msg

    def test_build_failure_preserves_existing_extension(self, tmp_path: Path) -> None:
        clone_ok = MagicMock(returncode=0, stdout="", stderr="")
        build_fail = MagicMock(returncode=1, stdout="", stderr="build error")

        with (
            patch(
                "shell_configs.gh_extensions._get_extensions_dir",
                return_value=tmp_path / "extensions",
            ),
            patch(
                "shell_configs.gh_extensions.shutil.which", return_value="/usr/bin/go"
            ),
            patch(
                "shell_configs.gh_extensions.tempfile.mkdtemp",
                return_value=str(tmp_path / "clone"),
            ),
            patch(
                "shell_configs.gh_extensions.subprocess.run",
                side_effect=[clone_ok, build_fail],
            ),
            patch("shell_configs.gh_extensions.shutil.rmtree"),
            patch("shell_configs.gh_extensions._remove_extension") as mock_remove,
        ):
            success, msg = install_from_source("wpfleger96/gh-infra", "./cmd/gh-infra/")
        assert success is False
        assert "Failed to build" in msg
        mock_remove.assert_not_called()

    def test_success(self, tmp_path: Path) -> None:
        clone_ok = MagicMock(returncode=0, stdout="", stderr="")
        build_ok = MagicMock(returncode=0, stdout="", stderr="")

        staged_dir = tmp_path / "staged"
        staged_dir.mkdir()

        def fake_move(src: str, dst: str) -> None:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            Path(dst).touch()

        with (
            patch(
                "shell_configs.gh_extensions._get_extensions_dir",
                return_value=tmp_path / "extensions",
            ),
            patch(
                "shell_configs.gh_extensions.shutil.which", return_value="/usr/bin/go"
            ),
            patch(
                "shell_configs.gh_extensions.tempfile.mkdtemp",
                side_effect=[str(tmp_path / "clone"), str(staged_dir)],
            ),
            patch(
                "shell_configs.gh_extensions.subprocess.run",
                side_effect=[clone_ok, build_ok],
            ),
            patch("shell_configs.gh_extensions._remove_extension") as mock_remove,
            patch("shell_configs.gh_extensions.shutil.move", side_effect=fake_move),
            patch("shell_configs.gh_extensions.shutil.rmtree"),
        ):
            success, msg = install_from_source("wpfleger96/gh-infra", "./cmd/gh-infra/")
        assert success is True
        assert "Built and installed" in msg
        mock_remove.assert_called_once_with("infra")

    def test_clone_with_pin(self, tmp_path: Path) -> None:
        clone_ok = MagicMock(returncode=0, stdout="", stderr="")
        build_ok = MagicMock(returncode=0, stdout="", stderr="")

        def fake_move(src: str, dst: str) -> None:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            Path(dst).touch()

        with (
            patch(
                "shell_configs.gh_extensions._get_extensions_dir",
                return_value=tmp_path / "extensions",
            ),
            patch(
                "shell_configs.gh_extensions.shutil.which", return_value="/usr/bin/go"
            ),
            patch(
                "shell_configs.gh_extensions.tempfile.mkdtemp",
                side_effect=[str(tmp_path / "clone"), str(tmp_path / "staged")],
            ),
            patch(
                "shell_configs.gh_extensions.subprocess.run",
                side_effect=[clone_ok, build_ok],
            ) as mock_run,
            patch("shell_configs.gh_extensions._remove_extension"),
            patch("shell_configs.gh_extensions.shutil.move", side_effect=fake_move),
            patch("shell_configs.gh_extensions.shutil.rmtree"),
        ):
            success, msg = install_from_source(
                "wpfleger96/gh-infra", "./cmd/gh-infra/", pin="dev"
            )
        assert success is True
        clone_call = mock_run.call_args_list[0]
        assert clone_call[0][0] == [
            "git",
            "clone",
            "--depth",
            "1",
            "-b",
            "dev",
            "https://github.com/wpfleger96/gh-infra.git",
            str(tmp_path / "clone"),
        ]


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

    def test_install_extension_conflict_uninstall_retry(self) -> None:
        conflict = MagicMock(
            returncode=1,
            stdout="",
            stderr="there is already an installed extension that provides the command",
        )
        remove_ok = MagicMock(returncode=0, stdout="", stderr="")
        retry_ok = MagicMock(returncode=0, stdout="", stderr="")

        with patch(
            "shell_configs.gh_extensions.subprocess.run",
            side_effect=[conflict, remove_ok, retry_ok],
        ):
            success, msg = install_extension("babarot/gh-infra")
        assert success is True
        assert msg == "Installed babarot/gh-infra"

    def test_install_extension_conflict_retry_failure(self) -> None:
        conflict = MagicMock(
            returncode=1,
            stdout="",
            stderr="there is already an installed extension that provides the command",
        )
        remove_ok = MagicMock(returncode=0, stdout="", stderr="")
        retry_fail = MagicMock(returncode=1, stdout="", stderr="still broken")

        with patch(
            "shell_configs.gh_extensions.subprocess.run",
            side_effect=[conflict, remove_ok, retry_fail],
        ):
            success, msg = install_extension("babarot/gh-infra")
        assert success is False
        assert "still broken" in msg

    def test_install_extension_with_build_path_delegates_to_source(self) -> None:
        with patch(
            "shell_configs.gh_extensions.install_from_source",
            return_value=(
                True,
                "Built and installed wpfleger96/gh-infra from source",
            ),
        ) as mock_source:
            success, msg = install_extension(
                "wpfleger96/gh-infra", build_path="./cmd/gh-infra/"
            )
        mock_source.assert_called_once_with(
            "wpfleger96/gh-infra", "./cmd/gh-infra/", pin=None, dry_run=False
        )
        assert success is True

    def test_install_extension_with_build_path_dry_run(self) -> None:
        with patch(
            "shell_configs.gh_extensions.install_from_source",
            return_value=(True, "Would build wpfleger96/gh-infra from source"),
        ) as mock_source:
            success, msg = install_extension(
                "wpfleger96/gh-infra", build_path="./cmd/gh-infra/", dry_run=True
            )
        mock_source.assert_called_once_with(
            "wpfleger96/gh-infra", "./cmd/gh-infra/", pin=None, dry_run=True
        )
        assert success is True

    def test_install_extension_with_pin_and_build_path(self) -> None:
        with patch(
            "shell_configs.gh_extensions.install_from_source",
            return_value=(True, "Built and installed wpfleger96/gh-infra from source"),
        ) as mock_source:
            success, msg = install_extension(
                "wpfleger96/gh-infra", pin="dev", build_path="./cmd/gh-infra/"
            )
        mock_source.assert_called_once_with(
            "wpfleger96/gh-infra", "./cmd/gh-infra/", pin="dev", dry_run=False
        )
        assert success is True


@pytest.mark.unit
class TestGhExtensionsComponent:
    @pytest.fixture(autouse=True)
    def _gh_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shell_configs.bootstrap.is_command_available", lambda cmd: True
        )

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
                ctx = self._make_ctx()
                result = component.apply(ctx, component.plan(ctx))
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
                    ctx = self._make_ctx()
                    result = component.apply(ctx, component.plan(ctx))
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
                    ctx = self._make_ctx()
                    result = component.apply(ctx, component.plan(ctx))
        assert result is False

    def test_component_install_dry_run(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch("shell_configs.gh_extensions.list_installed", return_value={}):
                with patch("shell_configs.gh_extensions.subprocess.run") as mock_run:
                    component = GhExtensionsComponent()
                    ctx = self._make_ctx(dry_run=True)
                    result = component.apply(ctx, component.plan(ctx))
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
                result = component.plan(self._make_ctx()).has_changes
        assert result is False

    def test_component_diff_with_missing(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="babarot/gh-infra")]

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch("shell_configs.gh_extensions.list_installed", return_value={}):
                component = GhExtensionsComponent()
                result = component.plan(self._make_ctx()).has_changes
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
                result = component.plan(self._make_ctx()).has_changes
        assert result is True

    def test_plan_local_extension_matched_by_command_name(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="wpfleger96/gh-infra")]
        installed = {"infra": None}

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch(
                "shell_configs.gh_extensions.list_installed", return_value=installed
            ):
                component = GhExtensionsComponent()
                plan = component.plan(self._make_ctx())
        assert plan.missing == []
        assert plan.extra == set()
        assert plan.has_changes is False

    def test_plan_local_extension_not_marked_as_extra(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [GhExtension(repo="wpfleger96/gh-infra")]
        installed = {"infra": None, "github/gh-copilot": "v1.0.0"}

        with patch("shell_configs.gh_extensions.load_extensions", return_value=desired):
            with patch(
                "shell_configs.gh_extensions.list_installed", return_value=installed
            ):
                component = GhExtensionsComponent()
                plan = component.plan(self._make_ctx())
        assert plan.missing == []
        assert plan.extra == {"github/gh-copilot"}

    def test_component_install_with_build_path(self) -> None:
        from shell_configs.cli.components.gh_extensions import GhExtensionsComponent

        desired = [
            GhExtension(repo="wpfleger96/gh-infra", build_path="./cmd/gh-infra/")
        ]

        with (
            patch("shell_configs.gh_extensions.load_extensions", return_value=desired),
            patch("shell_configs.gh_extensions.list_installed", return_value={}),
            patch(
                "shell_configs.gh_extensions.install_from_source",
                return_value=(
                    True,
                    "Built and installed wpfleger96/gh-infra from source",
                ),
            ) as mock_source,
        ):
            component = GhExtensionsComponent()
            ctx = self._make_ctx()
            result = component.apply(ctx, component.plan(ctx))
        assert result is True
        mock_source.assert_called_once_with(
            "wpfleger96/gh-infra", "./cmd/gh-infra/", pin=None, dry_run=False
        )
