"""Manager for shell configuration sections."""

from .core import ConfigManager
from .types import (
    AdditionalFileEntry,
    AdditionalFileManifest,
    ManagedSection,
    OperationResult,
    get_default_additional_manifest_path,
)

__all__ = [
    "ConfigManager",
    "OperationResult",
    "ManagedSection",
    "AdditionalFileEntry",
    "AdditionalFileManifest",
    "get_default_additional_manifest_path",
]
