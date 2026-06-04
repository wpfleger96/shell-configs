"""AI coding agent management (Claude Code, Codex, Gemini, Goose, Amp)."""

from __future__ import annotations

import shutil
import subprocess

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from shell_configs.config import get_config_dir
from shell_configs.platform import Platform, is_platform


@dataclass(frozen=True)
class AgentInstallConfig:
    method: str  # "npm"
    package: str | None = None


@dataclass(frozen=True)
class Agent:
    name: str
    command: str
    description: str
    check_path: str | None = None
    install_cmd: str | None = None
    uninstall_cmd: str | None = None
    macos: AgentInstallConfig | None = None
    linux: AgentInstallConfig | None = None
    windows: AgentInstallConfig | None = None


def load_agents(manifest_path: Path | None = None) -> list[Agent]:
    """Load desired agents from the YAML manifest."""
    path = manifest_path or get_config_dir() / "agents.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    entries = data.get("agents") or []
    if not isinstance(entries, list):
        return []

    result: list[Agent] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        command = entry.get("command", "")
        if not name or not command:
            continue

        macos_cfg: AgentInstallConfig | None = None
        linux_cfg: AgentInstallConfig | None = None

        if isinstance(entry.get("macos"), dict):
            m: dict[str, Any] = entry["macos"]
            macos_cfg = AgentInstallConfig(
                method=m.get("method", ""),
                package=m.get("package") or None,
            )
        if isinstance(entry.get("linux"), dict):
            li: dict[str, Any] = entry["linux"]
            linux_cfg = AgentInstallConfig(
                method=li.get("method", ""),
                package=li.get("package") or None,
            )

        windows_cfg: AgentInstallConfig | None = None
        if isinstance(entry.get("windows"), dict):
            w: dict[str, Any] = entry["windows"]
            windows_cfg = AgentInstallConfig(
                method=w.get("method", ""),
                package=w.get("package") or None,
            )

        result.append(
            Agent(
                name=name,
                command=command,
                description=entry.get("description", ""),
                check_path=entry.get("check_path") or None,
                install_cmd=entry.get("install_cmd") or None,
                uninstall_cmd=entry.get("uninstall_cmd") or None,
                macos=macos_cfg,
                linux=linux_cfg,
                windows=windows_cfg,
            )
        )
    return result


def is_agent_installed(agent: Agent) -> bool:
    """Return True if the agent is present on this machine."""
    if agent.check_path:
        return Path(agent.check_path.replace("~", str(Path.home()))).exists()
    return shutil.which(agent.command) is not None


