"""Tests for VS Code Local (Windows-side) extension management on WSL."""

import subprocess

from unittest.mock import patch

import pytest

from shell_configs.extensions import (
    CliExtensionInvoker,
    ExtensionManager,
    ExtensionResultStatus,
    PowerShellExtensionInvoker,
)
from shell_configs.platform import Platform
from shell_configs.shells.vscode import VSCodeLocalShell


@pytest.mark.unit
class TestCliExtensionInvoker:
    """Tests for CliExtensionInvoker command generation."""

    def test_list_command(self):
        invoker = CliExtensionInvoker("code")
        assert invoker.list_command() == ["code", "--list-extensions"]

    def test_install_command(self):
        invoker = CliExtensionInvoker("code")
        assert invoker.install_command("golang.go") == [
            "code",
            "--install-extension",
            "golang.go",
            "--force",
        ]

    def test_uninstall_command(self):
        invoker = CliExtensionInvoker("cursor")
        assert invoker.uninstall_command("golang.go") == [
            "cursor",
            "--uninstall-extension",
            "golang.go",
        ]

    def test_display_name(self):
        invoker = CliExtensionInvoker("code")
        assert invoker.display_name == "code"


@pytest.mark.unit
class TestPowerShellExtensionInvoker:
    """Tests for PowerShellExtensionInvoker command generation."""

    WIN_PATH = "C:\\Users\\testuser\\AppData\\Local\\Programs\\Microsoft VS Code\\bin\\code.cmd"

    def test_list_command_structure(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        cmd = invoker.list_command()
        assert cmd[0] == "powershell.exe"
        assert "-NoProfile" in cmd
        assert "-NonInteractive" in cmd
        assert "--list-extensions" in cmd[-1]

    def test_install_command_embeds_ext_id(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        cmd = invoker.install_command("golang.go")
        assert "--install-extension golang.go --force" in cmd[-1]

    def test_uninstall_command_embeds_ext_id(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        cmd = invoker.uninstall_command("golang.go")
        assert "--uninstall-extension golang.go" in cmd[-1]

    def test_commands_contain_error_action_preference(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        cmd = invoker.list_command()
        assert "SilentlyContinue" in cmd[-1]

    def test_commands_suppress_stderr(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        cmd = invoker.list_command()
        assert "2>$null" in cmd[-1]

    def test_commands_propagate_exit_code(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        cmd = invoker.list_command()
        assert "$LASTEXITCODE" in cmd[-1]

    def test_display_name(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        assert invoker.display_name == "powershell.exe"

    def test_win_path_embedded_in_command(self):
        invoker = PowerShellExtensionInvoker(self.WIN_PATH)
        cmd = invoker.list_command()
        assert self.WIN_PATH in cmd[-1]


@pytest.mark.unit
class TestVSCodeLocalShell:
    """Tests for VSCodeLocalShell class."""

    def test_name(self):
        shell = VSCodeLocalShell()
        assert shell.name == "vscode-local"

    def test_display_name(self):
        shell = VSCodeLocalShell()
        assert shell.display_name == "VS Code (Local)"

    def test_get_extension_cli_returns_none(self):
        shell = VSCodeLocalShell()
        assert shell.get_extension_cli() is None

    def test_returns_none_on_non_wsl(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.LINUX,
        )
        shell = VSCodeLocalShell()
        assert shell.get_extension_invoker() is None

    def test_returns_invoker_on_wsl(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_windows_username",
            lambda: "testuser",
        )
        code_cmd = (
            tmp_path
            / "Users"
            / "testuser"
            / "AppData"
            / "Local"
            / "Programs"
            / "Microsoft VS Code"
            / "bin"
            / "code.cmd"
        )
        code_cmd.parent.mkdir(parents=True)
        code_cmd.touch()

        monkeypatch.setattr(
            "shell_configs.shells.vscode.Path",
            lambda p: tmp_path / p.removeprefix("/mnt/c/"),
        )

        shell = VSCodeLocalShell()
        invoker = shell.get_extension_invoker()
        assert isinstance(invoker, PowerShellExtensionInvoker)

    def test_returns_none_when_username_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_windows_username",
            lambda: "",
        )
        shell = VSCodeLocalShell()
        assert shell.get_extension_invoker() is None

    def test_returns_none_when_code_cmd_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "shell_configs.shells.vscode.is_platform",
            lambda p: p == Platform.WSL,
        )
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_windows_username",
            lambda: "testuser",
        )
        shell = VSCodeLocalShell()
        assert shell.get_extension_invoker() is None

    def test_extension_list_paths(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "shell_configs.shells.vscode.get_config_dir", lambda: tmp_path
        )
        shell = VSCodeLocalShell()
        paths = shell.get_extension_list_paths()
        assert len(paths) == 1
        assert paths[0] == tmp_path / "vscode" / "extensions-local.txt"


@pytest.mark.unit
class TestExtensionManagerWithInvoker:
    """Tests for ExtensionManager methods using ExtensionInvoker."""

    def test_get_installed_via_invoker(self):
        invoker = CliExtensionInvoker("code")
        manager = ExtensionManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="golang.go\nrust-lang.rust-analyzer\n"
            )
            result = manager.get_installed_extensions(invoker=invoker)

        assert result == {"golang.go", "rust-lang.rust-analyzer"}
        mock_run.assert_called_once_with(
            ["code", "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_get_installed_via_invoker_returns_none_on_failure(self):
        invoker = CliExtensionInvoker("code")
        manager = ExtensionManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="error"
            )
            result = manager.get_installed_extensions(invoker=invoker)

        assert result is None

    def test_invoker_takes_precedence_over_cli_command(self):
        invoker = CliExtensionInvoker("custom-code")
        manager = ExtensionManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="golang.go\n"
            )
            manager.get_installed_extensions("code", invoker=invoker)

        assert mock_run.call_args[0][0] == ["custom-code", "--list-extensions"]

    def test_install_via_invoker(self):
        invoker = CliExtensionInvoker("code")
        manager = ExtensionManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="Installed"
            )
            results = manager.install_extensions(
                extensions={"golang.go"}, invoker=invoker
            )

        assert len(results) == 1
        assert results[0].success
        assert results[0].extension_id == "golang.go"

    def test_uninstall_via_invoker(self):
        invoker = CliExtensionInvoker("code")
        manager = ExtensionManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="Uninstalled"
            )
            results = manager.uninstall_extensions(
                extensions={"golang.go"}, invoker=invoker
            )

        assert len(results) == 1
        assert results[0].success
        assert results[0].extension_id == "golang.go"

    def test_install_via_invoker_handles_failure(self):
        invoker = CliExtensionInvoker("code")
        manager = ExtensionManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="marketplace error"
            )
            results = manager.install_extensions(
                extensions={"bad.ext"}, invoker=invoker
            )

        assert len(results) == 1
        assert not results[0].success
        assert results[0].status == ExtensionResultStatus.FAILED

    def test_powershell_invoker_integration(self):
        win_path = "C:\\Users\\test\\AppData\\Local\\Programs\\Microsoft VS Code\\bin\\code.cmd"
        invoker = PowerShellExtensionInvoker(win_path)
        manager = ExtensionManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="hashicorp.terraform\nms-vscode.powershell\n",
            )
            result = manager.get_installed_extensions(invoker=invoker)

        assert result == {"hashicorp.terraform", "ms-vscode.powershell"}
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[0] == "powershell.exe"
        assert win_path in called_cmd[-1]


