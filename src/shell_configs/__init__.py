"""Shell configuration management tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("shell-configs")
except PackageNotFoundError:
    __version__ = "dev"
