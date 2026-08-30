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

    def test_personal_profile_shared_set_minus_a_appears_at_least_twice(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert shared.count("set -a") >= 2

    def test_personal_profile_shared_set_plus_a_appears_at_least_twice(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert shared.count("set +a") >= 2

    def test_load_tf_secrets_set_minus_a_before_first_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-tf-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set -a") < func_body.index('eval "$(enpass-cli')

    def test_load_tf_secrets_set_plus_a_after_last_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-tf-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set +a") > func_body.rindex('eval "$(enpass-cli')

    def test_load_buzz_relay_secrets_set_minus_a_before_first_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-buzz-relay-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set -a") < func_body.index('eval "$(enpass-cli')

    def test_load_buzz_relay_secrets_set_plus_a_after_last_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-buzz-relay-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set +a") > func_body.rindex('eval "$(enpass-cli')

    def test_personal_profile_shared_contains_load_snore_secrets(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "load-snore-secrets" in shared

    def test_load_snore_secrets_set_minus_a_before_first_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-snore-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set -a") < func_body.index('eval "$(enpass-cli')

    def test_load_snore_secrets_set_plus_a_after_last_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-snore-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set +a") > func_body.rindex('eval "$(enpass-cli')

    def test_load_meowdb_secrets_exports_s3_bucket(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-meowdb-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert "MEOWDB_S3_BUCKET=wpfleger-meow-media" in func_body

    def test_personal_profile_shared_contains_load_unifi_secrets(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "load-unifi-secrets" in shared

    def test_load_unifi_secrets_set_minus_a_before_first_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-unifi-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set -a") < func_body.index('eval "$(enpass-cli')

    def test_load_unifi_secrets_set_plus_a_after_last_eval(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-unifi-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert func_body.index("set +a") > func_body.rindex('eval "$(enpass-cli')

    def test_load_unifi_secrets_maps_fields_to_tf_vars(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-unifi-secrets()")
        func_body = shared[func_start : shared.index("\n}", func_start)]
        assert '-field "UNIFI_USERNAME" env TF_VAR_unifi_username=' in func_body
        assert '-field "UNIFI_PASSWORD" env TF_VAR_unifi_password=' in func_body

    def test_personal_profile_shared_contains_load_all_secrets(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "load-all-secrets" in shared

    def test_personal_profile_shared_contains_enpass_helpers(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        assert "_enpass-preflight()" in shared
        assert "_enpass-ensure-masterpw()" in shared

    def test_load_all_secrets_calls_all_loaders(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")
        func_start = shared.index("load-all-secrets()")
        func_body = shared[func_start:]
        assert "load-tf-secrets" in func_body
        assert "load-buzz-relay-secrets" in func_body
        assert "load-snore-secrets" in func_body
        assert "load-unifi-secrets" in func_body

    def test_loaders_preserve_preexisting_masterpw(
        self, real_loader: ProfileLoader
    ) -> None:
        profile = real_loader.load_profile("personal")
        shared = profile.shell_overrides.get("shared", "")

        tf_start = shared.index("load-tf-secrets()")
        tf_body = shared[tf_start : shared.index("\n}", tf_start)]
        assert "had_masterpw" in tf_body

        buzz_start = shared.index("load-buzz-relay-secrets()")
        buzz_body = shared[buzz_start : shared.index("\n}", buzz_start)]
        assert "had_masterpw" in buzz_body

        snore_start = shared.index("load-snore-secrets()")
        snore_body = shared[snore_start : shared.index("\n}", snore_start)]
        assert "had_masterpw" in snore_body
