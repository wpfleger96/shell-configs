"""Regression tests for the managed `wt` shell helpers."""

import json
import os
import shlex
import subprocess

from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_SH = REPO_ROOT / "src" / "shell_configs" / "config" / "shared.sh"

FAKE_GIT_SCRIPT = """#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
state = json.loads(open(os.environ["TEST_GIT_STATE"]).read())
removals_path = os.environ.get("TEST_GIT_REMOVALS")


def branch_state(name):
    return state.get("branches", {}).get(name, {})


def write_removal(path):
    if removals_path:
        with open(removals_path, "a", encoding="utf-8") as f:
            f.write(path + "\\n")


if args[:3] == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
    print(state["git_common_dir"])
    sys.exit(0)

if args[:2] == ["rev-parse", "--git-dir"]:
    print(state["git_dir"])
    sys.exit(0)

if len(args) >= 2 and args[0] == "symbolic-ref" and args[1] == "refs/remotes/origin/HEAD":
    print(f'refs/remotes/origin/{state["default_branch"]}')
    sys.exit(0)

if len(args) >= 2 and args[0] == "show-ref" and args[1] == "--verify":
    ref = args[-1]
    if ref.startswith("refs/heads/"):
        sys.exit(0 if branch_state(ref.removeprefix("refs/heads/")).get("exists", False) else 1)
    if ref.startswith("refs/remotes/origin/"):
        sys.exit(0 if branch_state(ref.removeprefix("refs/remotes/origin/")).get("has_remote", False) else 1)
    sys.exit(1)

if args[:2] == ["rev-parse", f'origin/{state["default_branch"]}']:
    print(branch_state(state["default_branch"]).get("head", ""))
    sys.exit(0)

if len(args) >= 2 and args[0] == "rev-parse":
    ref = args[1]
    if ref.startswith("refs/heads/"):
        branch = ref.removeprefix("refs/heads/")
    else:
        branch = ref
    branch_info = branch_state(branch)
    if branch_info.get("exists", False):
        print(branch_info.get("head", ""))
        sys.exit(0)
    sys.exit(1)

if len(args) >= 3 and args[0] == "merge-base" and args[1] == "--is-ancestor":
    branch = args[2]
    sys.exit(0 if branch_state(branch).get("is_ancestor", False) else 1)

if len(args) >= 3 and args[0] == "merge-base":
    branch = args[1]
    branch_info = branch_state(branch)
    if branch_info.get("exists", False):
        print(branch_info.get("merge_base", branch_info.get("head", "")))
        sys.exit(0)
    sys.exit(1)

if len(args) >= 3 and args[0] == "cherry":
    branch = args[2]
    for idx in range(branch_state(branch).get("cherry_plus", 0)):
        print(f"+ deadbeef{idx}")
    sys.exit(0)

if len(args) >= 2 and args[0] == "fetch":
    sys.exit(0)

if args[:3] == ["worktree", "list", "--porcelain"]:
    for worktree in state["worktrees"]:
        print(f'worktree {worktree["path"]}')
        print(f'HEAD {worktree["head"]}')
        branch = worktree.get("branch")
        if branch:
            print(f"branch refs/heads/{branch}")
        if worktree.get("detached", False):
            print("detached")
        prunable = worktree.get("prunable")
        if prunable:
            print(f"prunable {prunable}")
        print()
    sys.exit(0)

if len(args) >= 3 and args[0] == "worktree" and args[1] == "remove":
    path = args[-1]
    blocked = set(state.get("blocked_removals", []))
    if path in blocked:
        print("fatal: worktree contains uncommitted changes", file=sys.stderr)
        sys.exit(1)
    write_removal(path)
    sys.exit(0)

print("unsupported git invocation:", " ".join(args), file=sys.stderr)
sys.exit(1)
"""


