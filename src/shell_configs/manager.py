"""Manager for shell configuration sections."""

import os
import shutil
import tempfile

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class OperationResult(Enum):
    """Result of a configuration operation."""

    CREATED = "created"
    UPDATED = "updated"
    REMOVED = "removed"
    ALREADY_SYNCED = "already_synced"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class ManagedSection:
    """Represents a managed configuration section."""

    content: str
    start_line: int
    end_line: int


class ConfigManager:
    """Manages configuration sections in shell config files."""

    SHARED_SECTION_MARKER = "### Shared Config ###"
    SHELL_SPECIFIC_MARKER = "### Shell-Specific Config ###"

    def __init__(self, backup_suffix: str = "shell-configs-backup"):
        """Initialize the config manager.

        Args:
            backup_suffix: Suffix to use for backup files
        """
        self.backup_suffix = backup_suffix

    def _build_markers(self, prefix: str) -> tuple[str, str, str]:
        """Build marker strings with given comment prefix.

        Args:
            prefix: Comment prefix to use (e.g., '#', '//')

        Returns:
            Tuple of (decoration, start_marker, end_marker)
        """
        decoration = prefix * 40
        start_marker = f"{prefix * 5} shell-configs Managed Config {prefix * 5}"
        end_marker = f"{prefix * 5} End shell-configs Managed Config {prefix * 5}"
        return decoration, start_marker, end_marker

    def _is_json_content(self, content: str) -> bool:
        """Check if content appears to be JSON/JSONC format.

        Args:
            content: Content to check

        Returns:
            True if content looks like JSON
        """
        stripped = content.strip()
        return stripped.startswith("{") or stripped.startswith("[")

    def _strip_json_outer_brackets(self, content: str) -> str:
        """Strip outer { } or [ ] from JSON content for comparison.

        When markers are injected inside JSON brackets, we need to strip
        the outer brackets from source content before comparing with
        extracted managed section content.

        Args:
            content: JSON content with outer brackets

        Returns:
            Content with outer brackets removed
        """
        if not self._is_json_content(content):
            return content

        lines = content.splitlines()
        if not lines:
            return content

        if lines[0].strip() in ("{", "["):
            lines = lines[1:]

        if lines and lines[-1].strip() in ("}", "]"):
            lines = lines[:-1]

        return "\n".join(lines)

    def managed_content_matches(
        self, section_content: str, source_content: str
    ) -> bool:
        """Compare managed section content against source, handling JSON brackets.

        For JSON files, markers are injected inside brackets, so we strip
        outer brackets from source before comparing.

        Args:
            section_content: Content extracted from managed section
            source_content: Content from source file

        Returns:
            True if contents match
        """
        comparison_content = self._strip_json_outer_brackets(source_content)
        return section_content.strip() == comparison_content.strip()

    def has_managed_section(self, config_file: Path, comment_prefix: str = "#") -> bool:
        """Check if a config file has a managed section.

        Args:
            config_file: Path to the config file
            comment_prefix: Comment prefix to use for markers

        Returns:
            True if a managed section exists
        """
        if not config_file.exists():
            return False

        _, start_marker, end_marker = self._build_markers(comment_prefix)
        content = config_file.read_text()
        return start_marker in content and end_marker in content

    def extract_managed_section(
        self, config_file: Path, comment_prefix: str = "#"
    ) -> ManagedSection | None:
        """Extract the managed section from a config file.

        Args:
            config_file: Path to the config file
            comment_prefix: Comment prefix to use for markers

        Returns:
            ManagedSection if found, None otherwise
        """
        if not config_file.exists():
            return None

        decoration, start_marker, end_marker = self._build_markers(comment_prefix)
        lines = config_file.read_text().splitlines(keepends=True)
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i
            elif end_marker in line and start_idx is not None:
                end_idx = i
                break

        if start_idx is None or end_idx is None:
            return None

        content_start = start_idx + 1
        if content_start < len(lines) and decoration in lines[content_start]:
            content_start += 1

        content_end = end_idx
        if content_end > 0 and decoration in lines[content_end - 1]:
            content_end -= 1

        content_lines = lines[content_start:content_end]
        content = "".join(content_lines).rstrip("\n")

        return ManagedSection(content=content, start_line=start_idx, end_line=end_idx)

    def create_backup(self, config_file: Path) -> Path:
        """Create a timestamped backup of a config file.

        Args:
            config_file: Path to the config file

        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = config_file.with_suffix(
            f"{config_file.suffix}.{self.backup_suffix}.{timestamp}"
        )
        shutil.copy2(config_file, backup_path)
        return backup_path

    def install_section(
        self,
        config_file: Path,
        content: str | None,
        dry_run: bool = False,
        shared_content: str | None = None,
        comment_prefix: str = "#",
    ) -> tuple[OperationResult, str]:
        """Install or update a managed section in a config file.

        Args:
            config_file: Path to the config file
            content: Content to install (shell-specific content), or None for shared-only
            dry_run: If True, don't actually modify the file
            shared_content: Optional shared content to include before shell-specific content
            comment_prefix: Comment prefix to use for markers

        Returns:
            Tuple of (result, message)
        """
        try:
            final_content = self.combine_content(shared_content, content)

            existing_section = self.extract_managed_section(config_file, comment_prefix)

            if (
                existing_section
                and existing_section.content.strip() == final_content.strip()
            ):
                return (
                    OperationResult.ALREADY_SYNCED,
                    f"{config_file} is already synced",
                )

            if dry_run:
                if existing_section:
                    return (
                        OperationResult.UPDATED,
                        f"Would update managed section in {config_file}",
                    )
                return (
                    OperationResult.CREATED,
                    f"Would create managed section in {config_file}",
                )

            if config_file.exists():
                if not os.access(config_file, os.W_OK):
                    return (
                        OperationResult.ERROR,
                        f"No write permission for {config_file}",
                    )
                backup_path = self.create_backup(config_file)
                backup_msg = f" (backup: {backup_path.name})"
            else:
                backup_msg = ""
                config_file.parent.mkdir(parents=True, exist_ok=True)

            if existing_section:
                self._update_section(config_file, final_content, comment_prefix)
                return (
                    OperationResult.UPDATED,
                    f"Updated managed section in {config_file}{backup_msg}",
                )

            self._create_section(config_file, final_content, comment_prefix)
            return (
                OperationResult.CREATED,
                f"Created managed section in {config_file}{backup_msg}",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error installing section: {e}")

    def combine_content(
        self, shared_content: str | None, shell_content: str | None
    ) -> str:
        """Combine shared and shell-specific content with subsection markers.

        Args:
            shared_content: Optional shared content
            shell_content: Optional shell-specific content

        Returns:
            Combined content with subsection markers if both exist, or just the available content
        """
        has_shared = shared_content is not None and shared_content.strip()
        has_shell = shell_content is not None and shell_content.strip()

        if not has_shared and not has_shell:
            return ""

        if not has_shared:
            assert shell_content is not None
            return shell_content

        if not has_shell:
            assert shared_content is not None
            return shared_content

        parts: list[str] = []
        assert shared_content is not None
        assert shell_content is not None
        parts.append(self.SHARED_SECTION_MARKER)
        parts.append(shared_content)
        parts.append("")
        parts.append(self.SHELL_SPECIFIC_MARKER)
        parts.append(shell_content)

        return "\n".join(parts)

    def _create_section(
        self, config_file: Path, content: str, comment_prefix: str = "#"
    ) -> None:
        """Create a new managed section in a config file.

        Args:
            config_file: Path to the config file
            content: Content to add
            comment_prefix: Comment prefix to use for markers
        """
        decoration, start_marker, end_marker = self._build_markers(comment_prefix)

        if self._is_json_content(content):
            lines = content.splitlines()
            if not lines:
                new_content = ""
            else:
                opening_idx = None
                closing_idx = None

                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if opening_idx is None and stripped.startswith(("{", "[")):
                        opening_idx = i
                    if stripped.endswith(("}", "]")):
                        closing_idx = i

                if opening_idx is not None and closing_idx is not None:
                    wrapped_lines = lines[: opening_idx + 1]
                    wrapped_lines.extend(
                        [
                            f"    {decoration}",
                            f"    {start_marker}",
                            f"    {decoration}",
                        ]
                    )
                    wrapped_lines.extend(lines[opening_idx + 1 : closing_idx])
                    wrapped_lines.extend(
                        [
                            f"    {decoration}",
                            f"    {end_marker}",
                            f"    {decoration}",
                        ]
                    )
                    wrapped_lines.extend(lines[closing_idx:])

                    new_content = "\n".join(wrapped_lines) + "\n"
                else:
                    new_content = f"{decoration}\n{start_marker}\n{decoration}\n{content}\n{decoration}\n{end_marker}\n{decoration}\n"
        else:
            if config_file.exists():
                existing_content = config_file.read_text()
                if existing_content and not existing_content.endswith("\n"):
                    existing_content += "\n"
            else:
                existing_content = ""
            new_content = f"{existing_content}\n{decoration}\n{start_marker}\n{decoration}\n{content}\n{decoration}\n{end_marker}\n{decoration}\n"

        self._atomic_write(config_file, new_content)

    def _update_section(
        self, config_file: Path, content: str, comment_prefix: str = "#"
    ) -> None:
        """Update an existing managed section in a config file.

        Args:
            config_file: Path to the config file
            content: New content
            comment_prefix: Comment prefix to use for markers
        """
        decoration, start_marker, end_marker = self._build_markers(comment_prefix)
        lines = config_file.read_text().splitlines(keepends=True)
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i
            elif end_marker in line and start_idx is not None:
                end_idx = i
                break

        if start_idx is None or end_idx is None:
            raise ValueError("Managed section markers not found")

        start_boundary = start_idx
        if start_idx > 0 and decoration in lines[start_idx - 1]:
            start_boundary = start_idx - 1

        end_boundary = end_idx
        if end_idx < len(lines) - 1 and decoration in lines[end_idx + 1]:
            end_boundary = end_idx + 1

        if self._is_json_content(content):
            content_lines = content.splitlines()
            if not content_lines:
                new_section: list[str] = []
            else:
                opening_idx = None
                closing_idx = None

                for i, line in enumerate(content_lines):
                    stripped = line.strip()
                    if opening_idx is None and stripped.startswith(("{", "[")):
                        opening_idx = i
                    if stripped.endswith(("}", "]")):
                        closing_idx = i

                if opening_idx is not None and closing_idx is not None:
                    new_section = []
                    for line in content_lines[: opening_idx + 1]:
                        new_section.append(f"{line}\n")
                    new_section.extend(
                        [
                            f"    {decoration}\n",
                            f"    {start_marker}\n",
                            f"    {decoration}\n",
                        ]
                    )
                    for line in content_lines[opening_idx + 1 : closing_idx]:
                        new_section.append(f"{line}\n")
                    new_section.extend(
                        [
                            f"    {decoration}\n",
                            f"    {end_marker}\n",
                            f"    {decoration}\n",
                        ]
                    )
                    for line in content_lines[closing_idx:]:
                        new_section.append(f"{line}\n")
                else:
                    new_section = [
                        f"{decoration}\n",
                        f"{start_marker}\n",
                        f"{decoration}\n",
                        f"{content}\n",
                        f"{decoration}\n",
                        f"{end_marker}\n",
                        f"{decoration}\n",
                    ]
        else:
            new_section = [
                f"{decoration}\n",
                f"{start_marker}\n",
                f"{decoration}\n",
                f"{content}\n",
                f"{decoration}\n",
                f"{end_marker}\n",
                f"{decoration}\n",
            ]

        if self._is_json_content(content):
            new_content = "".join(new_section)
        else:
            new_lines = lines[:start_boundary] + new_section + lines[end_boundary + 1 :]
            new_content = "".join(new_lines)

        self._atomic_write(config_file, new_content)

    def uninstall_section(
        self, config_file: Path, dry_run: bool = False, comment_prefix: str = "#"
    ) -> tuple[OperationResult, str]:
        """Remove a managed section from a config file.

        Args:
            config_file: Path to the config file
            dry_run: If True, don't actually modify the file
            comment_prefix: Comment prefix to use for markers

        Returns:
            Tuple of (result, message)
        """
        try:
            if not config_file.exists():
                return (
                    OperationResult.NOT_FOUND,
                    f"{config_file} does not exist",
                )

            section = self.extract_managed_section(config_file, comment_prefix)
            if not section:
                return (
                    OperationResult.NOT_FOUND,
                    f"No managed section found in {config_file}",
                )

            if dry_run:
                return (
                    OperationResult.REMOVED,
                    f"Would remove managed section from {config_file}",
                )

            backup_path = self.create_backup(config_file)
            lines = config_file.read_text().splitlines(keepends=True)

            new_lines = lines[: section.start_line] + lines[section.end_line + 1 :]

            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()

            if new_lines:
                new_lines[-1] = new_lines[-1].rstrip("\n") + "\n"

            new_content = "".join(new_lines)
            self._atomic_write(config_file, new_content)

            return (
                OperationResult.REMOVED,
                f"Removed managed section from {config_file} (backup: {backup_path.name})",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error removing section: {e}")

    def install_additional_file(
        self, source_path: Path, target_path: Path, dry_run: bool = False
    ) -> tuple[OperationResult, str]:
        """Install or update an additional file.

        Args:
            source_path: Path to source file
            target_path: Path to target file
            dry_run: If True, don't actually modify the file

        Returns:
            Tuple of (result, message)
        """
        try:
            if not source_path.exists():
                return (
                    OperationResult.ERROR,
                    f"Source file does not exist: {source_path}",
                )

            source_content = source_path.read_text()

            if target_path.exists() and self.files_match(source_path, target_path):
                return (
                    OperationResult.ALREADY_SYNCED,
                    f"{target_path} is already synced",
                )

            if dry_run:
                if target_path.exists():
                    return (
                        OperationResult.UPDATED,
                        f"Would update {target_path}",
                    )
                return (
                    OperationResult.CREATED,
                    f"Would create {target_path}",
                )

            backup_msg = ""
            if target_path.exists():
                backup_path = self.create_backup(target_path)
                backup_msg = f" (backup: {backup_path.name})"

            self._atomic_write(target_path, source_content)

            if backup_msg:
                return (
                    OperationResult.UPDATED,
                    f"Updated {target_path}{backup_msg}",
                )
            return (
                OperationResult.CREATED,
                f"Created {target_path}",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error installing file: {e}")

    def uninstall_additional_file(
        self, target_path: Path, dry_run: bool = False
    ) -> tuple[OperationResult, str]:
        """Remove an additional file.

        Args:
            target_path: Path to target file
            dry_run: If True, don't actually remove the file

        Returns:
            Tuple of (result, message)
        """
        try:
            if not target_path.exists():
                return (
                    OperationResult.NOT_FOUND,
                    f"{target_path} does not exist",
                )

            if dry_run:
                return (
                    OperationResult.REMOVED,
                    f"Would remove {target_path}",
                )

            backup_path = self.create_backup(target_path)
            target_path.unlink()

            return (
                OperationResult.REMOVED,
                f"Removed {target_path} (backup: {backup_path.name})",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error removing file: {e}")

    def files_match(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            True if files have identical content
        """
        try:
            if not file1.exists() or not file2.exists():
                return False
            return file1.read_text() == file2.read_text()
        except Exception:
            return False

    def _atomic_write(self, file_path: Path, content: str) -> None:
        """Write content to a file atomically.

        Args:
            file_path: Path to the file
            content: Content to write
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent, prefix=f".{file_path.name}."
        )
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)

            if file_path.exists():
                shutil.copystat(file_path, temp_path)
            shutil.move(temp_path, file_path)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
