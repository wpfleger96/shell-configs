"""Manager for shell configuration sections."""

import configparser
import difflib
import json
import logging
import os
import plistlib
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

_MISSING = object()


def _format_pref_value(value: object) -> str:
    """Format a preference value for display in diffs."""
    if isinstance(value, dict):
        return f"<dict with {len(value)} key(s)>"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


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

    def __init__(
        self,
        backup_suffix: str = "shell-configs-backup",
        backup_retention: int | None = None,
    ):
        """Initialize the config manager.

        Args:
            backup_suffix: Suffix to use for backup files
            backup_retention: Number of backup files to keep per config.
                            If None, uses default from AutoUpdateConfig.
        """
        from shell_configs.bootstrap.config import AutoUpdateConfig

        self.backup_suffix = backup_suffix
        self.backup_retention = (
            backup_retention
            if backup_retention is not None
            else AutoUpdateConfig().backup_retention
        )

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

    def strip_json_outer_brackets(self, content: str) -> str:
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
        comparison_content = self.strip_json_outer_brackets(source_content)
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

    def create_backup(
        self, config_file: Path, backup_dir: Path | None = None
    ) -> tuple[Path, list[Path]]:
        """Create a timestamped backup of a config file.

        Args:
            config_file: Path to the config file
            backup_dir: Optional directory to store backups in instead of
                        the config file's parent directory

        Returns:
            Tuple of (backup_path, removed_files)
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{config_file.name}.{self.backup_suffix}.{timestamp}"

        if backup_dir:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / backup_name
        else:
            backup_path = config_file.with_suffix(
                f"{config_file.suffix}.{self.backup_suffix}.{timestamp}"
            )

        shutil.copy2(config_file, backup_path)

        removed_files = self.cleanup_old_backups(
            config_file, keep=self.backup_retention, backup_dir=backup_dir
        )

        return backup_path, removed_files

    def find_backup_files(
        self, config_file: Path, backup_dir: Path | None = None
    ) -> list[Path]:
        """Find all shell-configs backup files for a given config file.

        Args:
            config_file: Path to the config file
            backup_dir: Optional directory where backups are stored

        Returns:
            List of backup file paths, sorted by timestamp (newest first)
        """
        search_dir = backup_dir or config_file.parent
        if not search_dir.exists():
            return []

        pattern = f"{config_file.name}.{self.backup_suffix}.*"
        backup_files = list(search_dir.glob(pattern))

        return sorted(backup_files, reverse=True)

    def cleanup_old_backups(
        self, config_file: Path, keep: int = 5, backup_dir: Path | None = None
    ) -> list[Path]:
        """Remove old backup files, keeping the N most recent.

        Args:
            config_file: Path to the config file
            keep: Number of most recent backups to keep

        Returns:
            List of removed backup file paths
        """
        backup_files = self.find_backup_files(config_file, backup_dir=backup_dir)

        if len(backup_files) <= keep:
            return []

        files_to_remove = backup_files[keep:]
        removed = []

        for backup_file in files_to_remove:
            try:
                backup_file.unlink()
                removed.append(backup_file)
            except OSError:
                pass

        return removed

    def install_section(
        self,
        config_file: Path,
        content: str | None,
        dry_run: bool = False,
        shared_content: str | None = None,
        comment_prefix: str = "#",
    ) -> tuple[OperationResult, str, str | None]:
        """Install or update a managed section in a config file.

        Args:
            config_file: Path to the config file
            content: Content to install (shell-specific content), or None for shared-only
            dry_run: If True, don't actually modify the file
            shared_content: Optional shared content to include before shell-specific content
            comment_prefix: Comment prefix to use for markers

        Returns:
            Tuple of (result, message, diff_text)
        """
        try:
            final_content = self.combine_content(shared_content, content)

            existing_section = self.extract_managed_section(config_file, comment_prefix)

            if existing_section and self.managed_content_matches(
                existing_section.content, final_content
            ):
                return (
                    OperationResult.ALREADY_SYNCED,
                    f"{config_file} is already synced",
                    None,
                )

            if dry_run:
                if existing_section:
                    return (
                        OperationResult.UPDATED,
                        f"Would update managed section in {config_file}",
                        None,
                    )
                return (
                    OperationResult.CREATED,
                    f"Would create managed section in {config_file}",
                    None,
                )

            diff_text = None
            if existing_section:
                old_lines = existing_section.content.splitlines(keepends=True)
                new_content = self.strip_json_outer_brackets(final_content)
                new_lines = new_content.splitlines(keepends=True)
                diff_lines = difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile="Previous",
                    tofile="Updated",
                    lineterm="",
                )
                diff_text = "\n".join(diff_lines)
                if not diff_text.strip():
                    diff_text = None

            if config_file.exists():
                if not os.access(config_file, os.W_OK):
                    return (
                        OperationResult.ERROR,
                        f"No write permission for {config_file}",
                        None,
                    )
                backup_path, removed_files = self.create_backup(config_file)
                backup_msg = f" (backup: {backup_path.name})"
                if removed_files:
                    backup_msg += f"; removed {len(removed_files)} old backup(s)"
            else:
                backup_msg = ""
                config_file.parent.mkdir(parents=True, exist_ok=True)

            if existing_section:
                self._update_section(config_file, final_content, comment_prefix)
                return (
                    OperationResult.UPDATED,
                    f"Updated managed section in {config_file}{backup_msg}",
                    diff_text,
                )

            self._create_section(config_file, final_content, comment_prefix)
            return (
                OperationResult.CREATED,
                f"Created managed section in {config_file}{backup_msg}",
                None,
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error installing section: {e}", None)

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

            backup_path, removed_files = self.create_backup(config_file)
            lines = config_file.read_text().splitlines(keepends=True)

            new_lines = lines[: section.start_line] + lines[section.end_line + 1 :]

            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()

            if new_lines:
                new_lines[-1] = new_lines[-1].rstrip("\n") + "\n"

            new_content = "".join(new_lines)
            self._atomic_write(config_file, new_content)

            backup_msg = f" (backup: {backup_path.name})"
            if removed_files:
                backup_msg += f"; removed {len(removed_files)} old backup(s)"

            return (
                OperationResult.REMOVED,
                f"Removed managed section from {config_file}{backup_msg}",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error removing section: {e}")

    def install_additional_file(
        self,
        source_path: Path,
        target_path: Path,
        dry_run: bool = False,
        backup_dir: Path | None = None,
    ) -> tuple[OperationResult, str, str | None]:
        """Install or update an additional file.

        Args:
            source_path: Path to source file
            target_path: Path to target file
            dry_run: If True, don't actually modify the file

        Returns:
            Tuple of (result, message, diff_text)
        """
        if not source_path.exists():
            return (
                OperationResult.ERROR,
                f"Source file does not exist: {source_path}",
                None,
            )
        try:
            content = source_path.read_text()
        except Exception as e:
            return (
                OperationResult.ERROR,
                f"Failed to read source file {source_path}: {e}",
                None,
            )
        return self.install_additional_file_from_content(
            content, target_path, dry_run=dry_run, backup_dir=backup_dir
        )

    def install_additional_file_from_content(
        self,
        content: str,
        target_path: Path,
        dry_run: bool = False,
        backup_dir: Path | None = None,
    ) -> tuple[OperationResult, str, str | None]:
        """Install or update an additional file from pre-computed content.

        Used when content is generated by merging multiple source files.

        Args:
            content: The content to install
            target_path: Path to target file
            dry_run: If True, don't actually modify the file

        Returns:
            Tuple of (result, message, diff_text)
        """
        try:
            if target_path.exists() and self.content_matches(content, target_path):
                return (
                    OperationResult.ALREADY_SYNCED,
                    f"{target_path} is already synced",
                    None,
                )

            if dry_run:
                if target_path.exists():
                    return (
                        OperationResult.UPDATED,
                        f"Would update {target_path}",
                        None,
                    )
                return (
                    OperationResult.CREATED,
                    f"Would create {target_path}",
                    None,
                )

            diff_text = None
            if target_path.exists():
                old_lines = target_path.read_text().splitlines(keepends=True)
                new_lines = content.splitlines(keepends=True)
                diff_lines = difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile="Previous",
                    tofile="Updated",
                    lineterm="",
                )
                diff_text = "\n".join(diff_lines)
                if not diff_text.strip():
                    diff_text = None

            backup_msg = ""
            if target_path.exists():
                backup_path, removed_files = self.create_backup(
                    target_path, backup_dir=backup_dir
                )
                backup_msg = f" (backup: {backup_path.name})"
                if removed_files:
                    backup_msg += f"; removed {len(removed_files)} old backup(s)"

            self._atomic_write(target_path, content)

            if backup_msg:
                return (
                    OperationResult.UPDATED,
                    f"Updated {target_path}{backup_msg}",
                    diff_text,
                )
            return (
                OperationResult.CREATED,
                f"Created {target_path}",
                None,
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error installing file: {e}", None)

    def content_matches(self, content: str, file_path: Path) -> bool:
        """Check if a file's content matches the given string.

        Args:
            content: Expected content
            file_path: Path to file to compare

        Returns:
            True if file content matches
        """
        try:
            if not file_path.exists():
                return False
            return file_path.read_text() == content
        except Exception:
            return False

    def uninstall_additional_file(
        self,
        target_path: Path,
        dry_run: bool = False,
        backup_dir: Path | None = None,
    ) -> tuple[OperationResult, str]:
        """Remove an additional file.

        Args:
            target_path: Path to target file
            dry_run: If True, don't actually remove the file
            backup_dir: Optional directory to store backups in

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

            backup_path, removed_files = self.create_backup(
                target_path, backup_dir=backup_dir
            )
            target_path.unlink()

            backup_msg = f" (backup: {backup_path.name})"
            if removed_files:
                backup_msg += f"; removed {len(removed_files)} old backup(s)"

            return (
                OperationResult.REMOVED,
                f"Removed {target_path}{backup_msg}",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error removing file: {e}")

    def _sidecar_path(self, config_file: Path) -> Path:
        return config_file.parent / f"{config_file.name}.shell-configs-keys"

    def _parse_ini(self, text: str) -> configparser.RawConfigParser:
        cp = configparser.RawConfigParser(strict=False)
        cp.optionxform = str  # type: ignore[assignment]
        cp.read_string(text)
        return cp

    def _apply_ini_keys(
        self, text: str, managed_keys: list[tuple[str, str, str]]
    ) -> str:
        lines = text.splitlines()
        current_section: str | None = None
        section_last_key_idx: dict[str, int] = {}
        key_line_idx: dict[tuple[str, str], int] = {}

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                current_section = stripped[1:-1]
            elif (
                current_section is not None
                and "=" in stripped
                and not stripped.startswith(("#", ";"))
            ):
                k = stripped.split("=", 1)[0].strip()
                key_line_idx[(current_section, k)] = i
                section_last_key_idx[current_section] = i

        updates: list[tuple[int, str]] = []
        appends_by_section: dict[str, list[str]] = {}
        new_sections: dict[str, list[str]] = {}

        for section, key, value in managed_keys:
            line_entry = f"{key}={value}"
            if (section, key) in key_line_idx:
                updates.append((key_line_idx[(section, key)], line_entry))
            elif section in section_last_key_idx:
                appends_by_section.setdefault(section, []).append(line_entry)
            else:
                new_sections.setdefault(section, []).append(line_entry)

        for idx, line_entry in updates:
            lines[idx] = line_entry

        for section, entries in sorted(
            appends_by_section.items(),
            key=lambda kv: section_last_key_idx[kv[0]],
            reverse=True,
        ):
            insert_after = section_last_key_idx[section]
            for entry in reversed(entries):
                lines.insert(insert_after + 1, entry)

        result_lines = lines
        for section, entries in new_sections.items():
            result_lines = result_lines + ["", f"[{section}]"] + entries

        return "\n".join(result_lines) + "\n"

    def _remove_ini_keys(self, text: str, keys: list[list[str]]) -> str:
        remove_set = {(s, k) for s, k in keys}
        lines = text.splitlines()
        current_section: str | None = None
        section_has_keys: dict[str, bool] = {}
        section_header_idx: dict[str, int] = {}

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                current_section = stripped[1:-1]
                if current_section not in section_has_keys:
                    section_has_keys[current_section] = False
            elif (
                current_section is not None
                and "=" in stripped
                and not stripped.startswith(("#", ";"))
            ):
                k = stripped.split("=", 1)[0].strip()
                if (current_section, k) not in remove_set:
                    section_has_keys[current_section] = True

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section_header_idx[stripped[1:-1]] = i

        result: list[str] = []
        current_section = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                current_section = stripped[1:-1]
                if not section_has_keys.get(current_section, False):
                    continue
            elif (
                current_section is not None
                and "=" in stripped
                and not stripped.startswith(("#", ";"))
            ):
                k = stripped.split("=", 1)[0].strip()
                if (current_section, k) in remove_set:
                    continue
            result.append(line)

        return "\n".join(result) + "\n"

    def _managed_keys_from_source(
        self, source_path: Path
    ) -> list[tuple[str, str, str]]:
        cp = self._parse_ini(source_path.read_text())
        return [
            (section, key, cp.get(section, key))
            for section in cp.sections()
            for key in cp.options(section)
        ]

    def _clean_corrupted_ini_markers(self, text: str) -> str:
        if "shell-configs Managed Config" not in text:
            return text
        cleaned_lines: list[str] = []
        seen_sections: set[str] = set()
        for line in text.splitlines():
            stripped = line.strip()
            if "shell-configs Managed Config" in stripped:
                continue
            if stripped == "#" * 40:
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                section = stripped
                if section in seen_sections:
                    continue
                seen_sections.add(section)
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines) + "\n"

    def diff_ini_file(self, source_path: Path, config_file: Path) -> str | None:
        try:
            managed_keys = self._managed_keys_from_source(source_path)
            installed = self._parse_ini(
                config_file.read_text() if config_file.exists() else ""
            )
            old_lines: list[str] = []
            new_lines: list[str] = []
            for section, key, value in managed_keys:
                if installed.has_section(section) and installed.has_option(
                    section, key
                ):
                    old_lines.append(f"{key}={installed.get(section, key)}\n")
                new_lines.append(f"{key}={value}\n")
            diff = "\n".join(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile="Previous",
                    tofile="Updated",
                    lineterm="",
                )
            )
            return diff if diff.strip() else None
        except Exception:
            return None

    def check_ini_file_synced(self, source_path: Path, config_file: Path) -> bool:
        if not config_file.exists():
            return False
        try:
            managed_keys = self._managed_keys_from_source(source_path)
            installed = self._parse_ini(config_file.read_text())
            return all(
                installed.has_section(section)
                and installed.has_option(section, key)
                and installed.get(section, key) == value
                for section, key, value in managed_keys
            )
        except Exception:
            return False

    def install_ini_file(
        self,
        source_path: Path,
        config_file: Path,
        dry_run: bool = False,
    ) -> tuple[OperationResult, str, str | None]:
        try:
            managed_keys = self._managed_keys_from_source(source_path)

            file_text = config_file.read_text() if config_file.exists() else ""
            file_text = self._clean_corrupted_ini_markers(file_text)

            old_sidecar_path = self._sidecar_path(config_file)
            stale_keys: list[list[str]] = []
            if old_sidecar_path.exists():
                try:
                    raw = json.loads(old_sidecar_path.read_text())
                    if isinstance(raw, list) and all(
                        isinstance(item, list)
                        and len(item) == 2
                        and all(isinstance(v, str) for v in item)
                        for item in raw
                    ):
                        current_key_set = {(s, k) for s, k, _ in managed_keys}
                        stale_keys = [
                            item
                            for item in raw
                            if (item[0], item[1]) not in current_key_set
                        ]
                except json.JSONDecodeError, Exception:
                    stale_keys = []

            installed = self._parse_ini(file_text)
            already_synced = not stale_keys and all(
                installed.has_section(s)
                and installed.has_option(s, k)
                and installed.get(s, k) == v
                for s, k, v in managed_keys
            )

            old_lines: list[str] = []
            new_lines: list[str] = []
            for section, key, value in managed_keys:
                if installed.has_section(section) and installed.has_option(
                    section, key
                ):
                    old_lines.append(f"{key}={installed.get(section, key)}\n")
                new_lines.append(f"{key}={value}\n")

            diff_text_raw = "\n".join(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile="Previous",
                    tofile="Updated",
                    lineterm="",
                )
            )
            diff_text = diff_text_raw if diff_text_raw.strip() else None

            file_existed = config_file.exists()
            new_sidecar_data = [[s, k] for s, k, _ in managed_keys]

            if already_synced:
                if not old_sidecar_path.exists():
                    self._atomic_write(
                        old_sidecar_path, json.dumps(new_sidecar_data) + "\n"
                    )
                return (
                    OperationResult.ALREADY_SYNCED,
                    f"{config_file} is already synced",
                    None,
                )

            if dry_run:
                action = "Would create" if not file_existed else "Would update"
                return (
                    OperationResult.CREATED
                    if not file_existed
                    else OperationResult.UPDATED,
                    f"{action} {config_file}",
                    diff_text,
                )

            if stale_keys:
                file_text = self._remove_ini_keys(file_text, stale_keys)

            new_text = self._apply_ini_keys(file_text, managed_keys)

            backup_msg = ""
            if file_existed:
                backup_path, removed_files = self.create_backup(config_file)
                backup_msg = f" (backup: {backup_path.name})"
                if removed_files:
                    backup_msg += f"; removed {len(removed_files)} old backup(s)"

            self._atomic_write(config_file, new_text)
            self._atomic_write(
                self._sidecar_path(config_file), json.dumps(new_sidecar_data) + "\n"
            )

            return (
                OperationResult.UPDATED if file_existed else OperationResult.CREATED,
                f"{'Updated' if file_existed else 'Created'} {config_file}{backup_msg}",
                diff_text,
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error installing INI file: {e}", None)

    def uninstall_ini_file(
        self,
        config_file: Path,
        dry_run: bool = False,
    ) -> tuple[OperationResult, str]:
        try:
            sidecar = self._sidecar_path(config_file)
            if not config_file.exists() and not sidecar.exists():
                return (
                    OperationResult.NOT_FOUND,
                    f"{config_file} does not exist",
                )

            if dry_run:
                return (
                    OperationResult.REMOVED,
                    f"Would remove managed keys from {config_file}",
                )

            if sidecar.exists():
                try:
                    raw = json.loads(sidecar.read_text())
                    if not (
                        isinstance(raw, list)
                        and all(
                            isinstance(item, list)
                            and len(item) == 2
                            and all(isinstance(v, str) for v in item)
                            for item in raw
                        )
                    ):
                        sidecar.unlink()
                        return (
                            OperationResult.ERROR,
                            f"Sidecar for {config_file} is malformed; deleted it. Re-run install to repair.",
                        )
                    keys: list[list[str]] = raw
                except json.JSONDecodeError:
                    sidecar.unlink()
                    return (
                        OperationResult.ERROR,
                        f"Sidecar for {config_file} could not be parsed; deleted it. Re-run install to repair.",
                    )
            else:
                keys = []

            if config_file.exists() and keys:
                text = config_file.read_text()
                new_text = self._remove_ini_keys(text, keys)
                remaining = self._parse_ini(new_text)

                backup_path, removed_files = self.create_backup(config_file)
                backup_msg = f" (backup: {backup_path.name})"
                if removed_files:
                    backup_msg += f"; removed {len(removed_files)} old backup(s)"

                if remaining.sections():
                    self._atomic_write(config_file, new_text)
                else:
                    config_file.unlink()
            else:
                backup_msg = ""

            if sidecar.exists():
                sidecar.unlink()

            return (
                OperationResult.REMOVED,
                f"Removed managed keys from {config_file}{backup_msg}",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error uninstalling INI file: {e}")

    def _parse_guiconfigs_from_source(self, source_path: Path) -> list[ET.Element]:
        """Parse <GUIConfig> elements from a partial source XML file."""
        tree = ET.parse(source_path)
        root = tree.getroot()
        guiconfigs = root.find("GUIConfigs")
        if guiconfigs is None:
            return []
        return list(guiconfigs)

    def check_xml_guiconfig_synced(self, source_path: Path, config_file: Path) -> bool:
        """Check if all managed GUIConfig elements match the target file."""
        if not config_file.exists():
            return False
        try:
            managed = self._parse_guiconfigs_from_source(source_path)
            target_tree = ET.parse(config_file)
            target_root = target_tree.getroot()
            target_guiconfigs = target_root.find("GUIConfigs")
            if target_guiconfigs is None:
                return False
            for src_elem in managed:
                name = src_elem.get("name")
                target_elem = next(
                    (e for e in target_guiconfigs if e.get("name") == name),
                    None,
                )
                if target_elem is None:
                    return False
                if src_elem.attrib != target_elem.attrib:
                    return False
                if (
                    src_elem.text
                    and src_elem.text.strip() != (target_elem.text or "").strip()
                ):
                    return False
            return True
        except Exception:
            return False

    def diff_xml_guiconfig_file(
        self, source_path: Path, config_file: Path
    ) -> str | None:
        """Return a human-readable diff of managed GUIConfig elements vs target."""
        try:
            managed = self._parse_guiconfigs_from_source(source_path)
            target_exists = config_file.exists()
            target_tree = ET.parse(config_file) if target_exists else None
            target_root = target_tree.getroot() if target_tree else None
            target_guiconfigs = (
                target_root.find("GUIConfigs") if target_root is not None else None
            )

            lines = []
            for src_elem in managed:
                name = src_elem.get("name")
                target_elem = (
                    next(
                        (e for e in target_guiconfigs if e.get("name") == name),
                        None,
                    )
                    if target_guiconfigs is not None
                    else None
                )
                src_str = ET.tostring(src_elem, encoding="unicode").strip()
                if target_elem is None:
                    lines.append(f"  + {src_str}")
                else:
                    tgt_str = ET.tostring(target_elem, encoding="unicode").strip()
                    if src_str != tgt_str:
                        lines.append(f"  ~ {tgt_str} → {src_str}")
            return "\n".join(lines) if lines else None
        except Exception:
            return None

    def install_xml_guiconfig_file(
        self,
        source_path: Path,
        config_file: Path,
        dry_run: bool = False,
    ) -> tuple[OperationResult, str, str | None]:
        """Merge managed GUIConfig elements into an existing Notepad++ config.xml.

        Requires the target file to already exist — we do not create it from
        scratch because Notepad++ config.xml has dozens of required elements.
        """
        try:
            if not source_path.exists():
                return (
                    OperationResult.ERROR,
                    f"Source file does not exist: {source_path}",
                    None,
                )
            if not config_file.exists():
                return (
                    OperationResult.ERROR,
                    f"Target config does not exist: {config_file} "
                    "(Notepad++ must be installed and launched at least once)",
                    None,
                )

            if self.check_xml_guiconfig_synced(source_path, config_file):
                return (
                    OperationResult.ALREADY_SYNCED,
                    f"{config_file} is already synced",
                    None,
                )

            diff_text = self.diff_xml_guiconfig_file(source_path, config_file)

            if dry_run:
                return (
                    OperationResult.UPDATED,
                    f"Would update {config_file}",
                    diff_text,
                )

            managed = self._parse_guiconfigs_from_source(source_path)
            target_tree = ET.parse(config_file)
            target_root = target_tree.getroot()
            target_guiconfigs = target_root.find("GUIConfigs")
            if target_guiconfigs is None:
                target_guiconfigs = ET.SubElement(target_root, "GUIConfigs")

            for src_elem in managed:
                name = src_elem.get("name")
                target_elem = next(
                    (e for e in target_guiconfigs if e.get("name") == name),
                    None,
                )
                if target_elem is not None:
                    target_elem.attrib.clear()
                    target_elem.attrib.update(src_elem.attrib)
                    if src_elem.text and src_elem.text.strip():
                        target_elem.text = src_elem.text
                else:
                    import copy as _copy

                    target_guiconfigs.append(_copy.deepcopy(src_elem))

            backup_path, removed_files = self.create_backup(config_file)
            backup_msg = f" (backup: {backup_path.name})"
            if removed_files:
                backup_msg += f"; removed {len(removed_files)} old backup(s)"

            ET.indent(target_tree, space="    ")
            xml_content = ET.tostring(
                target_root, encoding="unicode", xml_declaration=False
            )
            xml_content = (
                '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content + "\n"
            )
            self._atomic_write(config_file, xml_content)

            return (
                OperationResult.UPDATED,
                f"Updated {config_file}{backup_msg}",
                diff_text,
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error updating XML config: {e}", None)

    def uninstall_xml_guiconfig_file(
        self,
        source_path: Path,
        config_file: Path,
        dry_run: bool = False,
    ) -> tuple[OperationResult, str]:
        """Remove managed GUIConfig elements from target by resetting to defaults.

        Since we can't know the original values, we remove the attributes we
        set and leave the elements with only their 'name' attribute, which
        prompts Notepad++ to use its built-in defaults on next launch.
        """
        try:
            if not config_file.exists():
                return (
                    OperationResult.NOT_FOUND,
                    f"{config_file} does not exist",
                )
            if not source_path.exists():
                return (
                    OperationResult.ERROR,
                    f"Source file does not exist: {source_path}",
                )

            managed = self._parse_guiconfigs_from_source(source_path)
            managed_names = {e.get("name") for e in managed}

            target_tree = ET.parse(config_file)
            target_root = target_tree.getroot()
            target_guiconfigs = target_root.find("GUIConfigs")

            if target_guiconfigs is None:
                return (
                    OperationResult.NOT_FOUND,
                    f"No GUIConfigs section found in {config_file}",
                )

            found = any(e.get("name") in managed_names for e in target_guiconfigs)
            if not found:
                return (
                    OperationResult.NOT_FOUND,
                    f"No managed GUIConfig elements found in {config_file}",
                )

            if dry_run:
                return (
                    OperationResult.REMOVED,
                    f"Would remove managed GUIConfig elements from {config_file}",
                )

            backup_path, removed_files = self.create_backup(config_file)
            backup_msg = f" (backup: {backup_path.name})"
            if removed_files:
                backup_msg += f"; removed {len(removed_files)} old backup(s)"

            for elem in list(target_guiconfigs):
                if elem.get("name") in managed_names:
                    target_guiconfigs.remove(elem)

            ET.indent(target_tree, space="    ")
            xml_content = ET.tostring(
                target_root, encoding="unicode", xml_declaration=False
            )
            xml_content = (
                '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content + "\n"
            )
            self._atomic_write(config_file, xml_content)

            return (
                OperationResult.REMOVED,
                f"Removed managed GUIConfig elements from {config_file}{backup_msg}",
            )

        except Exception as e:
            return (OperationResult.ERROR, f"Error uninstalling XML config: {e}")

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

    def _export_defaults_domain(self, domain: str) -> dict[str, object] | None:
        """Export a macOS defaults domain as a Python dict.

        Args:
            domain: The preferences domain (e.g., "com.googlecode.iterm2")

        Returns:
            Dict of all domain keys, or None if the domain doesn't exist
        """
        try:
            result = subprocess.run(
                ["defaults", "export", domain, "-"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace").lower()
                if "does not exist" not in stderr:
                    logger.debug("defaults export failed for %s: %s", domain, stderr)
                return None
            data: dict[str, object] = plistlib.loads(result.stdout)
            return data
        except Exception as e:
            logger.debug("defaults export error for %s: %s", domain, e)
            return None

    def _check_app_running(self, app_name: str) -> str | None:
        """Check if an application is running and return a warning if so.

        Args:
            app_name: Process name to check (e.g., "iTerm2")

        Returns:
            Warning message string, or None if not running
        """
        try:
            result = subprocess.run(
                ["pgrep", "-x", app_name],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return (
                    f"{app_name} is running — "
                    f"preference changes take effect after restart"
                )
        except Exception:
            pass
        return None

    def install_preferences_file(
        self,
        source_path: Path,
        domain: str,
        dry_run: bool = False,
        app_name: str | None = None,
    ) -> tuple[OperationResult, str, str | None]:
        """Install preferences from a JSON file into a macOS defaults domain.

        Reads the JSON file, converts managed keys to a plist, and writes
        via 'defaults import'. Only managed keys are written; other domain
        keys are untouched (defaults import merges at the top level).

        Note: nested dict values (e.g., GlobalKeyMap) are replaced entirely,
        not recursively merged. This is intentional — managed dicts represent
        the complete desired state.

        Args:
            source_path: Path to JSON file with managed preferences
            domain: macOS preferences domain
            dry_run: If True, don't actually modify preferences

        Returns:
            Tuple of (result, message, diff_text)
        """
        try:
            if not source_path.exists():
                return (
                    OperationResult.ERROR,
                    f"Source file does not exist: {source_path}",
                    None,
                )

            managed_prefs = json.loads(source_path.read_text())

            null_keys = [k for k, v in managed_prefs.items() if v is None]
            if null_keys:
                return (
                    OperationResult.ERROR,
                    f"Null values not supported in preferences: {', '.join(null_keys)}",
                    None,
                )

            domain_data = self._export_defaults_domain(domain)
            exists = domain_data is not None

            if exists and domain_data is not None:
                all_match = all(
                    domain_data.get(key) == value
                    for key, value in managed_prefs.items()
                )
                if all_match:
                    return (
                        OperationResult.ALREADY_SYNCED,
                        f"{domain} preferences are already synced",
                        None,
                    )

            if dry_run:
                action = "update" if exists else "create"
                return (
                    OperationResult.UPDATED if exists else OperationResult.CREATED,
                    f"Would {action} {len(managed_prefs)} preference(s) in {domain}",
                    None,
                )

            diff_text = self._build_preferences_diff(managed_prefs, domain_data or {})

            temp_path = None
            try:
                fd, temp_path = tempfile.mkstemp(suffix=".plist")
                os.close(fd)
                with open(temp_path, "wb") as f:
                    plistlib.dump(managed_prefs, f, fmt=plistlib.FMT_XML)

                result = subprocess.run(
                    ["defaults", "import", domain, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    return (
                        OperationResult.ERROR,
                        f"defaults import failed: {result.stderr.strip()}",
                        None,
                    )
            finally:
                if temp_path:
                    Path(temp_path).unlink(missing_ok=True)

            action = "Updated" if exists else "Created"
            message = f"{action} {len(managed_prefs)} preference(s) in {domain}"

            if app_name:
                warning = self._check_app_running(app_name)
                if warning:
                    message += f"\n  ⚠ {warning}"

            return (
                OperationResult.UPDATED if exists else OperationResult.CREATED,
                message,
                diff_text,
            )

        except Exception as e:
            return (
                OperationResult.ERROR,
                f"Error installing preferences: {e}",
                None,
            )

    def uninstall_preferences_file(
        self,
        source_path: Path,
        domain: str,
        dry_run: bool = False,
        app_name: str | None = None,
    ) -> tuple[OperationResult, str]:
        """Remove managed preference keys from a macOS defaults domain.

        Args:
            source_path: Path to JSON file with managed preference keys
            domain: macOS preferences domain
            dry_run: If True, don't actually modify preferences

        Returns:
            Tuple of (result, message)
        """
        try:
            if not source_path.exists():
                return (
                    OperationResult.ERROR,
                    f"Source file does not exist: {source_path}",
                )

            managed_prefs = json.loads(source_path.read_text())
            domain_data = self._export_defaults_domain(domain)

            if domain_data is None:
                return (
                    OperationResult.NOT_FOUND,
                    f"Domain {domain} does not exist",
                )

            existing_keys = [k for k in managed_prefs if k in domain_data]
            if not existing_keys:
                return (
                    OperationResult.NOT_FOUND,
                    f"No managed preferences found in {domain}",
                )

            if dry_run:
                return (
                    OperationResult.REMOVED,
                    f"Would delete {len(existing_keys)} preference(s) from {domain}",
                )

            deleted = 0
            failed: list[str] = []
            for key in existing_keys:
                result = subprocess.run(
                    ["defaults", "delete", domain, key],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    deleted += 1
                else:
                    failed.append(key)

            if failed:
                message = (
                    f"Deleted {deleted} preference(s) from {domain}; "
                    f"{len(failed)} failed: {', '.join(failed)}"
                )
            else:
                message = f"Deleted {deleted} preference(s) from {domain}"

            if app_name:
                warning = self._check_app_running(app_name)
                if warning:
                    message += f"\n  ⚠ {warning}"

            return (OperationResult.REMOVED, message)

        except Exception as e:
            return (OperationResult.ERROR, f"Error removing preferences: {e}")

    def check_preferences_file_status(
        self, source_path: Path, domain: str
    ) -> tuple[bool, bool]:
        """Check if managed preferences are installed and synced.

        Args:
            source_path: Path to JSON file with managed preferences
            domain: macOS preferences domain

        Returns:
            Tuple of (exists, synced) where:
            - exists = at least one managed key is present in the domain
            - synced = all managed keys match the expected values
        """
        try:
            if not source_path.exists():
                return (False, False)

            managed_prefs = json.loads(source_path.read_text())
            domain_data = self._export_defaults_domain(domain)

            if domain_data is None:
                return (False, False)

            exists = any(key in domain_data for key in managed_prefs)
            synced = all(
                domain_data.get(key) == value for key, value in managed_prefs.items()
            )

            return (exists, synced)
        except Exception:
            return (False, False)

    def diff_preferences_file(self, source_path: Path, domain: str) -> str | None:
        """Get a human-readable diff between repo preferences and installed.

        Args:
            source_path: Path to JSON file with managed preferences
            domain: macOS preferences domain

        Returns:
            Multi-line string showing changed/missing keys, or None if synced
        """
        try:
            if not source_path.exists():
                return None

            managed_prefs = json.loads(source_path.read_text())
            domain_data = self._export_defaults_domain(domain)

            return self._build_preferences_diff(managed_prefs, domain_data or {})
        except Exception:
            return None

    def _build_preferences_diff(
        self,
        managed_prefs: dict[str, object],
        domain_data: dict[str, object],
    ) -> str | None:
        """Build a human-readable diff between managed and installed prefs.

        Args:
            managed_prefs: Expected preference values
            domain_data: Current domain values

        Returns:
            Formatted diff string, or None if all match
        """
        lines = []
        for key, expected in sorted(managed_prefs.items()):
            current = domain_data.get(key, _MISSING)
            if current is _MISSING:
                lines.append(f"  + {key}: {_format_pref_value(expected)}")
            elif current != expected:
                lines.append(
                    f"  ~ {key}: "
                    f"{_format_pref_value(current)} → "
                    f"{_format_pref_value(expected)}"
                )

        if not lines:
            return None
        return "\n".join(lines)
