import os
import subprocess
import sys

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def guard_subprocess():
    """No-op override: E2E tests run real subprocesses."""
    yield


@pytest.fixture(autouse=True)
def mock_platform_for_tests():
    """No-op override: E2E tests use real platform detection."""
    yield


@pytest.fixture
def e2e_home(tmp_path):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    env_overrides = {
        "HOME": str(home_dir),
        "USERPROFILE": str(home_dir),
        "APPDATA": str(home_dir / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(home_dir / "AppData" / "Local"),
        "NO_COLOR": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PATH": os.environ.get("PATH", ""),
        "SHELL": "/bin/bash",
    }
    return home_dir, env_overrides


@pytest.fixture
def e2e_config_dir(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    bash_dir = config_dir / "bash"
    bash_dir.mkdir()
    (bash_dir / "bashrc").write_text("# E2E test bash config\nalias test='echo test'\n")

    zsh_dir = config_dir / "zsh"
    zsh_dir.mkdir()
    (zsh_dir / "zshrc").write_text("# E2E test zsh config\nalias test='echo test'\n")

    git_dir = config_dir / "git"
    git_dir.mkdir()

    (config_dir / "shared.gitconfig").write_text("[user]\n    name = E2E Test\n")
    (config_dir / "shared.sh").write_text("# Shared E2E config\n")

    profiles_dir = config_dir / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "default.yaml").write_text("name: default\ndescription: Default\n")

    return config_dir


@pytest.fixture
def run_cli(e2e_home):
    home_dir, env_overrides = e2e_home
    repo_root = Path(__file__).parents[2]
    src_path = repo_root / "src"

    def _run(args, extra_env=None, timeout=30):
        env = {**os.environ, **env_overrides}
        if extra_env:
            env.update(extra_env)
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(src_path) + os.pathsep + existing_pythonpath
            if existing_pythonpath
            else str(src_path)
        )
        return subprocess.run(
            [sys.executable, "-m", "shell_configs.cli", *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
            env=env,
            timeout=timeout,
        )

    return _run
