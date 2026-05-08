"""Profile loading and inheritance resolution."""

from pathlib import Path
from typing import Any

import yaml

from shell_configs.profiles.profile import (
    CircularInheritanceError,
    Profile,
    ProfileError,
    ProfileNotFoundError,
)
from shell_configs.shells.base import deep_merge as _deep_merge


class ProfileLoader:
    """Loads and resolves profile inheritance chains."""

    def __init__(self, config_dir: Path) -> None:
        """Initialize with the config directory (same root as ConfigReader uses).

        Args:
            config_dir: Path to the config/ directory containing profiles/
        """
        self._profiles_dir = config_dir / "profiles"

    def get_profile_path(self, name: str) -> Path | None:
        """Return the path to a profile YAML file, or None if it doesn't exist."""
        path = self._profiles_dir / f"{name}.yaml"
        return path if path.exists() else None

    def list_profiles(self) -> list[str]:
        """List all available profile names."""
        if not self._profiles_dir.exists():
            return ["default"]

        profiles = [p.stem for p in self._profiles_dir.glob("*.yaml")]

        if "default" not in profiles:
            profiles.append("default")

        return sorted(profiles)

    def load_profile(self, name: str) -> Profile:
        """Load a single profile YAML without resolving inheritance.

        Args:
            name: Profile name (without .yaml extension)

        Returns:
            Profile populated from YAML (extends chain NOT walked)

        Raises:
            ProfileNotFoundError: If the profile file does not exist
            ProfileError: If the YAML is malformed
        """
        profile_path = self._profiles_dir / f"{name}.yaml"

        if not profile_path.exists():
            if name == "default":
                return Profile(
                    name="default", description="Default profile (no overrides)"
                )
            available = self.list_profiles()
            raise ProfileNotFoundError(
                f"Profile '{name}' not found. Available: {', '.join(available)}"
            )

        try:
            with open(profile_path) as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ProfileError(f"Profile '{name}' has invalid YAML: {e}") from e

        return Profile(
            name=data.get("name", name),
            description=data.get("description", ""),
            extends=data.get("extends"),
            settings_overrides=data.get("settings_overrides", {}),
            shell_overrides=data.get("shell_overrides", {}),
            packages=data.get("packages", {}),
            extensions=data.get("extensions", {}),
        )

    def resolve_profile(self, name: str) -> Profile:
        """Walk the extends chain and merge all ancestors into a single Profile.

        Parent values are the base; child overrides on top. Detects cycles.

        Args:
            name: Profile name to resolve

        Returns:
            Fully merged Profile

        Raises:
            ProfileNotFoundError: If any profile in the chain is missing
            CircularInheritanceError: If the chain contains a cycle
            ProfileError: If any YAML in the chain is malformed
        """
        return self._resolve(name, visited=())

    def _resolve(self, name: str, visited: tuple[str, ...]) -> Profile:
        if name in visited:
            cycle = " -> ".join(visited) + f" -> {name}"
            raise CircularInheritanceError(
                f"Circular profile inheritance detected: {cycle}"
            )

        visited = (*visited, name)
        profile = self.load_profile(name)

        if not profile.extends:
            return profile

        parent = self._resolve(profile.extends, visited)
        return self._merge(parent, profile)

    def _merge(self, parent: Profile, child: Profile) -> Profile:
        """Merge parent into child; child wins on conflicts."""
        merged_settings = _deep_merge(
            parent.settings_overrides, child.settings_overrides
        )

        merged_shell: dict[str, str] = dict(parent.shell_overrides)
        for shell_name, content in child.shell_overrides.items():
            if shell_name in merged_shell:
                merged_shell[shell_name] = merged_shell[shell_name] + "\n" + content
            else:
                merged_shell[shell_name] = content

        parent_add = parent.packages.get("add", [])
        child_add = child.packages.get("add", [])
        parent_remove = parent.packages.get("remove", [])
        child_remove = child.packages.get("remove", [])

        merged_add = list(dict.fromkeys(parent_add + child_add))
        merged_remove = list(dict.fromkeys(parent_remove + child_remove))
        merged_add = [p for p in merged_add if p not in set(merged_remove)]

        merged_packages: dict[str, list[str]] = {}
        if merged_add:
            merged_packages["add"] = merged_add
        if merged_remove:
            merged_packages["remove"] = merged_remove

        merged_extensions: dict[str, dict[str, list[str]]] = {}
        all_shell_names = set(parent.extensions) | set(child.extensions)
        for shell_name in all_shell_names:
            p_ext = parent.extensions.get(shell_name, {})
            c_ext = child.extensions.get(shell_name, {})

            p_add = [e.lower() for e in p_ext.get("add", [])]
            c_add = [e.lower() for e in c_ext.get("add", [])]
            p_rm = [e.lower() for e in p_ext.get("remove", [])]
            c_rm = [e.lower() for e in c_ext.get("remove", [])]

            ext_add = list(dict.fromkeys(p_add + c_add))
            ext_rm = list(dict.fromkeys(p_rm + c_rm))
            ext_add = [e for e in ext_add if e not in set(ext_rm)]

            shell_ext: dict[str, list[str]] = {}
            if ext_add:
                shell_ext["add"] = ext_add
            if ext_rm:
                shell_ext["remove"] = ext_rm
            if shell_ext:
                merged_extensions[shell_name] = shell_ext

        return Profile(
            name=child.name,
            description=child.description,
            extends=child.extends,
            settings_overrides=merged_settings,
            shell_overrides=merged_shell,
            packages=merged_packages,
            extensions=merged_extensions,
        )
