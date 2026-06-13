"""Base shell configuration interface."""

import copy
import json
import subprocess
import tempfile

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shell_configs.extensions import ExtensionInvoker


@dataclass
class ConfigFile:
    """Represents a configuration file."""

    name: str
    path: Path
    repo_config_name: str | None = None


@dataclass
class AdditionalFile:
    """Represents an additional file to be installed alongside config."""

    name: str
    source_path: Path
    target_path: Path
    comment_prefix: str | None = None
    base_source_path: Path | None = field(default=None)
    backup_dir: Path | None = field(default=None)
    ini_merge: bool = False
    target_merge: bool = False
    xml_guiconfig_merge: bool = False


@dataclass
class PreferencesFile:
    """Represents application preferences written via macOS defaults(1)."""

    name: str
    source_path: Path
    domain: str
    app_name: str | None = None


@dataclass
class StateDbEntry:
    """Represents a key-value entry in an application's internal state database."""

    name: str
    db_path: Path
    key: str
    value: str


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dicts; override wins on key conflicts.

    Non-dict values are replaced entirely (not recursively merged).

    Args:
        base: Base dictionary
        override: Override dictionary (wins on key conflicts)

    Returns:
        New merged dictionary
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key not in result:
            result[key] = copy.deepcopy(value)
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def merge_json_with_profile(
    base_path: Path,
    override_path: Path,
    profile_overrides: dict[str, Any] | None,
) -> str:
    """Merge two JSON files and apply profile overrides on top.

    Calls merge_json_files for the two-file base/override merge, then
    deep-merges profile_overrides on top if provided.

    Args:
        base_path: Path to the base JSON file
        override_path: Path to the override JSON file
        profile_overrides: Optional dict of profile overrides to apply last

    Returns:
        Formatted JSON string with trailing newline
    """
    import json

    merged_str = merge_json_files(base_path, override_path)

    if not profile_overrides:
        return merged_str

    merged = json.loads(merged_str)
    merged = deep_merge(merged, profile_overrides)
    return json.dumps(merged, indent=4, ensure_ascii=False) + "\n"


def _json_is_subset(source: object, target: object) -> bool:
    """Check if all source keys/values exist in target (recursively).

    For dicts: every source key must exist in target with matching value.
    For lists: every source element must exist somewhere in target.
    For scalars: values must be equal.
    """
    if isinstance(source, dict) and isinstance(target, dict):
        return all(
            k in target and _json_is_subset(v, target[k]) for k, v in source.items()
        )
    if isinstance(source, list) and isinstance(target, list):
        return all(any(_json_is_subset(s, t) for t in target) for s in source)
    return source == target


def merge_json_into_target(source_path: Path, target_path: Path) -> tuple[str, bool]:
    """Merge source JSON keys into existing target JSON.

    Returns (merged_content, is_synced) where is_synced uses subset
    checking — True when every source key/value already exists in
    the target, ignoring extra target keys and formatting.
    """
    import json

    try:
        source = json.loads(source_path.read_text()) if source_path.exists() else {}
    except Exception:
        source = {}

    try:
        target = json.loads(target_path.read_text()) if target_path.exists() else {}
    except Exception:
        target = {}

    is_synced = _json_is_subset(source, target)
    merged = deep_merge(target, source)
    content = json.dumps(merged, indent=4, ensure_ascii=False) + "\n"
    return content, is_synced


def merge_json_files(base_path: Path, override_path: Path) -> str:
    """Shallow-merge two JSON files. Override keys win.

    This is a top-level-only merge: if both files contain the same
    top-level key, the override's value replaces the base's entirely
    (nested objects are NOT recursively merged). Override files should
    only contain keys unique to that editor (e.g., cursor.* namespace).

    Args:
        base_path: Path to the base JSON file
        override_path: Path to the override JSON file

    Returns:
        Formatted JSON string with trailing newline
    """
    try:
        base = json.loads(base_path.read_text()) if base_path.exists() else {}
    except Exception:
        base = {}

    try:
        override = (
            json.loads(override_path.read_text()) if override_path.exists() else {}
        )
    except Exception:
        override = {}

    merged = {**base, **override}
    return json.dumps(merged, indent=4, ensure_ascii=False) + "\n"


