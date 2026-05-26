"""Unit tests for the ConfigManager."""

from pathlib import Path

import pytest

from shell_configs.manager import ConfigManager, OperationResult


@pytest.mark.unit
class TestConfigManager:
    """Test the ConfigManager class."""

    def test_managed_section_detection(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"

        assert not manager.has_managed_section(config_file)
        assert manager.extract_managed_section(config_file) is None

        config_file.write_text("Some content\n")
        assert not manager.has_managed_section(config_file)
        assert manager.extract_managed_section(config_file) is None

        managed_content = "alias test='echo test'"
        _, start_marker, end_marker = manager._build_markers("#")
        config_file.write_text(
            f"Some content\n{start_marker}\n{managed_content}\n{end_marker}\n"
        )
        assert manager.has_managed_section(config_file)

        section = manager.extract_managed_section(config_file)
        assert section is not None
        assert section.content == managed_content
        assert section.start_line == 1
        assert section.end_line == 3

    def test_install_section_new_file(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        content = "alias test='echo test'"

        result, message, _ = manager.install_section(config_file, content)

        assert result == OperationResult.CREATED
        assert config_file.exists()
        assert manager.has_managed_section(config_file)

        section = manager.extract_managed_section(config_file)
        assert section is not None
        assert section.content == content

    def test_install_section_existing_file(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        config_file.write_text("Existing content\n")
        content = "alias test='echo test'"

        result, message, _ = manager.install_section(config_file, content)

        assert result == OperationResult.CREATED
        assert "Existing content" in config_file.read_text()
        assert manager.has_managed_section(config_file)

        section = manager.extract_managed_section(config_file)
        assert section is not None
        assert section.content == content

    def test_install_section_update_existing(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        old_content = "alias old='echo old'"
        new_content = "alias new='echo new'"

        manager.install_section(config_file, old_content)
        result, message, _ = manager.install_section(config_file, new_content)

        assert result == OperationResult.UPDATED

        section = manager.extract_managed_section(config_file)
        assert section is not None
        assert section.content == new_content

    def test_install_section_already_synced(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        content = "alias test='echo test'"

        manager.install_section(config_file, content)
        result, message, _ = manager.install_section(config_file, content)

        assert result == OperationResult.ALREADY_SYNCED

    def test_install_section_dry_run(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        content = "alias test='echo test'"

        result, message, _ = manager.install_section(config_file, content, dry_run=True)

        assert result == OperationResult.CREATED
        assert not config_file.exists()

    def test_uninstall_section(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"

        result, message = manager.uninstall_section(config_file)
        assert result == OperationResult.NOT_FOUND

        config_file.write_text("Some content\n")
        result, message = manager.uninstall_section(config_file)
        assert result == OperationResult.NOT_FOUND

        original_content = "Original content\n"
        managed_content = "alias test='echo test'"
        config_file.write_text(original_content)
        manager.install_section(config_file, managed_content)

        result, message = manager.uninstall_section(config_file)
        assert result == OperationResult.REMOVED
        assert not manager.has_managed_section(config_file)

        final_content = config_file.read_text()
        assert original_content.strip() in final_content

    def test_uninstall_section_dry_run(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        content = "alias test='echo test'"

        manager.install_section(config_file, content)
        result, message = manager.uninstall_section(config_file, dry_run=True)

        assert result == OperationResult.REMOVED
        assert manager.has_managed_section(config_file)


@pytest.mark.unit
class TestConfigManagerAdditionalFiles:
    """Test ConfigManager additional file methods."""

    def test_install_additional_file_new(self, temp_dir):
        manager = ConfigManager()
        source_file = temp_dir / "source.sh"
        target_file = temp_dir / "target.sh"

        source_content = "# Test script\necho 'hello'"
        source_file.write_text(source_content)

        result, message, _ = manager.install_additional_file(source_file, target_file)

        assert result == OperationResult.CREATED
        assert target_file.exists()
        assert target_file.read_text() == source_content

    def test_install_additional_file_update_existing(self, temp_dir):
        manager = ConfigManager()
        source_file = temp_dir / "source.sh"
        target_file = temp_dir / "target.sh"

        original_content = "# Original content"
        new_content = "# New content"
        target_file.write_text(original_content)
        source_file.write_text(new_content)

        result, message, _ = manager.install_additional_file(source_file, target_file)

        assert result == OperationResult.UPDATED
        assert target_file.read_text() == new_content
        assert "backup:" in message

    def test_install_additional_file_already_synced(self, temp_dir):
        manager = ConfigManager()
        source_file = temp_dir / "source.sh"
        target_file = temp_dir / "target.sh"

        content = "# Same content"
        source_file.write_text(content)
        target_file.write_text(content)

        result, message, _ = manager.install_additional_file(source_file, target_file)

        assert result == OperationResult.ALREADY_SYNCED

    def test_install_additional_file_source_missing(self, temp_dir):
        manager = ConfigManager()
        source_file = temp_dir / "missing.sh"
        target_file = temp_dir / "target.sh"

        result, message, _ = manager.install_additional_file(source_file, target_file)

        assert result == OperationResult.ERROR
        assert "does not exist" in message

    def test_install_additional_file_dry_run(self, temp_dir):
        manager = ConfigManager()
        source_file = temp_dir / "source.sh"
        target_file = temp_dir / "target.sh"

        source_file.write_text("# Test content")

        result, message, _ = manager.install_additional_file(
            source_file, target_file, dry_run=True
        )

        assert result == OperationResult.CREATED
        assert "Would create" in message
        assert not target_file.exists()

    def test_uninstall_additional_file(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.sh"

        target_file.write_text("# Test content")

        result, message = manager.uninstall_additional_file(target_file)

        assert result == OperationResult.REMOVED
        assert not target_file.exists()
        assert "backup:" in message

    def test_uninstall_additional_file_not_found(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "missing.sh"

        result, message = manager.uninstall_additional_file(target_file)

        assert result == OperationResult.NOT_FOUND

    def test_uninstall_additional_file_dry_run(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.sh"

        target_file.write_text("# Test content")

        result, message = manager.uninstall_additional_file(target_file, dry_run=True)

        assert result == OperationResult.REMOVED
        assert "Would remove" in message
        assert target_file.exists()


@pytest.mark.unit
class TestConfigManagerAdditionalFilesFromContent:
    """Test ConfigManager install_additional_file_from_content and content_matches."""

    def test_install_from_content_new(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.json"
        content = '{"key": "value"}\n'

        result, message, _ = manager.install_additional_file_from_content(
            content, target_file
        )

        assert result == OperationResult.CREATED
        assert target_file.exists()
        assert target_file.read_text() == content

    def test_install_from_content_update_existing(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.json"
        target_file.write_text('{"old": true}\n')

        new_content = '{"new": true}\n'
        result, message, diff_text = manager.install_additional_file_from_content(
            new_content, target_file
        )

        assert result == OperationResult.UPDATED
        assert target_file.read_text() == new_content
        assert "backup:" in message
        assert diff_text is not None

    def test_install_from_content_already_synced(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.json"
        content = '{"key": "value"}\n'
        target_file.write_text(content)

        result, message, _ = manager.install_additional_file_from_content(
            content, target_file
        )

        assert result == OperationResult.ALREADY_SYNCED

    def test_install_from_content_dry_run(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.json"
        content = '{"key": "value"}\n'

        result, message, _ = manager.install_additional_file_from_content(
            content, target_file, dry_run=True
        )

        assert result == OperationResult.CREATED
        assert "Would create" in message
        assert not target_file.exists()

    def test_content_matches_identical(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.json"
        content = '{"key": "value"}\n'
        target_file.write_text(content)

        assert manager.content_matches(content, target_file)

    def test_content_matches_different(self, temp_dir):
        manager = ConfigManager()
        target_file = temp_dir / "target.json"
        target_file.write_text('{"old": true}\n')

        assert not manager.content_matches('{"new": true}\n', target_file)

    def test_content_matches_missing_file(self, temp_dir):
        manager = ConfigManager()
        missing = temp_dir / "missing.json"

        assert not manager.content_matches("anything", missing)


@pytest.mark.unit
class TestConfigManagerSharedConfig:
    """Test ConfigManager shared config functionality."""

    def test_install_section_with_shared_content(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        shared_content = "# Shared\nalias ll='ls -la'"
        shell_content = "# Shell\nexport PS1='> '"

        result, message, _ = manager.install_section(
            config_file, shell_content, shared_content=shared_content
        )

        assert result == OperationResult.CREATED
        assert config_file.exists()

        _, start_marker, end_marker = manager._build_markers("#")
        content = config_file.read_text()
        assert start_marker in content
        assert end_marker in content
        assert manager.SHARED_SECTION_MARKER in content
        assert manager.SHELL_SPECIFIC_MARKER in content
        assert shared_content in content
        assert shell_content in content


@pytest.mark.unit
class TestConfigManagerIniMerge:
    """Test ConfigManager INI merge methods."""

    def _write_source(self, path: Path) -> None:
        path.write_text(
            "[Default Applications]\n"
            "text/html=wslview.desktop\n"
            "x-scheme-handler/http=wslview.desktop\n"
        )

    def test_install_ini_file_new(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        result, message, _ = manager.install_ini_file(source, target)

        assert result == OperationResult.CREATED
        assert target.exists()
        text = target.read_text()
        assert "text/html" in text
        assert "wslview.desktop" in text
        assert manager._sidecar_path(target).exists()

    def test_install_ini_file_already_synced(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        manager.install_ini_file(source, target)
        result, message, _ = manager.install_ini_file(source, target)

        assert result == OperationResult.ALREADY_SYNCED

    def test_install_ini_file_preserves_user_keys(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        target.write_text(
            "[Default Applications]\n"
            "x-scheme-handler/claude-cli=claude-code-url-handler.desktop\n"
        )

        result, message, _ = manager.install_ini_file(source, target)

        assert result == OperationResult.UPDATED
        text = target.read_text()
        assert "claude-code-url-handler.desktop" in text
        assert "wslview.desktop" in text

    def test_install_ini_file_dry_run(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        result, message, _ = manager.install_ini_file(source, target, dry_run=True)

        assert result == OperationResult.CREATED
        assert not target.exists()

    def test_check_ini_file_synced(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        assert not manager.check_ini_file_synced(source, target)

        manager.install_ini_file(source, target)
        assert manager.check_ini_file_synced(source, target)

    def test_check_ini_file_synced_with_extra_keys(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        manager.install_ini_file(source, target)
        import configparser

        cp = configparser.RawConfigParser()
        cp.optionxform = str  # type: ignore[assignment]
        cp.read_string(target.read_text())
        cp.set(
            "Default Applications",
            "x-scheme-handler/claude-cli",
            "claude-code-url-handler.desktop",
        )
        import io

        buf = io.StringIO()
        cp.write(buf)
        target.write_text(buf.getvalue())

        assert manager.check_ini_file_synced(source, target)

    def test_uninstall_ini_file(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        target.write_text(
            "[Default Applications]\n"
            "x-scheme-handler/claude-cli=claude-code-url-handler.desktop\n"
        )

        manager.install_ini_file(source, target)
        result, message = manager.uninstall_ini_file(target)

        assert result == OperationResult.REMOVED
        assert target.exists()
        text = target.read_text()
        assert "claude-code-url-handler.desktop" in text
        assert "wslview.desktop" not in text
        assert not manager._sidecar_path(target).exists()

    def test_uninstall_ini_file_removes_empty_file(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        manager.install_ini_file(source, target)
        result, message = manager.uninstall_ini_file(target)

        assert result == OperationResult.REMOVED
        assert not target.exists()

    def test_uninstall_ini_file_not_found(self, temp_dir):
        manager = ConfigManager()
        target = temp_dir / "missing.list"

        result, message = manager.uninstall_ini_file(target)

        assert result == OperationResult.NOT_FOUND

    def test_clean_corrupted_ini_markers(self, temp_dir):
        """Corrupted markers are stripped in-memory for sync comparison; content already
        matching source returns ALREADY_SYNCED without rewriting the file."""
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        target.write_text(
            "[Default Applications]\n"
            "    ########################################\n"
            "    ##### shell-configs Managed Config #####\n"
            "    ########################################\n"
            "    ########################################\n"
            "    ##### End shell-configs Managed Config #####\n"
            "    ########################################\n"
            "[Default Applications]\n"
            "text/html=wslview.desktop\n"
            "x-scheme-handler/http=wslview.desktop\n"
        )

        result, message, _ = manager.install_ini_file(source, target)

        assert result == OperationResult.ALREADY_SYNCED

    def test_install_ini_file_generates_diff(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        target.write_text("[Default Applications]\ntext/html=firefox.desktop\n")

        result, message, diff_text = manager.install_ini_file(source, target)

        assert result == OperationResult.UPDATED
        assert diff_text is not None
        assert "firefox.desktop" in diff_text
        assert "wslview.desktop" in diff_text

    def test_uninstall_ini_file_dry_run(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        manager.install_ini_file(source, target)
        result, message = manager.uninstall_ini_file(target, dry_run=True)

        assert result == OperationResult.REMOVED
        assert "Would remove" in message
        assert target.exists()
        assert manager._sidecar_path(target).exists()

    def test_install_ini_file_dry_run_shows_diff(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        target.write_text("[Default Applications]\ntext/html=firefox.desktop\n")

        result, message, diff_text = manager.install_ini_file(
            source, target, dry_run=True
        )

        assert result == OperationResult.UPDATED
        assert diff_text is not None
        assert "firefox.desktop" in diff_text
        assert not target.read_text().endswith("wslview.desktop\n")

    def test_parse_ini_handles_duplicate_sections(self, temp_dir):
        manager = ConfigManager()
        corrupted_ini = (
            "[Default Applications]\nkey1=value1\n[Default Applications]\nkey2=value2\n"
        )
        cp = manager._parse_ini(corrupted_ini)
        assert cp.has_section("Default Applications")
        assert cp.get("Default Applications", "key1") == "value1"
        assert cp.get("Default Applications", "key2") == "value2"

    def test_diff_handles_corrupted_mimeapps(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        source.write_text("[Default Applications]\ntext/html=wslview.desktop\n")
        target.write_text(
            "[Default Applications]\n"
            "    ########################################\n"
            "    ##### shell-configs Managed Config #####\n"
            "    ########################################\n"
            "[Default Applications]\n"
            "text/html=firefox.desktop\n"
        )
        manager._managed_keys_from_source(source)
        installed_cp = manager._parse_ini(target.read_text())
        assert installed_cp.has_section("Default Applications")

    def test_uninstall_ini_file_handles_corrupted_file(self, temp_dir):
        manager = ConfigManager()
        target = temp_dir / "mimeapps.list"
        sidecar = manager._sidecar_path(target)
        target.write_text(
            "[Default Applications]\nkey1=value1\n[Default Applications]\nkey2=value2\n"
        )
        sidecar.write_text('[["Default Applications", "key1"]]')
        result, message = manager.uninstall_ini_file(target)
        assert result == OperationResult.REMOVED
        content = target.read_text()
        assert "key2" in content
        assert "value2" in content
        assert "key1" not in content

    def test_dry_run_does_not_modify_file(self, temp_dir):
        """Dry-run must not write to disk — even for files with corrupted markers."""
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        original = (
            "[Default Applications]\n"
            "    ########################################\n"
            "    ##### shell-configs Managed Config #####\n"
            "    ########################################\n"
            "old=value\n"
        )
        target.write_text(original)

        manager.install_ini_file(source, target, dry_run=True)

        assert target.read_text() == original

    def test_sidecar_written_on_already_synced_migration(self, temp_dir):
        """Migration: sidecar must be created even when content already matches."""
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        target.write_text(
            "[Default Applications]\n"
            "text/html=wslview.desktop\n"
            "x-scheme-handler/http=wslview.desktop\n"
        )
        sidecar = manager._sidecar_path(target)
        assert not sidecar.exists()

        result, _, _ = manager.install_ini_file(source, target)

        assert result == OperationResult.ALREADY_SYNCED
        assert sidecar.exists()

    def test_stale_keys_removed_on_source_update(self, temp_dir):
        """Keys removed from source should be removed from the installed file."""
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        manager.install_ini_file(source, target)

        source.write_text("[Default Applications]\ntext/html=wslview.desktop\n")
        result, _, _ = manager.install_ini_file(source, target)

        assert result == OperationResult.UPDATED
        text = target.read_text()
        assert "text/html=wslview.desktop" in text
        assert "x-scheme-handler/http" not in text

    def test_install_preserves_comments(self, temp_dir):
        """User comments and formatting in the target file must survive install."""
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        target.write_text(
            "# User comment at top\n"
            "[Default Applications]\n"
            "; inline comment\n"
            "x-scheme-handler/claude-cli=claude-code-url-handler.desktop\n"
        )

        manager.install_ini_file(source, target)

        text = target.read_text()
        assert "# User comment at top" in text
        assert "; inline comment" in text
        assert "claude-code-url-handler.desktop" in text
        assert "wslview.desktop" in text

    def test_dry_run_create_message(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)

        result, message, _ = manager.install_ini_file(source, target, dry_run=True)

        assert result == OperationResult.CREATED
        assert "Would create" in message

    def test_diff_text_has_newlines(self, temp_dir):
        manager = ConfigManager()
        source = temp_dir / "source.list"
        target = temp_dir / "mimeapps.list"
        self._write_source(source)
        target.write_text("[Default Applications]\ntext/html=firefox.desktop\n")

        _, _, diff_text = manager.install_ini_file(source, target)

        assert diff_text is not None
        lines = diff_text.splitlines()
        assert len(lines) > 1
        assert any(line.startswith("---") for line in lines)

    def test_malformed_sidecar_deleted_on_uninstall(self, temp_dir):
        manager = ConfigManager()
        target = temp_dir / "mimeapps.list"
        target.write_text("[Default Applications]\nkey=value\n")
        sidecar = manager._sidecar_path(target)
        sidecar.write_text("not valid json{{")

        result, message = manager.uninstall_ini_file(target)

        assert result == OperationResult.ERROR
        assert not sidecar.exists()
