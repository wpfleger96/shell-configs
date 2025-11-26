"""Unit tests for the ConfigManager."""

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
        config_file.write_text(
            f"Some content\n{manager.START_MARKER}\n{managed_content}\n{manager.END_MARKER}\n"
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

        result, message = manager.install_section(config_file, content)

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

        result, message = manager.install_section(config_file, content)

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
        result, message = manager.install_section(config_file, new_content)

        assert result == OperationResult.UPDATED

        section = manager.extract_managed_section(config_file)
        assert section is not None
        assert section.content == new_content

    def test_install_section_already_synced(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        content = "alias test='echo test'"

        manager.install_section(config_file, content)
        result, message = manager.install_section(config_file, content)

        assert result == OperationResult.ALREADY_SYNCED

    def test_install_section_dry_run(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        content = "alias test='echo test'"

        result, message = manager.install_section(config_file, content, dry_run=True)

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

        result, message = manager.install_additional_file(source_file, target_file)

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

        result, message = manager.install_additional_file(source_file, target_file)

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

        result, message = manager.install_additional_file(source_file, target_file)

        assert result == OperationResult.ALREADY_SYNCED

    def test_install_additional_file_source_missing(self, temp_dir):
        manager = ConfigManager()
        source_file = temp_dir / "missing.sh"
        target_file = temp_dir / "target.sh"

        result, message = manager.install_additional_file(source_file, target_file)

        assert result == OperationResult.ERROR
        assert "does not exist" in message

    def test_install_additional_file_dry_run(self, temp_dir):
        manager = ConfigManager()
        source_file = temp_dir / "source.sh"
        target_file = temp_dir / "target.sh"

        source_file.write_text("# Test content")

        result, message = manager.install_additional_file(
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
class TestConfigManagerSharedConfig:
    """Test ConfigManager shared config functionality."""

    def test_install_section_with_shared_content(self, temp_dir):
        manager = ConfigManager()
        config_file = temp_dir / "test.conf"
        shared_content = "# Shared\nalias ll='ls -la'"
        shell_content = "# Shell\nexport PS1='> '"

        result, message = manager.install_section(
            config_file, shell_content, shared_content=shared_content
        )

        assert result == OperationResult.CREATED
        assert config_file.exists()

        content = config_file.read_text()
        assert manager.START_MARKER in content
        assert manager.END_MARKER in content
        assert manager.SHARED_SECTION_MARKER in content
        assert manager.SHELL_SPECIFIC_MARKER in content
        assert shared_content in content
        assert shell_content in content
