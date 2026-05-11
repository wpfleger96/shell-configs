"""Package management for shell-configs."""

import shutil
import subprocess

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from shell_configs.profiles.profile import Profile

from pydantic import BaseModel

from shell_configs.platform import Platform, is_platform


def _is_pwsh_module_installed(name: str) -> bool:
    """Check if a PowerShell module is installed."""
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
    if not shutil.which("pwsh"):
        return False, "PowerShell (pwsh) is not installed"

    if dry_run:
        return True, f"Would install PowerShell module {name}"

    try:
        if _is_pwsh_module_installed(name):
            return True, f"{name} is already installed"

        install_cmd = f"Install-Module -Name {name} -Force -Scope CurrentUser"
        result = subprocess.run(
            ["pwsh", "-Command", install_cmd],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            return True, f"Successfully installed {name}"

        return False, result.stderr.strip() or "Installation failed"

    except subprocess.TimeoutExpired:
        return False, "Installation timed out"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def _uninstall_pwsh_module(name: str, dry_run: bool) -> tuple[bool, str]:
    """Uninstall a PowerShell module via pwsh."""
    if not shutil.which("pwsh"):
        return False, "PowerShell (pwsh) is not installed"

    if dry_run:
        return True, f"Would uninstall PowerShell module {name}"

    if not _is_pwsh_module_installed(name):
        return True, f"{name} is not installed"

    try:
        uninstall_cmd = f"Uninstall-Module -Name {name} -Force -AllVersions"
        result = subprocess.run(
            ["pwsh", "-Command", uninstall_cmd],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True, f"Successfully uninstalled {name}"

        return False, result.stderr.strip() or "Uninstall failed"

    except subprocess.TimeoutExpired:
        return False, "Uninstall timed out"
    except Exception as e:
        return False, f"Unexpected error: {e}"


CANNOT_AUTO_UNINSTALL = frozenset({"script"})


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
    install_cmd: str | None = None


class Package(BaseModel):
    """Package with platform-specific install configs."""

    name: str
    command: str | None = None
    description: str = ""
    required: bool = False
    wsl_only: bool = False
    macos: InstallConfig | None = None
    linux: InstallConfig | None = None

    def get_command(self) -> str:
        """Get command name for system check."""
        return self.command or self.name

    def get_config_for_platform(self) -> InstallConfig | None:
        """Get install config for current platform."""
        if self.wsl_only and not is_platform(Platform.WSL):
            return None
        return self.macos if is_platform(Platform.MACOS) else self.linux


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

    def _get_installed_formulae(self) -> set[str]:
        """Get all installed Homebrew formulae (cached)."""
        if self._installed_cache is None:
            try:
                result = subprocess.run(
                    ["brew", "list", "--formula", "-1"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    self._installed_cache = set(result.stdout.strip().split("\n"))
                else:
                    self._installed_cache = set()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._installed_cache = set()
        return self._installed_cache

    def _get_installed_casks(self) -> set[str]:
        """Get all installed Homebrew casks (cached)."""
        if self._cask_cache is None:
            try:
                result = subprocess.run(
                    ["brew", "list", "--cask", "-1"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    self._cask_cache = set(result.stdout.strip().split("\n"))
                else:
                    self._cask_cache = set()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._cask_cache = set()
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

        try:
            if config.tap:
                tap_result = subprocess.run(
                    ["brew", "tap", config.tap],
                    capture_output=True,
                    timeout=60,
                )
                if tap_result.returncode != 0:
                    return False, f"Failed to tap {config.tap}"

            cmd = ["brew", "install"]
            if config.cask:
                cmd.append("--cask")
            cmd.append(name)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                self._installed_cache = None
                self._cask_cache = None
                return True, f"Successfully installed {name}"

            return False, result.stderr.strip() or "Installation failed"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out after 5 minutes"
        except Exception as e:
            return False, f"Unexpected error: {e}"

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

        try:
            cmd = ["brew", "uninstall"]
            if config.cask:
                cmd.append("--cask")
            cmd.append(name)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self._installed_cache = None
                self._cask_cache = None
                return True, f"Successfully uninstalled {name}"

            error_msg = result.stderr.strip() or "Uninstall failed"
            if "required by" in error_msg and "--ignore-dependencies" in error_msg:
                return (
                    False,
                    f"Cannot uninstall (required by other packages). Use: brew uninstall --ignore-dependencies {name}",
                )

            return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "Uninstall timed out"
        except Exception as e:
            return False, f"Unexpected error: {e}"


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

        if config.method == "apt":
            return self._install_apt(pkg, config, dry_run)
        elif config.method == "pip":
            return self._install_pip(pkg, config, dry_run)
        elif config.method == "uv_tool":
            return self._install_uv_tool(pkg, config, dry_run)
        elif config.method == "script":
            return self._install_script(pkg, config, dry_run)
        elif config.method == "pwsh":
            name = config.package or pkg.name
            return _install_pwsh_module(name, dry_run)

        return False, f"Unknown method: {config.method}"

    def _install_apt(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Install a package via apt."""
        if not shutil.which("apt"):
            return False, "apt is not available"

        name = config.package or pkg.name

        if dry_run:
            msg = f"Would install {name} via apt"
            if config.repo:
                msg += f" (with {config.repo.name} repo)"
            return True, msg

        try:
            if config.repo:
                self._setup_apt_repo(config.repo)

            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", name],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return True, f"Successfully installed {name}"

            return False, result.stderr.strip() or "Installation failed"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out after 5 minutes"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _setup_apt_repo(self, repo: AptRepo) -> None:
        """Setup a custom apt repository."""
        key_path = f"/usr/share/keyrings/{repo.name}-archive-keyring.gpg"
        sources_path = f"/etc/apt/sources.list.d/{repo.name}.list"

        if Path(key_path).exists() and Path(sources_path).exists():
            return

        subprocess.run(
            f"curl -fsSL {repo.key_url} | sudo gpg --dearmor -o {key_path}",
            shell=True,
            check=True,
            timeout=60,
        )

        subprocess.run(
            f'echo "{repo.source}" | sudo tee {sources_path}',
            shell=True,
            check=True,
            timeout=10,
        )

        subprocess.run(
            ["sudo", "apt-get", "update"],
            capture_output=True,
            timeout=120,
        )

    def _install_pip(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Install a package via pip."""
        if not shutil.which("pip"):
            return False, "pip is not available"

        name = config.package or pkg.name

        if dry_run:
            return True, f"Would install {name} via pip"

        try:
            result = subprocess.run(
                ["pip", "install", "--user", name],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return True, f"Successfully installed {name}"

            return False, result.stderr.strip() or "Installation failed"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out after 5 minutes"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _install_uv_tool(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Install a package via uv tool."""
        if not shutil.which("uv"):
            return False, "uv is not available"

        name = config.package or pkg.name

        if dry_run:
            return True, f"Would install {name} via uv tool"

        try:
            result = subprocess.run(
                ["uv", "tool", "install", name],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return True, f"Successfully installed {name}"

            return False, result.stderr.strip() or "Installation failed"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out after 5 minutes"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _install_script(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Install a package via custom script."""
        if not config.install_cmd:
            return False, f"No install command for {pkg.name}"

        if dry_run:
            return True, f"Would run: {config.install_cmd}"

        try:
            result = subprocess.run(
                config.install_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return True, f"Successfully installed {pkg.name}"

            return False, result.stderr.strip() or "Installation failed"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out after 5 minutes"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def uninstall(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        """Uninstall a package on Linux."""
        config = pkg.linux
        if not config:
            return False, f"No Linux config for {pkg.name}"

        if not self.is_installed(pkg):
            return True, f"{pkg.name} is not installed"

        if config.method == "apt":
            return self._uninstall_apt(pkg, config, dry_run)
        elif config.method == "pip":
            return self._uninstall_pip(pkg, config, dry_run)
        elif config.method == "uv_tool":
            return self._uninstall_uv_tool(pkg, config, dry_run)
        elif config.method == "pwsh":
            return _uninstall_pwsh_module(config.package or pkg.name, dry_run)
        elif config.method in CANNOT_AUTO_UNINSTALL:
            return False, f"Cannot auto-uninstall {pkg.name} (method: {config.method})"

        return False, f"Unknown method: {config.method}"

    def _uninstall_apt(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Uninstall a package via apt."""
        if not shutil.which("apt"):
            return False, "apt is not available"

        name = config.package or pkg.name

        if dry_run:
            return True, f"Would uninstall {name} via apt"

        try:
            result = subprocess.run(
                ["sudo", "apt-get", "remove", "-y", name],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return True, f"Successfully uninstalled {name}"

            return False, result.stderr.strip() or "Uninstall failed"

        except subprocess.TimeoutExpired:
            return False, "Uninstall timed out"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _uninstall_pip(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Uninstall a package via pip."""
        if not shutil.which("pip"):
            return False, "pip is not available"

        name = config.package or pkg.name

        if dry_run:
            return True, f"Would uninstall {name} via pip"

        try:
            result = subprocess.run(
                ["pip", "uninstall", "-y", name],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return True, f"Successfully uninstalled {name}"

            return False, result.stderr.strip() or "Uninstall failed"

        except subprocess.TimeoutExpired:
            return False, "Uninstall timed out"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _uninstall_uv_tool(
        self, pkg: Package, config: InstallConfig, dry_run: bool
    ) -> tuple[bool, str]:
        """Uninstall a package via uv tool."""
        if not shutil.which("uv"):
            return False, "uv is not available"

        name = config.package or pkg.name

        if dry_run:
            return True, f"Would uninstall {name} via uv tool"

        try:
            result = subprocess.run(
                ["uv", "tool", "uninstall", name],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return True, f"Successfully uninstalled {name}"

            return False, result.stderr.strip() or "Uninstall failed"

        except subprocess.TimeoutExpired:
            return False, "Uninstall timed out"
        except Exception as e:
            return False, f"Unexpected error: {e}"


def get_package_manager() -> PackageManager | None:
    """Get the appropriate package manager for this system.

    Returns:
        PackageManager if available, None otherwise
    """
    if is_platform(Platform.MACOS):
        brew = HomebrewManager()
        return brew if brew.is_available() else None

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
    profile: "Profile | None",
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

    with open(manifest_path) as f:
        data = yaml.safe_load(f) or {}

    all_packages = [Package(**item) for item in data.get("packages", [])]
    # Manager methods access pkg.linux directly, bypassing get_config_for_platform()
    return [p for p in all_packages if not p.wsl_only or is_platform(Platform.WSL)]
