"""Package management for shell-configs."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from shell_configs.profiles.profile import Profile

from pydantic import BaseModel

from shell_configs.platform import Platform, is_platform

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_package_name(name: str) -> str:
    if not _SAFE_NAME_RE.match(name):
        raise ValueError(f"Invalid package name: {name!r}")
    return name


def _inject_signed_by(source: str, key_path: str) -> str:
    """Inject signed-by= into a deb source line.

    Modern apt requires signed-by= to trust a keyring stored in
    /usr/share/keyrings/ rather than the legacy /etc/apt/trusted.gpg.d/.
    If the source already has an options bracket, signed-by= is inserted
    into it; otherwise a new bracket is prepended after 'deb '.
    """
    if "signed-by=" in source:
        return source
    if re.match(r"^deb\s+\[", source):
        return re.sub(r"^(deb\s+)\[([^\]]*)\]", rf"\1[\2 signed-by={key_path}]", source)
    return re.sub(r"^(deb\s+)", rf"\1[signed-by={key_path}] ", source)


def _run_pkg_cmd(
    cmd: list[str] | str,
    *,
    timeout: int,
    success_msg: str,
    failure_msg: str,
    timeout_msg: str,
) -> tuple[bool, str]:
    """Run a package-manager command with the shared result/error handling."""
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return False, timeout_msg
    except Exception as e:
        return False, f"Unexpected error: {e}"
    if result.returncode == 0:
        return True, success_msg
    return False, result.stderr.strip() or result.stdout.strip() or failure_msg


def ensure_sudo_auth() -> tuple[bool, str]:
    """Cache sudo credentials so captured sudo calls never block invisibly.

    Returns (True, "") when credentials are cached or not needed.
    Returns (False, reason) when auth fails or no TTY is available.
    """
    if os.geteuid() == 0 or shutil.which("sudo") is None:
        return True, ""

    try:
        probe = subprocess.run(["sudo", "-n", "-v"], capture_output=True, timeout=10)
    except subprocess.TimeoutExpired:
        probe = None

    if probe is not None and probe.returncode == 0:
        return True, ""

    if sys.stdin.isatty():
        from shell_configs.display import print_info

        print_info(
            "Administrator access needed to install packages"
            " — you may be prompted for your sudo password"
        )
        result = subprocess.run(["sudo", "-v"])
        if result.returncode == 0:
            return True, ""
        return False, "sudo authentication failed"

    return (
        False,
        "sudo authentication required but no TTY is available; run 'sudo -v' first",
    )


def _is_pwsh_module_installed(name: str) -> bool:
    """Check if a PowerShell module is installed."""
    _validate_package_name(name)
    if not shutil.which("pwsh"):
        return False

    try:
        check_cmd = f"Get-Module -ListAvailable -Name {name}"
        result = subprocess.run(
            ["pwsh", "-Command", check_cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return name in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _install_pwsh_module(name: str, dry_run: bool) -> tuple[bool, str]:
    """Install a PowerShell module via pwsh."""
    _validate_package_name(name)
    if not shutil.which("pwsh"):
        return False, "PowerShell (pwsh) is not installed"

    if dry_run:
        return True, f"Would install PowerShell module {name}"

    if _is_pwsh_module_installed(name):
        return True, f"{name} is already installed"

    return _run_pkg_cmd(
        ["pwsh", "-Command", f"Install-Module -Name {name} -Force -Scope CurrentUser"],
        timeout=120,
        success_msg=f"Successfully installed {name}",
        failure_msg="Installation failed",
        timeout_msg="Installation timed out",
    )


def _uninstall_pwsh_module(name: str, dry_run: bool) -> tuple[bool, str]:
    """Uninstall a PowerShell module via pwsh."""
    _validate_package_name(name)
    if not shutil.which("pwsh"):
        return False, "PowerShell (pwsh) is not installed"

    if dry_run:
        return True, f"Would uninstall PowerShell module {name}"

    if not _is_pwsh_module_installed(name):
        return True, f"{name} is not installed"

    return _run_pkg_cmd(
        ["pwsh", "-Command", f"Uninstall-Module -Name {name} -Force -AllVersions"],
        timeout=60,
        success_msg=f"Successfully uninstalled {name}",
        failure_msg="Uninstall failed",
        timeout_msg="Uninstall timed out",
    )


CANNOT_AUTO_UNINSTALL = frozenset({"script"})


@dataclass(frozen=True)
class _LinuxMethod:
    """Table entry for a simple which-check → run Linux install method."""

    tool: str  # binary checked with shutil.which
    label: str  # human label used in dry-run messages
    install_cmd: Callable[[str], list[str]]
    uninstall_cmd: Callable[[str], list[str]]


_LINUX_METHODS: dict[str, _LinuxMethod] = {
    "apt": _LinuxMethod(
        tool="apt",
        label="apt",
        install_cmd=lambda n: ["sudo", "-n", "apt-get", "install", "-y", n],
        uninstall_cmd=lambda n: ["sudo", "-n", "apt-get", "remove", "-y", n],
    ),
    "pip": _LinuxMethod(
        tool="pip",
        label="pip",
        install_cmd=lambda n: ["pip", "install", "--user", n],
        uninstall_cmd=lambda n: ["pip", "uninstall", "-y", n],
    ),
    "uv_tool": _LinuxMethod(
        tool="uv",
        label="uv tool",
        install_cmd=lambda n: ["uv", "tool", "install", n],
        uninstall_cmd=lambda n: ["uv", "tool", "uninstall", n],
    ),
}


class AptRepo(BaseModel):
    """Configuration for custom apt repository."""

    name: str
    key_url: str
    source: str


class InstallConfig(BaseModel):
    """Platform-specific installation configuration."""

    method: str
    package: str | None = None
    tap: str | None = None
    cask: bool = False
    repo: AptRepo | None = None
    extra_packages: list[str] | None = None
    install_cmd: str | None = None


class Package(BaseModel):
    """Package with platform-specific install configs."""

    name: str
    command: str | None = None
    description: str = ""
    required: bool = False
    wsl_only: bool = False
    # Setting both wsl_only and wsl_exclude is contradictory (package would
    # never be available on any platform) and must not be done.
    wsl_exclude: bool = False
    macos: InstallConfig | None = None
    linux: InstallConfig | None = None
    windows: InstallConfig | None = None

    def get_command(self) -> str:
        """Get command name for system check."""
        return self.command or self.name

    def get_config_for_platform(self) -> InstallConfig | None:
        """Get install config for current platform."""
        if self.wsl_only and not is_platform(Platform.WSL):
            return None
        if self.wsl_exclude and is_platform(Platform.WSL):
            return None
        if is_platform(Platform.MACOS):
            return self.macos
        if is_platform(Platform.WINDOWS):
            return self.windows
        return self.linux


def _linux_needs_sudo(pkg: Package) -> bool:
    """True if installing/uninstalling this package on Linux invokes sudo."""
    config = pkg.linux
    if config is None:
        return False
    if config.method == "apt":
        return True
    if (
        config.method == "script"
        and config.install_cmd
        and "sudo" in config.install_cmd
    ):
        return True
    return False


class PackageManager(ABC):
    """Base class for package managers."""

    name: str
    display_name: str

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def is_installed(self, pkg: Package) -> bool: ...

    @abstractmethod
    def install(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]: ...

    @abstractmethod
    def uninstall(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]: ...

    def can_uninstall(self, pkg: Package) -> bool:
        """Check if this manager can uninstall the package.

        Default: can uninstall if installed. Override for special cases.
        """
        return self.is_installed(pkg)


class HomebrewManager(PackageManager):
    """Homebrew package manager for macOS."""

    name = "homebrew"
    display_name = "Homebrew"

    def __init__(self) -> None:
        """Initialize HomebrewManager with cache fields."""
        self._installed_cache: set[str] | None = None
        self._cask_cache: set[str] | None = None

    def is_available(self) -> bool:
        """Check if brew command is available."""
        return shutil.which("brew") is not None

    @staticmethod
    def _list_brew(flag: str) -> set[str]:
        """List installed brew formulae or casks (empty set on failure)."""
        try:
            result = subprocess.run(
                ["brew", "list", flag, "-1"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return set(result.stdout.strip().split("\n"))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return set()

    def _get_installed_formulae(self) -> set[str]:
        """Get all installed Homebrew formulae (cached)."""
        if self._installed_cache is None:
            self._installed_cache = self._list_brew("--formula")
        return self._installed_cache

    def _get_installed_casks(self) -> set[str]:
        """Get all installed Homebrew casks (cached)."""
        if self._cask_cache is None:
            self._cask_cache = self._list_brew("--cask")
        return self._cask_cache

    def is_installed(self, pkg: Package) -> bool:
        """Check if package is installed."""
        config = pkg.macos
        if config and config.method == "pwsh":
            return _is_pwsh_module_installed(config.package or pkg.name)

        if shutil.which(pkg.get_command()):
            return True

        if not config:
            return False

        name = config.package or pkg.name

        if config.cask:
            return name in self._get_installed_casks()
        return name in self._get_installed_formulae()

    def is_managed_by_brew(self, pkg: Package) -> bool:
        """Check if package is managed by Homebrew (ignores PATH binaries)."""
        config = pkg.macos
        if not config or config.method != "brew":
            return False

        name = config.package or pkg.name
        if "/" in name:
            name = name.split("/")[-1]

        if config.cask:
            return name in self._get_installed_casks()
        return name in self._get_installed_formulae()

    def can_uninstall(self, pkg: Package) -> bool:
        """Check if we can uninstall this package."""
        config = pkg.macos
        if not config or config.method in CANNOT_AUTO_UNINSTALL:
            return False
        if config.method == "pwsh":
            return _is_pwsh_module_installed(config.package or pkg.name)
        return self.is_managed_by_brew(pkg)

    def install(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        """Install a package via Homebrew or PowerShell module."""
        config = pkg.macos
        if not config:
            return False, f"No macOS config for {pkg.name}"

        if self.is_installed(pkg):
            name = config.package or pkg.name
            return True, f"{name} is already installed"

        if config.method == "pwsh":
            name = config.package or pkg.name
            return _install_pwsh_module(name, dry_run)
        elif config.method == "brew":
            return self._install_brew(pkg, config, dry_run)

        return False, f"Unknown method: {config.method}"

    def _install_brew(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Install a package via Homebrew."""
        name = config.package or pkg.name

        if not self.is_available():
            return False, "Homebrew is not installed"

        if dry_run:
            install_type = "cask" if config.cask else "formula"
            return True, f"Would install {name} ({install_type})"

        if config.tap:
            try:
                tap_result = subprocess.run(
                    ["brew", "tap", config.tap],
                    capture_output=True,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                return False, "Installation timed out after 5 minutes"
            except Exception as e:
                return False, f"Unexpected error: {e}"
            if tap_result.returncode != 0:
                return False, f"Failed to tap {config.tap}"

        cmd = ["brew", "install"]
        if config.cask:
            cmd.append("--cask")
        cmd.append(name)

        ok, msg = _run_pkg_cmd(
            cmd,
            timeout=300,
            success_msg=f"Successfully installed {name}",
            failure_msg="Installation failed",
            timeout_msg="Installation timed out after 5 minutes",
        )
        if ok:
            self._installed_cache = None
            self._cask_cache = None
        return ok, msg

    def uninstall(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        """Uninstall a package."""
        config = pkg.macos
        if not config:
            return False, f"No macOS config for {pkg.name}"

        if config.method == "pwsh":
            return _uninstall_pwsh_module(config.package or pkg.name, dry_run)

        if config.method != "brew":
            return False, f"Cannot uninstall {pkg.name} (method: {config.method})"

        name = config.package or pkg.name
        if "/" in name:
            name = name.split("/")[-1]

        if not self.is_available():
            return False, "Homebrew is not installed"

        if not self.is_managed_by_brew(pkg):
            if shutil.which(pkg.get_command()):
                return (
                    True,
                    f"{name} is installed but not managed by Homebrew (skipping)",
                )
            return True, f"{name} is not installed"

        if dry_run:
            uninstall_type = "cask" if config.cask else "formula"
            return True, f"Would uninstall {name} ({uninstall_type})"

        cmd = ["brew", "uninstall"]
        if config.cask:
            cmd.append("--cask")
        cmd.append(name)

        ok, msg = _run_pkg_cmd(
            cmd,
            timeout=60,
            success_msg=f"Successfully uninstalled {name}",
            failure_msg="Uninstall failed",
            timeout_msg="Uninstall timed out",
        )
        if ok:
            self._installed_cache = None
            self._cask_cache = None
        elif "required by" in msg and "--ignore-dependencies" in msg:
            return (
                False,
                f"Cannot uninstall (required by other packages). Use: brew uninstall --ignore-dependencies {name}",
            )
        return ok, msg


class LinuxInstaller(PackageManager):
    """Handles multiple installation methods for Linux."""

    name = "linux"
    display_name = "Linux Installer"

    def is_available(self) -> bool:
        """Check if we can install packages on Linux."""
        return (
            shutil.which("apt") is not None
            or shutil.which("pip") is not None
            or shutil.which("uv") is not None
        )

    def is_installed(self, pkg: Package) -> bool:
        """Check if package is installed."""
        config = pkg.linux
        if config and config.method == "pwsh":
            return _is_pwsh_module_installed(config.package or pkg.name)

        if shutil.which(pkg.get_command()):
            return True

        if config and config.method == "apt":
            name = config.package or pkg.name
            try:
                result = subprocess.run(
                    ["dpkg", "-s", name],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False

        return False

    def can_uninstall(self, pkg: Package) -> bool:
        """Check if we can uninstall this package."""
        config = pkg.linux
        if not config or config.method in CANNOT_AUTO_UNINSTALL:
            return False
        if config.method == "pwsh":
            return _is_pwsh_module_installed(config.package or pkg.name)
        return self.is_installed(pkg)

    def install(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        """Install a package on Linux."""
        config = pkg.linux
        if not config:
            return False, f"No Linux config for {pkg.name}"

        if self.is_installed(pkg):
            return True, f"{pkg.name} is already installed"

        if config.method in _LINUX_METHODS:
            return self._run_method(config.method, pkg, config, dry_run, install=True)
        elif config.method == "script":
            return self._install_script(pkg, config, dry_run)
        elif config.method == "pwsh":
            name = config.package or pkg.name
            return _install_pwsh_module(name, dry_run)

        return False, f"Unknown method: {config.method}"

    def _run_method(
        self,
        method: str,
        pkg: Package,
        config: InstallConfig,
        dry_run: bool,
        *,
        install: bool,
    ) -> tuple[bool, str]:
        """Install or uninstall via one of the table-driven Linux methods."""
        m = _LINUX_METHODS[method]
        if not shutil.which(m.tool):
            return False, f"{m.tool} is not available"

        name = config.package or pkg.name
        verb = "install" if install else "uninstall"

        if dry_run:
            msg = f"Would {verb} {name} via {m.label}"
            if install and method == "apt" and config.repo:
                msg += f" (with {config.repo.name} repo)"
            if method == "apt" and config.extra_packages:
                msg += f" (+ {', '.join(config.extra_packages)})"
            return True, msg

        if install and method == "apt" and config.repo:
            try:
                self._setup_apt_repo(config.repo)
            except subprocess.TimeoutExpired:
                return False, "Installation timed out after 5 minutes"
            except Exception as e:
                return False, f"Unexpected error: {e}"

        if install:
            cmd = m.install_cmd(name)
            if method == "apt" and config.extra_packages:
                for ep in config.extra_packages:
                    _validate_package_name(ep)
                cmd.extend(config.extra_packages)
            return _run_pkg_cmd(
                cmd,
                timeout=300,
                success_msg=f"Successfully installed {name}",
                failure_msg="Installation failed",
                timeout_msg="Installation timed out after 5 minutes",
            )
        cmd = m.uninstall_cmd(name)
        if method == "apt" and config.extra_packages:
            cmd.extend(config.extra_packages)
        return _run_pkg_cmd(
            cmd,
            timeout=120,
            success_msg=f"Successfully uninstalled {name}",
            failure_msg="Uninstall failed",
            timeout_msg="Uninstall timed out",
        )

    def _setup_apt_repo(self, repo: AptRepo) -> None:
        """Setup a custom apt repository."""
        key_path = f"/usr/share/keyrings/{repo.name}-archive-keyring.gpg"
        sources_path = f"/etc/apt/sources.list.d/{repo.name}.list"
        source_line = _inject_signed_by(repo.source, key_path)

        sources_file = Path(sources_path)
        if Path(key_path).exists() and sources_file.exists():
            existing = sources_file.read_text(encoding="utf-8").strip()
            if existing == source_line:
                return  # Already configured correctly

        if not Path(key_path).exists():
            subprocess.run(
                f"curl -fsSL {repo.key_url} | sudo gpg --dearmor -o {key_path}",
                shell=True,
                check=True,
                timeout=60,
            )

        subprocess.run(
            f'echo "{source_line}" | sudo tee {sources_path}',
            shell=True,
            check=True,
            timeout=10,
        )

        update_result = subprocess.run(
            ["sudo", "-n", "apt-get", "update"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if update_result.returncode != 0:
            from shell_configs.display import print_warning

            stderr_tail = "\n".join(update_result.stderr.strip().splitlines()[-5:])
            print_warning(
                f"apt-get update failed for repo '{repo.name}'; "
                f"the following install result is definitive.\n{stderr_tail}"
            )

    def _install_script(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Install a package via custom script."""
        if not config.install_cmd:
            return False, f"No install command for {pkg.name}"

        if dry_run:
            return True, f"Would run: {config.install_cmd}"

        return _run_pkg_cmd(
            config.install_cmd,
            timeout=300,
            success_msg=f"Successfully installed {pkg.name}",
            failure_msg="Installation failed",
            timeout_msg="Installation timed out after 5 minutes",
        )

    def uninstall(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        """Uninstall a package on Linux."""
        config = pkg.linux
        if not config:
            return False, f"No Linux config for {pkg.name}"

        if not self.is_installed(pkg):
            return True, f"{pkg.name} is not installed"

        if config.method in _LINUX_METHODS:
            return self._run_method(config.method, pkg, config, dry_run, install=False)
        elif config.method == "pwsh":
            return _uninstall_pwsh_module(config.package or pkg.name, dry_run)
        elif config.method in CANNOT_AUTO_UNINSTALL:
            return False, f"Cannot auto-uninstall {pkg.name} (method: {config.method})"

        return False, f"Unknown method: {config.method}"


class WingetManager(PackageManager):
    """Winget package manager for Windows."""

    name = "winget"
    display_name = "Winget"

    def is_available(self) -> bool:
        return shutil.which("winget") is not None

    def is_installed(self, pkg: Package) -> bool:
        config = pkg.windows
        if config and config.method == "pwsh":
            return _is_pwsh_module_installed(config.package or pkg.name)
        if shutil.which(pkg.get_command()):
            return True
        # Fallback: check winget registry
        if config and config.package:
            try:
                result = subprocess.run(
                    ["winget", "list", "--id", config.package, "--exact"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.returncode == 0 and config.package in result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        return False

    def can_uninstall(self, pkg: Package) -> bool:
        config = pkg.windows
        if not config or config.method in CANNOT_AUTO_UNINSTALL:
            return False
        if config.method == "pwsh":
            return _is_pwsh_module_installed(config.package or pkg.name)
        return self.is_installed(pkg)

    def install(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        config = pkg.windows
        if not config:
            return False, f"No Windows config for {pkg.name}"

        if self.is_installed(pkg):
            return True, f"{pkg.name} is already installed"

        if config.method == "pwsh":
            return _install_pwsh_module(config.package or pkg.name, dry_run)

        if config.method != "winget":
            return False, f"Unknown method: {config.method}"

        name = config.package or pkg.name
        if dry_run:
            return True, f"Would install {name} via winget"

        return _run_pkg_cmd(
            [
                "winget",
                "install",
                name,
                "--silent",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
            timeout=300,
            success_msg=f"Successfully installed {name}",
            failure_msg="Installation failed",
            timeout_msg="Installation timed out",
        )

    def uninstall(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        config = pkg.windows
        if not config:
            return False, f"No Windows config for {pkg.name}"

        if not self.is_installed(pkg):
            return True, f"{pkg.name} is not installed"

        if config.method == "pwsh":
            return _uninstall_pwsh_module(config.package or pkg.name, dry_run)

        if config.method != "winget":
            return False, f"Cannot uninstall {pkg.name} (method: {config.method})"

        name = config.package or pkg.name
        if dry_run:
            return True, f"Would uninstall {name} via winget"

        return _run_pkg_cmd(
            ["winget", "uninstall", name, "--silent"],
            timeout=120,
            success_msg=f"Successfully uninstalled {name}",
            failure_msg="Uninstall failed",
            timeout_msg="Uninstall timed out",
        )


def get_package_manager() -> PackageManager | None:
    """Get the appropriate package manager for this system.

    Returns:
        PackageManager if available, None otherwise
    """
    if is_platform(Platform.MACOS):
        brew = HomebrewManager()
        return brew if brew.is_available() else None

    if is_platform(Platform.WINDOWS):
        winget = WingetManager()
        return winget if winget.is_available() else None

    if is_platform(Platform.WSL) or is_platform(Platform.LINUX):
        linux_installer = LinuxInstaller()
        return linux_installer if linux_installer.is_available() else None

    return None


def sort_packages_for_install(packages: list[Package]) -> list[Package]:
    """Sort packages so pwsh-method packages come last (after powershell).

    This ensures PowerShell is installed before PowerShell modules.
    """

    def sort_key(pkg: Package) -> int:
        config = pkg.get_config_for_platform()
        if config and config.method == "pwsh":
            return 1
        return 0

    return sorted(packages, key=sort_key)


def sort_packages_for_uninstall(packages: list[Package]) -> list[Package]:
    """Sort packages so pwsh-method packages come first (before powershell).

    This ensures PowerShell modules are uninstalled before PowerShell itself.
    """

    def sort_key(pkg: Package) -> int:
        config = pkg.get_config_for_platform()
        if config and config.method == "pwsh":
            return 0
        return 1

    return sorted(packages, key=sort_key)


def load_packages_for_profile(
    profile: Profile | None,
    manifest_path: Path | None = None,
) -> list[Package]:
    """Load packages filtered and extended by a profile.

    Starts with the full package list, removes packages in
    profile.packages["remove"], and adds packages in profile.packages["add"]
    (only those that already exist in the manifest by name).

    Args:
        profile: Active profile (uses base list unchanged when None)
        manifest_path: Optional path to packages.yaml

    Returns:
        Filtered/extended list of Package objects
    """
    base_packages = load_packages(manifest_path)
    if profile is None:
        return base_packages
    remove_names = set(profile.packages.get("remove", []))
    add_names = profile.packages.get("add", [])

    result = [p for p in base_packages if p.name not in remove_names]

    existing_names = {p.name for p in result}
    for name in add_names:
        if name not in existing_names:
            matching = [p for p in base_packages if p.name == name]
            result.extend(matching)

    return result


def load_packages(manifest_path: Path | None = None) -> list[Package]:
    """Load packages from YAML manifest.

    Args:
        manifest_path: Path to packages.yaml (auto-detected if None)

    Returns:
        List of Package objects

    Raises:
        FileNotFoundError: If manifest file doesn't exist
    """
    if manifest_path is None:
        from shell_configs.config import get_config_dir

        manifest_path = get_config_dir() / "packages.yaml"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Package manifest not found: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    all_packages = [Package(**item) for item in data.get("packages", [])]
    return [p for p in all_packages if p.get_config_for_platform() is not None]
