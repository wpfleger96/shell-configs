"""Active profile resolution."""

from shell_configs.profiles.loader import ProfileLoader
from shell_configs.profiles.profile import Profile


def resolve_active_profile(
    flag_value: str | None,
    loader: ProfileLoader,
) -> Profile:
    """Determine which profile to use and return the fully resolved Profile.

    Priority: --profile flag > AutoUpdateConfig.active_profile > "default".

    Args:
        flag_value: Value from --profile CLI flag, or None if not passed
        loader: ProfileLoader to use for loading/resolving

    Returns:
        Fully resolved Profile
    """
    if flag_value:
        return loader.resolve_profile(flag_value)

    from shell_configs.bootstrap.config import load_auto_update_config

    auto_config = load_auto_update_config()
    if auto_config.active_profile:
        return loader.resolve_profile(auto_config.active_profile)

    return loader.resolve_profile("default")
