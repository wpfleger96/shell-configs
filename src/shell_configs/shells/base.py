"""Base shell configuration interface."""

import json
import subprocess
import tempfile

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


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


@dataclass
class PreferencesFile:
    """Represents application preferences written via macOS defaults(1)."""

    name: str
    source_path: Path
    domain: str
    app_name: str | None = None


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

    @abstractmethod
    def _get_validation_command(self, temp_file: Path) -> list[str]:
        """Get the validation command for this shell.

        Args:
            temp_file: Path to temporary file with content

        Returns:
            Command list to execute
        """

    @abstractmethod
    def _get_temp_suffix(self) -> str:
        """Get the file suffix for temp validation files.

        Returns:
            File suffix (e.g., ".sh", ".zsh", ".gitconfig")
        """

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

    def get_preferences_files(self) -> list["PreferencesFile"]:
        """Get preferences files to install via the macOS defaults system.

        Returns:
            List of PreferencesFile objects
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