@pytest.mark.unit
class TestRegistryWSLConditional:
    """Tests for conditional registration of VSCodeLocalShell."""

    def test_vscode_local_registered_on_wsl(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.WSL,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("vscode-local") is not None
        assert isinstance(registry.get("vscode-local"), VSCodeLocalShell)

    def test_vscode_local_not_registered_on_linux(self, monkeypatch, mock_home):
        monkeypatch.setattr(
            "shell_configs.platform.is_platform",
            lambda p: p == Platform.LINUX,
        )
        from shell_configs.shells.registry import ShellRegistry

        registry = ShellRegistry()
        assert registry.get("vscode-local") is None


@pytest.mark.unit
class TestBuiltinExtensionsVscodeLocal:
    """Tests for vscode-local builtin extension filtering."""

    def test_vscode_local_builtins(self):
        from shell_configs.extensions import get_builtin_extensions

        builtins = get_builtin_extensions("vscode-local")
        assert "ms-vscode-remote.remote-wsl" in builtins

    def test_vscode_local_builtins_includes_copilot_chat(self):
        from shell_configs.extensions import get_builtin_extensions

        builtins = get_builtin_extensions("vscode-local")
        assert "github.copilot-chat" in builtins

    def test_compute_diff_ignores_wsl_extension(self):
        manager = ExtensionManager()
        desired = {"ms-vscode.powershell", "ms-vscode-remote.remote-wsl"}
        installed = {"ms-vscode.powershell", "ms-vscode-remote.remote-wsl"}
        diff = manager.compute_diff(desired, installed, shell_name="vscode-local")
        assert "ms-vscode-remote.remote-wsl" in diff.ignored
        assert not diff.missing
        assert not diff.extra

    def test_compute_diff_ignores_copilot_chat(self):
        manager = ExtensionManager()
        desired = {"ms-vscode.powershell"}
        installed = {"ms-vscode.powershell", "github.copilot-chat"}
        diff = manager.compute_diff(desired, installed, shell_name="vscode-local")
        assert "github.copilot-chat" not in diff.extra
        assert not diff.extra
