"""Shell completion installation and management."""

import os
import re

from dataclasses import dataclass
from pathlib import Path

COMPLETION_MARKER_START = "# shell-configs shell completion"
COMPLETION_MARKER_END = "# End shell-configs shell completion"

PROG_NAME = "shell-configs"


@dataclass
class ShellConfig:
    """Configuration for a supported shell."""

    name: str
    config_files: list[str]

    def get_config_candidates(self) -> list[Path]:
        """Get existing config file paths for this shell."""
        home = Path.home()
        return [home / cf for cf in self.config_files if (home / cf).exists()]


SHELL_REGISTRY: dict[str, ShellConfig] = {
    "bash": ShellConfig("bash", [".bashrc", ".bash_profile", ".profile"]),
    "zsh": ShellConfig("zsh", [".zshrc", ".zprofile"]),
}


def get_supported_shells() -> tuple[str, ...]:
    """Get tuple of supported shell names."""
    return tuple(SHELL_REGISTRY.keys())


def detect_shell() -> str | None:
    """Detect current shell from $SHELL environment variable.

    Returns:
        Shell name if supported, None otherwise
    """
    shell_path = os.environ.get("SHELL", "")
    shell_name = Path(shell_path).name if shell_path else None
    return shell_name if shell_name in SHELL_REGISTRY else None


def _get_shell_config_candidates(shell: str) -> list[Path]:
    """Return candidate config files for a shell, checking which exist.

    Args:
        shell: Shell name (e.g., 'bash', 'zsh')

    Returns:
        List of config file paths that exist on the system
    """
    shell_config = SHELL_REGISTRY.get(shell)
    if shell_config is None:
        return []
    return shell_config.get_config_candidates()


def find_config_file(shell: str) -> Path | None:
    """Find the appropriate config file - first existing candidate.

    Args:
        shell: Shell name ('bash' or 'zsh')

    Returns:
        Path to config file, or None if no candidates exist
    """
    candidates = _get_shell_config_candidates(shell)
    return candidates[0] if candidates else None


def is_completion_installed(config_path: Path) -> bool:
    """Check if completion is already installed in config file.

    Args:
        config_path: Path to shell config file

    Returns:
        True if completion marker found in file
    """
    if not config_path.exists():
        return False

    content = config_path.read_text()
    return COMPLETION_MARKER_START in content


def generate_completion_script(shell: str) -> str:
    """Generate completion script with command-existence guard.

    Args:
        shell: Shell name ('bash' or 'zsh')

    Returns:
        Completion script to add to shell config

    Raises:
        ValueError: If shell is not supported
    """
    from click.shell_completion import get_completion_class

    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        raise ValueError(f"Unsupported shell: {shell}")

    env_var = f"_{PROG_NAME.upper().replace('-', '_')}_COMPLETE"

    return f"""{COMPLETION_MARKER_START}
if command -v {PROG_NAME} >/dev/null 2>&1; then
  eval "$({env_var}={shell}_source {PROG_NAME})"
fi
{COMPLETION_MARKER_END}"""


def install_completion(shell: str, dry_run: bool = False) -> tuple[bool, str]:
    """Install completion to shell config file.

    Args:
        shell: Shell name (e.g., 'bash', 'zsh')
        dry_run: If True, only show what would be done

    Returns:
        Tuple of (success: bool, message: str)
    """
    if shell not in SHELL_REGISTRY:
        supported = ", ".join(get_supported_shells())
        return False, f"Unsupported shell: {shell}. Supported: {supported}"

    config_path = find_config_file(shell)
    if config_path is None:
        return (
            False,
            f"No {shell} config file found. Expected one of: "
            + ", ".join(str(p) for p in _get_shell_config_candidates(shell)),
        )

    if is_completion_installed(config_path):
        return update_completion(shell, dry_run=dry_run)

    script = generate_completion_script(shell)

    if dry_run:
        return True, f"Would append completion script to {config_path}"

    try:
        with config_path.open("a") as f:
            f.write(f"\n{script}\n")
        return (
            True,
            f"Completion installed to {config_path}. Restart your shell or run: source {config_path}",
        )
    except Exception as e:
        return False, f"Failed to write to {config_path}: {e}"


def update_completion(shell: str, dry_run: bool = False) -> tuple[bool, str]:
    """Replace existing completion block with a freshly generated one.

    Args:
        shell: Shell name (e.g., 'bash', 'zsh')
        dry_run: If True, only show what would be done

    Returns:
        Tuple of (success: bool, message: str)
    """
    config_path = find_config_file(shell)
    if config_path is None:
        return False, f"No {shell} config file found"
    if not is_completion_installed(config_path):
        return install_completion(shell, dry_run=dry_run)

    new_script = generate_completion_script(shell)
    if dry_run:
        return True, f"Would update completion in {config_path}"

    content = config_path.read_text()

    start_re = re.escape(COMPLETION_MARKER_START)
    end_re = re.escape(COMPLETION_MARKER_END)
    pattern = f"({start_re}).*?({end_re})"
    new_content, n = re.subn(pattern, lambda _: new_script, content, flags=re.DOTALL)
    if n == 0:
        return False, f"Could not find completion block in {config_path}"
    config_path.write_text(new_content)
    return (
        True,
        f"Completion updated in {config_path}. Restart your shell or run: source {config_path}",
    )


def uninstall_completion(config_path: Path) -> tuple[bool, str]:
    """Remove completion block from shell config file.

    Args:
        config_path: Path to shell config file

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not config_path.exists():
        return False, f"Config file not found: {config_path}"

    if not is_completion_installed(config_path):
        return True, f"Completion not installed in {config_path}"

    try:
        content = config_path.read_text()

        start_re = re.escape(COMPLETION_MARKER_START)
        end_re = re.escape(COMPLETION_MARKER_END)
        pattern = f"({start_re}).*?({end_re})"
        new_content = re.sub(pattern, lambda _: "", content, flags=re.DOTALL)

        if new_content == content:
            return False, f"Could not find complete completion block in {config_path}"

        new_content = re.sub(r"\n{3,}", "\n\n", new_content)

        config_path.write_text(new_content)
        return True, f"Completion removed from {config_path}"
    except Exception as e:
        return False, f"Failed to modify {config_path}: {e}"
