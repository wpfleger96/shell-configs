"""AI coding agent management (Claude Code, Codex, Gemini, Goose, etc.)."""

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
    method: str  # "brew" or "npm"
    package: str | None = None
    cask: bool = False
    tap: str | None = None


@dataclass(frozen=True)
class Agent:
    name: str
    command: str
    description: str
    check_path: str | None = None
    install_cmd: str | None = None
    macos: AgentInstallConfig | None = None
    linux: AgentInstallConfig | None = None


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
                cask=bool(m.get("cask", False)),
                tap=m.get("tap") or None,
            )
        if isinstance(entry.get("linux"), dict):
            li: dict[str, Any] = entry["linux"]
            linux_cfg = AgentInstallConfig(
                method=li.get("method", ""),
                package=li.get("package") or None,
                cask=bool(li.get("cask", False)),
                tap=li.get("tap") or None,
            )

        result.append(
            Agent(
                name=name,
                command=command,
                description=entry.get("description", ""),
                check_path=entry.get("check_path") or None,
                install_cmd=entry.get("install_cmd") or None,
                macos=macos_cfg,
                linux=linux_cfg,
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
        except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
            continue
    return None


def install_agent(agent: Agent, dry_run: bool = False) -> tuple[bool, str]:
    """Install an agent. Returns (success, message)."""
    if is_agent_installed(agent):
        return True, f"{agent.name} is already installed"

    ok, msg = False, f"No install method configured for {agent.name} on this platform"

    if is_platform(Platform.MACOS) and agent.macos:
        ok, msg = _install_via_config(agent.name, agent.macos, dry_run)
    elif (is_platform(Platform.WSL) or is_platform(Platform.LINUX)) and agent.linux:
        ok, msg = _install_via_config(agent.name, agent.linux, dry_run)
    elif agent.install_cmd:
        ok, msg = _install_via_script(agent.name, agent.install_cmd, dry_run)

    return ok, msg


def _install_via_config(
    name: str, config: AgentInstallConfig, dry_run: bool
) -> tuple[bool, str]:
    pkg = config.package or name
    if config.method == "brew":
        return _install_brew(name, config, dry_run)
    if config.method == "npm":
        return _install_npm(name, pkg, dry_run)
    return False, f"Unknown install method: {config.method}"


def _install_brew(
    name: str, config: AgentInstallConfig, dry_run: bool
) -> tuple[bool, str]:
    if not shutil.which("brew"):
        return False, "brew is not available"
    pkg = config.package or name
    if dry_run:
        cask_flag = " --cask" if config.cask else ""
        tap_msg = f" (tap: {config.tap})" if config.tap else ""
        return True, f"Would install {pkg} via brew{cask_flag}{tap_msg}"
    try:
        if config.tap:
            tap_result = subprocess.run(
                ["brew", "tap", config.tap],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if tap_result.returncode != 0:
                return False, f"Failed to tap {config.tap}: {tap_result.stderr.strip()}"
        cmd = ["brew", "install"]
        if config.cask:
            cmd.append("--cask")
        cmd.append(pkg)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, f"Installed {name} via brew"
        return False, f"Failed to install {name}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Failed to install {name}: brew timed out"


def _install_npm(name: str, package: str, dry_run: bool) -> tuple[bool, str]:
    if not shutil.which("npm"):
        return False, "npm is not available"
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