class Shell(ABC):
    """Abstract base class for shell implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the shell name (e.g., 'bash', 'zsh', 'git')."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Get the display name for the shell."""

    @abstractmethod
    def get_config_files(self) -> list[ConfigFile]:
        """Get the list of configuration files for this shell.

        Returns:
            List of ConfigFile objects
        """

    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get the validation command for this shell.

        Defaults to a no-op; shells with real syntax checkers override.

        Args:
            temp_file: Path to temporary file with content

        Returns:
            Command list to execute
        """
        return self._noop_validation_command()

    def _get_temp_suffix(self) -> str:
        """Get the file suffix for temp validation files.

        Returns:
            File suffix (e.g., ".sh", ".zsh", ".gitconfig")
        """
        return ".txt"

    def _noop_validation_command(self) -> list[str]:
        from shell_configs.platform import Platform, is_platform

        if is_platform(Platform.WINDOWS):
            return ["cmd", "/c", "exit", "0"]
        return ["true"]

    def validate_syntax(self, content: str) -> tuple[bool, str]:
        """Validate the syntax of configuration content.

        Args:
            content: Content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=self._get_temp_suffix(), delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            command = self._get_validation_command(temp_path)
            return self._run_validation_command(command, temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def get_extension_cli(self) -> str | None:
        """Get the CLI command for managing extensions (e.g., "code", "cursor").

        Returns None for shells that don't manage extensions.
        """
        return None

    def get_extension_invoker(self) -> ExtensionInvoker | None:
        """Get an ExtensionInvoker for this shell.

        When an invoker is returned, callers use it instead of get_extension_cli().
        Returns None by default; override in shells that need non-standard CLI
        invocation (e.g., PowerShell-based invocation on WSL).
        """
        return None

    def get_extension_list_paths(self) -> list[Path]:
        """Get ordered list of extension list file paths to merge.

        Returns empty list for shells that don't manage extensions.
        """
        return []

    def get_extensions_json_path(self) -> Path | None:
        return None

    def get_additional_files(self) -> list[AdditionalFile]:
        """Get additional files that should be installed for this shell.

        Returns:
            List of AdditionalFile objects
        """
        return []

    def _discover_additional_files(
        self,
        config_dirs: list[str],
        target_dir: Path,
    ) -> list[AdditionalFile]:
        """Helper to discover additional files from config directories.

        Args:
            config_dirs: List of config directory names to scan (e.g., ["bash", "git"])
            target_dir: Target directory where files will be installed

        Returns:
            List of AdditionalFile objects
        """
        from shell_configs.config import get_config_dir

        additional_files = []
        base_config_dir = get_config_dir()

        for dir_name in config_dirs:
            config_dir = base_config_dir / dir_name
            if not config_dir.exists():
                continue

            exclude_file = "gitconfig" if dir_name == "git" else f"{dir_name}rc"

            for file_path in config_dir.iterdir():
                if file_path.is_file() and file_path.name != exclude_file:
                    additional_files.append(
                        AdditionalFile(
                            name=file_path.name,
                            source_path=file_path,
                            target_path=target_dir / file_path.name,
                        )
                    )

        return additional_files

    def get_preferences_files(self) -> list[PreferencesFile]:
        """Get preferences files to install via the macOS defaults system.

        Returns:
            List of PreferencesFile objects
        """
        return []

    def get_state_db_entries(self) -> list[StateDbEntry]:
        """Get state database entries to manage for this shell.

        Returns:
            List of StateDbEntry objects
        """
        return []

    def supports_shared_config(self) -> bool:
        """Check if this shell supports shared configuration.

        Returns:
            True if shell supports shared configs, False otherwise
        """
        return False

    def _run_validation_command(
        self, command: list[str], temp_file: Path
    ) -> tuple[bool, str]:
        """Helper to run a validation command.

        Args:
            command: Command to run
            temp_file: Path to temporary file with content

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return (True, "")
            return (False, result.stderr.strip() or result.stdout.strip())
        except FileNotFoundError:
            return (False, f"Command not found: {command[0]}")
        except subprocess.TimeoutExpired:
            return (False, "Validation timeout")
        except Exception as e:
            return (False, f"Validation error: {e}")
