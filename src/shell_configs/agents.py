"""AI coding agent management (Claude Code, Codex, Gemini, Goose, Amp)."""

from __future__ import annotations

import shutil
import subprocess

from dataclasses import dataclass
from pathlib import Path

import yaml

from shell_configs.config import get_config_dir
from shell_configs.installers import (
    PlatformInstallConfig,
    install_npm,
    install_winget,
    parse_platform_configs,
    resolve_platform_config,
    run_script,
    run_via_config,
    uninstall_npm,
    uninstall_winget,
)

AgentInstallConfig = PlatformInstallConfig

_AGENT_INSTALL = {"npm": install_npm, "winget": install_winget}
_AGENT_UNINSTALL = {"npm": uninstall_npm, "winget": uninstall_winget}


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

        macos_cfg, linux_cfg, windows_cfg = parse_platform_configs(entry)

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
    return resolve_platform_config(
        macos=agent.macos, linux=agent.linux, windows=agent.windows
    )


def install_agent(agent: Agent, dry_run: bool = False) -> tuple[bool, str]:
    """Install an agent. Returns (success, message)."""
    if is_agent_installed(agent):
        return True, f"{agent.name} is already installed"

    config = _resolve_platform_config(agent)
    if config:
        return run_via_config(agent.name, config, dry_run, handlers=_AGENT_INSTALL)
    if agent.install_cmd:
        return run_script(agent.name, agent.install_cmd, dry_run)
    return False, f"No install method configured for {agent.name} on this platform"


def uninstall_agent(agent: Agent, dry_run: bool = False) -> tuple[bool, str]:
    """Uninstall an agent. Returns (success, message)."""
    if not is_agent_installed(agent):
        return True, f"{agent.name} is not installed"

    config = _resolve_platform_config(agent)
    if config:
        return run_via_config(agent.name, config, dry_run, handlers=_AGENT_UNINSTALL)
    if agent.uninstall_cmd:
        return run_script(agent.name, agent.uninstall_cmd, dry_run, verb="uninstall")
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
        return uninstall_npm(name, package or name, dry_run)
    if install_method == "winget":
        return uninstall_winget(name, package or name, dry_run)
    if install_method == "script":
        return True, f"{name} has no reverse uninstall script"
    return False, f"Unknown install method: {install_method}"


def get_agent_install_method(agent: Agent) -> tuple[str, str | None]:
    """Return (install_method, package) for manifest recording."""
    config = _resolve_platform_config(agent)
    if config:
        return config.method, config.package or agent.name
    return "script", None
