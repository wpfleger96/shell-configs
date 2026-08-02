"""Regression tests for the personal profile YAML."""

import pytest

from shell_configs.config import get_config_dir
from shell_configs.profiles.loader import ProfileLoader


@pytest.fixture
def real_loader() -> ProfileLoader:
    """ProfileLoader pointed at the real config/profiles directory."""
    return ProfileLoader(get_config_dir())


class TestPersonalProfile:
    """Smoke tests verifying the personal profile content and inheritance."""

    def test_personal_profile_extends_default(self, real_loader: ProfileLoader) -> None:
        profile = real_loader.load_profile("personal")
        assert profile.extends == "default"

    def test_personal_profile_shared_contains_enpass_vault_path(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "ENPASS_VAULT_PATH" in shared

    def test_personal_profile_shared_contains_load_tf_secrets(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "load-tf-secrets" in shared

    def test_personal_profile_shared_contains_load_buzz_relay_secrets(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "load-buzz-relay-secrets" in shared

    def test_personal_profile_shared_contains_darwin_container_path(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "in.sinew.Enpass-Desktop" in shared

    def test_resolve_personal_profile_succeeds(
        self, real_loader: ProfileLoader
    ) -> None:
        resolved = real_loader.resolve_profile("personal")
        assert resolved.name == "personal"

    def test_resolved_personal_profile_inherits_signing_emails_from_default(
        self, real_loader: ProfileLoader
    ) -> None:
        resolved = real_loader.resolve_profile("personal")
        assert resolved.signing_emails == ["pfleger.will@gmail.com"]

    def test_loaded_default_profile_signing_emails(
        self, real_loader: ProfileLoader
    ) -> None:
        default = real_loader.load_profile("default")
        assert default.signing_emails == ["pfleger.will@gmail.com"]

    def test_resolved_work_profile_signing_emails_replaces_parent(
        self, real_loader: ProfileLoader
    ) -> None:
        resolved = real_loader.resolve_profile("work")
        assert resolved.signing_emails == ["wpfleger@block.xyz"]
        assert "pfleger.will@gmail.com" not in resolved.signing_emails
