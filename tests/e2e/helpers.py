import re
import shutil
import sys


def is_windows() -> bool:
    return sys.platform == "win32"


def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def shell_available(name: str) -> bool:
    """Return True if the named shell binary is on PATH."""
    return shutil.which(name) is not None


# The literal sentinel shell-configs writes around every managed config block.
# Asserting on this stable token (rather than exact decoration) keeps the E2E
# suite resilient to cosmetic refactors.
MANAGED_MARKER = "shell-configs Managed Config"


def has_managed_marker(text: str) -> bool:
    """True if the given file content contains a shell-configs managed section."""
    return MANAGED_MARKER in text
