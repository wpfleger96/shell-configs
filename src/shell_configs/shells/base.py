"""Base shell configuration interface."""

import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
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

    def get_additional_files(self, repo_root: Path) -> list[AdditionalFile]:
        """Get additional files that should be installed for this shell.

        Args:
            repo_root: Root directory of the repository

        Returns:
            List of AdditionalFile objects
        """
        return []

    def _discover_additional_files(
        self,
        repo_root: Path,
        config_dirs: list[str],
        target_dir: Path,
    ) -> list[AdditionalFile]:
        """Helper to discover additional files from config directories.

        Args:
            repo_root: Root directory of the repository
            config_dirs: List of config directory names to scan (e.g., ["bash", "git"])
            target_dir: Target directory where files will be installed

        Returns:
            List of AdditionalFile objects
        """
        additional_files = []

        for dir_name in config_dirs:
            config_dir = repo_root / "config" / dir_name
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

    def supports_shared_config(self) -> bool:
        """Check if this shell supports shared configuration.

        Returns:
            True if shell supports shared configs, False otherwise
        """
        return False

    def _run_validation_command(self, command: list[str], temp_file: Path) -> tuple[bool, str]:
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