def get_agent_version(agent: Agent) -> str | None:
    """Return a short version string for display, or None if unavailable."""
    if not shutil.which(agent.command):
        return None
    # Most agents use --version; goose uses "version" subcommand as fallback
    for flag in ("--version", "version"):
        try:
            result = subprocess.run(
                [agent.command, flag],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                first_line = (result.stdout or result.stderr).splitlines()[0].strip()
                return first_line if first_line else None
        except FileNotFoundError, subprocess.TimeoutExpired, IndexError:
            continue
    return None


def _resolve_platform_config(agent: Agent) -> AgentInstallConfig | None:
    if is_platform(Platform.MACOS) and agent.macos:
        return agent.macos
    if is_platform(Platform.WINDOWS) and agent.windows:
        return agent.windows
    if (is_platform(Platform.WSL) or is_platform(Platform.LINUX)) and agent.linux:
        return agent.linux
    return None


def install_agent(agent: Agent, dry_run: bool = False) -> tuple[bool, str]:
    """Install an agent. Returns (success, message)."""
    if is_agent_installed(agent):
        return True, f"{agent.name} is already installed"

    config = _resolve_platform_config(agent)
    if config:
        return _install_via_config(agent.name, config, dry_run)
    if agent.install_cmd:
        return _install_via_script(agent.name, agent.install_cmd, dry_run)
    return False, f"No install method configured for {agent.name} on this platform"


def _install_via_config(
    name: str, config: AgentInstallConfig, dry_run: bool
) -> tuple[bool, str]:
    pkg = config.package or name
    if config.method == "npm":
        return _install_npm(name, pkg, dry_run)
    if config.method == "winget":
        return _install_winget(name, pkg, dry_run)
    return False, f"Unknown install method: {config.method}"


def uninstall_agent(agent: Agent, dry_run: bool = False) -> tuple[bool, str]:
    """Uninstall an agent. Returns (success, message)."""
    if not is_agent_installed(agent):
        return True, f"{agent.name} is not installed"

    config = _resolve_platform_config(agent)
    if config:
        return _uninstall_via_config(agent.name, config, dry_run)
    if agent.uninstall_cmd:
        return _uninstall_via_script(agent.name, agent.uninstall_cmd, dry_run)
    return False, f"No uninstall method configured for {agent.name} on this platform"


def uninstall_agent_by_manifest_entry(
    name: str,
    command: str,
    install_method: str,
    package: str | None,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Uninstall an agent using manifest-recorded install method."""
    if not shutil.which(command):
        return True, f"{name} is not installed"
    if install_method == "npm":
        return _uninstall_npm(name, package or name, dry_run)
    if install_method == "winget":
        return _uninstall_winget(name, package or name, dry_run)
    if install_method == "script":
        return True, f"{name} has no reverse uninstall script"
    return False, f"Unknown install method: {install_method}"


def _uninstall_via_config(
    name: str, config: AgentInstallConfig, dry_run: bool
) -> tuple[bool, str]:
    pkg = config.package or name
    if config.method == "npm":
        return _uninstall_npm(name, pkg, dry_run)
    if config.method == "winget":
        return _uninstall_winget(name, pkg, dry_run)
    return False, f"Unknown install method: {config.method}"


def _uninstall_npm(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("npm"):
        return (
            False,
            "npm is not available — install Node.js first, then re-run",
        )
    if dry_run:
        return True, f"Would uninstall {package} via npm uninstall -g"
    try:
        result = subprocess.run(
            ["npm", "uninstall", "-g", package],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Uninstalled {name} via npm"
        return False, f"Failed to uninstall {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to uninstall {name}: npm timed out"


def _uninstall_winget(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("winget"):
        return False, "winget is not available"
    if dry_run:
        return True, f"Would uninstall {package} via winget"
    try:
        result = subprocess.run(
            [
                "winget",
                "uninstall",
                package,
                "--silent",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Uninstalled {name} via winget"
        return False, f"Failed to uninstall {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to uninstall {name}: winget timed out"


def _uninstall_via_script(
    name: str, uninstall_cmd: str, dry_run: bool
) -> tuple[bool, str]:
    if dry_run:
        return True, f"Would uninstall {name} via: {uninstall_cmd}"
    try:
        result = subprocess.run(
            uninstall_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Uninstalled {name}"
        return False, f"Failed to uninstall {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to uninstall {name}: uninstall script timed out"


def get_agent_install_method(agent: Agent) -> tuple[str, str | None]:
    """Return (install_method, package) for manifest recording."""
    config = _resolve_platform_config(agent)
    if config:
        return config.method, config.package or agent.name
    return "script", None


def _install_npm(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("npm"):
        return (
            False,
            "npm is not available — install Node.js first, then re-run",
        )
    if dry_run:
        return True, f"Would install {package} via npm install -g"
    try:
        result = subprocess.run(
            ["npm", "install", "-g", package],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Installed {name} via npm"
        return False, f"Failed to install {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: npm timed out"


def _install_winget(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("winget"):
        return False, "winget is not available"
    if dry_run:
        return True, f"Would install {package} via winget"
    try:
        result = subprocess.run(
            [
                "winget",
                "install",
                package,
                "--accept-source-agreements",
                "--accept-package-agreements",
                "--silent",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Installed {name} via winget"
        return False, f"Failed to install {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: winget timed out"


def _install_via_script(name: str, install_cmd: str, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, f"Would install {name} via: {install_cmd}"
    try:
        result = subprocess.run(
            install_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Installed {name}"
        return False, f"Failed to install {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: install script timed out"
