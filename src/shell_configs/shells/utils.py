"""Shared utilities for shell configuration handlers."""

import subprocess


def get_windows_username() -> str:
    """Get Windows username when running in WSL.

    Returns:
        Windows username or empty string if unable to determine
    """
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERNAME%"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        username = result.stdout.strip()
        if result.returncode == 0 and username:
            return username
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["whoami.exe"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        username = result.stdout.strip().split("\\")[-1]
        if result.returncode == 0 and username:
            return username
    except Exception:
        pass

    return ""