def _make_state(repo_root: Path) -> dict[str, Any]:
    return {
        "git_common_dir": str(repo_root / ".git"),
        "git_dir": str(repo_root / ".git"),
        "default_branch": "main",
        "branches": {
            "main": {
                "exists": True,
                "head": "a" * 40,
                "merge_base": "a" * 40,
                "has_remote": True,
                "is_ancestor": True,
                "cherry_plus": 0,
            }
        },
        "worktrees": [
            {
                "path": str(repo_root),
                "branch": "main",
                "head": "a" * 40,
            }
        ],
    }


def _run_wt_command(
    temp_dir: Path, script: str, state: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    repo_root = temp_dir / "repo"
    repo_root.mkdir(exist_ok=True)
    (repo_root / ".git").mkdir(exist_ok=True)

    fake_bin = temp_dir / "bin"
    fake_bin.mkdir(exist_ok=True)
    fake_git = fake_bin / "git"
    fake_git.write_text(FAKE_GIT_SCRIPT)
    fake_git.chmod(0o755)

    state_path = temp_dir / "git-state.json"
    state_path.write_text(json.dumps(state))
    removals_path = temp_dir / "git-removals.txt"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["TEST_GIT_STATE"] = str(state_path)
    env["TEST_GIT_REMOVALS"] = str(removals_path)

    command = (
        f"export PATH={shlex.quote(str(fake_bin))}:$PATH\n"
        f"source {shlex.quote(str(SHARED_SH))} >/dev/null 2>&1\n"
        f"{script}\n"
    )
    return subprocess.run(
        ["bash", "-c", command],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _read_removals(temp_dir: Path) -> list[str]:
    removals_path = temp_dir / "git-removals.txt"
    if not removals_path.exists():
        return []
    return removals_path.read_text().splitlines()


@pytest.mark.unit
class TestWorktreeShell:
    """Tests for `wt` shell command behavior."""

    def test_wt_list_shows_prunable_branch_name_for_external_worktree(self, temp_dir):
        repo_root = temp_dir / "repo"
        state = _make_state(repo_root)
        external_path = (
            repo_root / ".claude" / "worktrees" / "backport-ai-rules-improvements"
        )
        external_path.mkdir(parents=True)
        managed_path = repo_root / ".worktrees" / "feature-merged"
        managed_path.mkdir(parents=True)
        state["branches"]["feature-merged"] = {
            "exists": True,
            "head": "b" * 40,
            "merge_base": "b" * 40,
            "has_remote": True,
            "is_ancestor": True,
            "cherry_plus": 0,
        }
        state["worktrees"].extend(
            [
                {
                    "path": str(external_path),
                    "branch": "worktree-backport-ai-rules-improvements",
                    "head": "c" * 40,
                    "prunable": "gitdir file points to non-existent location",
                },
                {
                    "path": str(managed_path),
                    "branch": "feature-merged",
                    "head": "b" * 40,
                },
            ]
        )

        result = _run_wt_command(temp_dir, "_wt_ls", state)

        assert result.returncode == 0
        assert "  * main (main worktree)" in result.stdout
        assert (
            "  - worktree-backport-ai-rules-improvements"
            " [PRUNABLE: gitdir file points to non-existent location]"
        ) in result.stdout
        assert "  - prunable" not in result.stdout
        assert "  - feature-merged [MERGED]" in result.stdout

    def test_wt_prune_ignores_external_prunable_worktrees(self, temp_dir):
        repo_root = temp_dir / "repo"
        state = _make_state(repo_root)
        external_path = (
            repo_root / ".claude" / "worktrees" / "backport-ai-rules-improvements"
        )
        external_path.mkdir(parents=True)
        managed_path = repo_root / ".worktrees" / "feature-merged"
        managed_path.mkdir(parents=True)
        state["branches"]["feature-merged"] = {
            "exists": True,
            "head": "b" * 40,
            "merge_base": "b" * 40,
            "has_remote": True,
            "is_ancestor": True,
            "cherry_plus": 0,
        }
        state["worktrees"].extend(
            [
                {
                    "path": str(external_path),
                    "branch": "worktree-backport-ai-rules-improvements",
                    "head": "c" * 40,
                    "prunable": "gitdir file points to non-existent location",
                },
                {
                    "path": str(managed_path),
                    "branch": "feature-merged",
                    "head": "b" * 40,
                },
            ]
        )

        result = _run_wt_command(temp_dir, "_wt_prune", state)

        assert result.returncode == 0
        assert "Pruned merged worktree: feature-merged" in result.stdout
        assert "worktree-backport-ai-rules-improvements" not in result.stdout
        assert _read_removals(temp_dir) == [str(managed_path)]

    def test_wt_orphans_reports_all_deleted_branches(self, temp_dir):
        repo_root = temp_dir / "repo"
        state = _make_state(repo_root)
        external_path = (
            repo_root / ".claude" / "worktrees" / "backport-ai-rules-improvements"
        )
        external_path.mkdir(parents=True)
        managed_path = repo_root / ".worktrees" / "deleted-branch"
        managed_path.mkdir(parents=True)
        state["branches"]["deleted-branch"] = {
            "exists": False,
            "head": "d" * 40,
            "merge_base": "a" * 40,
            "has_remote": False,
            "is_ancestor": False,
            "cherry_plus": 1,
        }
        state["worktrees"].extend(
            [
                {
                    "path": str(external_path),
                    "branch": "worktree-backport-ai-rules-improvements",
                    "head": "c" * 40,
                    "prunable": "gitdir file points to non-existent location",
                },
                {
                    "path": str(managed_path),
                    "branch": "deleted-branch",
                    "head": "d" * 40,
                },
            ]
        )

        result = _run_wt_command(temp_dir, "_wt_orphans", state)

        assert result.returncode == 0
        assert "  - deleted-branch (branch deleted)" in result.stdout
        assert (
            "  - worktree-backport-ai-rules-improvements (branch deleted) [external]"
            in result.stdout
        )

    def test_wt_rm_removes_external_worktree(self, temp_dir):
        repo_root = temp_dir / "repo"
        state = _make_state(repo_root)
        external_path = (
            repo_root / ".claude" / "worktrees" / "backport-ai-rules-improvements"
        )
        external_path.mkdir(parents=True)
        state["branches"]["worktree-backport-ai-rules-improvements"] = {
            "exists": True,
            "head": "c" * 40,
            "merge_base": "a" * 40,
            "has_remote": True,
            "is_ancestor": False,
            "cherry_plus": 1,
        }
        state["worktrees"].append(
            {
                "path": str(external_path),
                "branch": "worktree-backport-ai-rules-improvements",
                "head": "c" * 40,
            }
        )

        result = _run_wt_command(
            temp_dir, "_wt_rm worktree-backport-ai-rules-improvements", state
        )

        assert result.returncode == 0
        assert (
            "Removed worktree for 'worktree-backport-ai-rules-improvements'"
            in result.stdout
        )

    def test_wt_cd_navigates_to_external_worktree(self, temp_dir):
        repo_root = temp_dir / "repo"
        state = _make_state(repo_root)
        external_path = (
            repo_root / ".claude" / "worktrees" / "backport-ai-rules-improvements"
        )
        external_path.mkdir(parents=True)
        state["branches"]["worktree-backport-ai-rules-improvements"] = {
            "exists": True,
            "head": "c" * 40,
            "merge_base": "a" * 40,
            "has_remote": True,
            "is_ancestor": False,
            "cherry_plus": 1,
        }
        state["worktrees"].append(
            {
                "path": str(external_path),
                "branch": "worktree-backport-ai-rules-improvements",
                "head": "c" * 40,
            }
        )

        result = _run_wt_command(
            temp_dir, "_wt_cd worktree-backport-ai-rules-improvements", state
        )

        assert result.returncode == 0
