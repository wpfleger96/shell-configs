"""Component registry — the authoritative lists of managed components."""

from __future__ import annotations

from shell_configs.cli.components.completions import CompletionsComponent
from shell_configs.cli.components.configs import ConfigsComponent
from shell_configs.cli.components.extensions import ExtensionsComponent
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
]

STATUS_COMPONENTS: list[Component] = [
    ConfigsComponent(),
    CompletionsComponent(),
    OptionalPackagesComponent(),
    ExtensionsComponent(),
    ScriptsComponent(),
    SigningComponent(),
]

COMPONENTS = INSTALL_COMPONENTS
