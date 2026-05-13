"""Component registry — the authoritative lists of managed components."""

from __future__ import annotations

from shell_configs.cli.components.completions import CompletionsComponent
from shell_configs.cli.components.configs import ConfigsComponent
from shell_configs.cli.components.extensions import ExtensionsComponent
from shell_configs.cli.components.gh_extensions import GhExtensionsComponent
from shell_configs.cli.components.packages import (
    OptionalPackagesComponent,
    RequiredPackagesComponent,
)
from shell_configs.cli.components.scripts import ScriptsComponent
from shell_configs.cli.components.signing import SigningComponent
from shell_configs.cli.context import Component

INSTALL_COMPONENTS: list[Component] = [
    RequiredPackagesComponent(),
    ConfigsComponent(),
    OptionalPackagesComponent(),
    SigningComponent(),
    ScriptsComponent(),
    ExtensionsComponent(),
    GhExtensionsComponent(),
]

STATUS_COMPONENTS: list[Component] = [
    ConfigsComponent(),
    CompletionsComponent(),
    OptionalPackagesComponent(),
    ExtensionsComponent(),
    ScriptsComponent(),
    SigningComponent(),
    GhExtensionsComponent(),
]

DIFF_COMPONENTS = INSTALL_COMPONENTS

# Only components with real uninstall() overrides; the other 5 inherit the base no-op.
UNINSTALL_COMPONENTS: list[Component] = [
    ConfigsComponent(),
    ScriptsComponent(),
]
