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
            encoding="utf-8",
            check=False,
            cwd=repo_root,
            env=env,
            timeout=timeout,
        )

    return _run


@pytest.fixture(scope="session")
def bundled_config_dir():
    """Path to the real config shipped inside the shell_configs package.

    This is what `configs install` (and the top-level `install`) use by
    default, so installing from it exercises the genuine bundled aliases,
    functions, git-prompt, etc. — not a synthetic stand-in.
    """
    import shell_configs

    return Path(shell_configs.__file__).parent / "config"


@pytest.fixture
def installed_home(run_cli, e2e_home):
    """Perform a real, hermetic configs+scripts install into the isolated HOME.

    Drives only `configs install` and `scripts install` (NOT the top-level
    `install`, which would invoke the package/language/gh/signing components and
    attempt real apt/brew/gh/network/sudo work). Returns (home_dir, env).
    """
    home_dir, env_overrides = e2e_home
    result = run_cli(["configs", "install", "--shells", "bash,zsh,git", "-y"])
    assert result.returncode == 0, f"configs install failed: {result.stderr}"
    scripts_result = run_cli(["scripts", "install", "-y"])
    assert scripts_result.returncode == 0, (
        f"scripts install failed: {scripts_result.stderr}"
    )
    return home_dir, env_overrides


@pytest.fixture
def run_shell(e2e_home):
    """Factory to run a script in a real bash/zsh with the isolated HOME.

    Loads only the installed rc (no system rc): bash via `--norc`, zsh via
    `-f` (NO_RCS); the script is expected to `source` the installed rc itself.
    Non-interactive to avoid TTY hangs.
    """
    _, env_overrides = e2e_home

    def _run(shell_name, script, timeout=15):
        env = {**os.environ, **env_overrides}
        if shell_name == "bash":
            argv = ["bash", "--norc", "-c", script]
        elif shell_name == "zsh":
            argv = ["zsh", "-f", "-c", script]
        else:
            raise ValueError(f"unsupported shell: {shell_name}")
        return subprocess.run(
            argv,
            capture_output=True,
            encoding="utf-8",
            check=False,
            env=env,
            timeout=timeout,
        )

    return _run


@pytest.fixture
def git_repo(e2e_home):
    """Create a real git repo (branch `main`, one commit) inside the isolated HOME.

    Signing is disabled and identity is set locally so the commit succeeds
    regardless of any managed ~/.gitconfig (the bundled config enables ssh
    signing, which would otherwise fail without a key/agent).
    """
    home_dir, env_overrides = e2e_home
    repo = home_dir / "repo"
    repo.mkdir()
    env = {
        **os.environ,
        **env_overrides,
        "GIT_CONFIG_GLOBAL": str(home_dir / ".gitconfig"),
    }

    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            encoding="utf-8",
            check=True,
            cwd=repo,
            env=env,
        )

    _git("init", "-q", "-b", "main")
    _git("config", "user.email", "e2e@example.com")
    _git("config", "user.name", "E2E Test")
    _git("config", "commit.gpgsign", "false")
    _git("commit", "-q", "--allow-empty", "-m", "init")
    return repo
