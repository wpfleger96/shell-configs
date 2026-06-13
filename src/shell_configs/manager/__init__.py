"""Manager for shell configuration sections."""

# Re-exported so tests can monkeypatch ``shell_configs.manager.subprocess.run``
# (subprocess is a singleton module; this binds the same object core.py uses).
import subprocess  # noqa: F401

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
