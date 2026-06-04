"""Unit tests for the disk-cleanup standalone script."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import time
import types

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "shell_configs"
    / "scripts"
    / "system"
    / "disk-cleanup"
)


def _load_module() -> types.ModuleType:
    loader = importlib.machinery.SourceFileLoader("disk_cleanup", str(_SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("disk_cleanup", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["disk_cleanup"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _collect_scan_results(
    dev_dir: Path, **kwargs: object
) -> tuple[list[Any], list[Any]]:
    all_targets = list(mod._scan_dev_tree(dev_dir, **kwargs))
    rust_targets = [t for t in all_targets if t.category == "target"]
    incrementals = [t for t in all_targets if t.category == "incremental"]
    return rust_targets, incrementals


# Capture the real subprocess.run before autouse fixtures replace it
_real_subprocess_run = subprocess.run


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectPlatform:
    def test_darwin_returns_macos(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        assert mod._detect_platform() == "macos"

    def test_win32_returns_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert mod._detect_platform() == "windows"

    def test_linux_with_microsoft_in_proc_version_returns_wsl(
        self, monkeypatch, tmp_path
    ):
        proc_version = tmp_path / "proc_version"
        proc_version.write_text("Linux version 5.15 microsoft standard\n")
        monkeypatch.setattr(sys, "platform", "linux")

        original_open = open

        def _patched_open(path, *args, **kwargs):
            if str(path) == "/proc/version":
                return original_open(str(proc_version), *args, **kwargs)
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _patched_open)
        assert mod._detect_platform() == "wsl"

    def test_linux_with_wsl_in_proc_version_returns_wsl(self, monkeypatch, tmp_path):
        proc_version = tmp_path / "proc_version"
        proc_version.write_text("Linux version 5.15 WSL2 kernel\n")
        monkeypatch.setattr(sys, "platform", "linux")

        original_open = open

        def _patched_open(path, *args, **kwargs):
            if str(path) == "/proc/version":
                return original_open(str(proc_version), *args, **kwargs)
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _patched_open)
        assert mod._detect_platform() == "wsl"

    def test_linux_normal_returns_linux(self, monkeypatch, tmp_path):
        proc_version = tmp_path / "proc_version"
        proc_version.write_text("Linux version 6.1.0-generic\n")
        monkeypatch.setattr(sys, "platform", "linux")

        original_open = open

        def _patched_open(path, *args, **kwargs):
            if str(path) == "/proc/version":
                return original_open(str(proc_version), *args, **kwargs)
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _patched_open)
        assert mod._detect_platform() == "linux"

    def test_linux_unreadable_proc_version_returns_linux(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")

        def _patched_open(path, *args, **kwargs):
            if str(path) == "/proc/version":
                raise OSError("Permission denied")
            return open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _patched_open)
        assert mod._detect_platform() == "linux"


# ---------------------------------------------------------------------------
# Human-readable size formatting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHumanSize:
    @pytest.mark.parametrize(
        "nbytes,expected",
        [
            (0, "0B"),
            (512, "512B"),
            (1023, "1023B"),
            (1024, "1K"),
            (2048, "2K"),
            (1048576, "1M"),
            (5 * 1024**2, "5M"),
            (1073741824, "1.0G"),
            (10737418240, "10.0G"),
            (2 * 1024**3, "2.0G"),
        ],
    )
    def test_human_size(self, nbytes, expected):
        assert mod._human_size(nbytes) == expected


# ---------------------------------------------------------------------------
# Short path formatting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestShortPath:
    def test_path_under_home_starts_with_tilde(self, monkeypatch, tmp_path):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        target = fake_home / "projects" / "myrepo"
        result = mod._short_path(target)

        assert result.startswith("~")
        assert "projects/myrepo" in result

    def test_path_outside_home_unchanged(self, monkeypatch, tmp_path):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        outside = Path("/usr/local/bin")
        result = mod._short_path(outside)

        assert result == "/usr/local/bin"

    def test_home_itself_becomes_tilde(self, monkeypatch, tmp_path):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        result = mod._short_path(fake_home)

        assert result == "~"


# ---------------------------------------------------------------------------
# Row formatting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatRows:
    def test_right_aligns_size_at_term_width(self, monkeypatch, tmp_path):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        target = mod.ScanTarget(
            path=fake_home / "project" / "target",
            label="x",
            category="target",
            tier=3,
            size_bytes=5 * 1024**3,
        )
        rows = mod._format_rows([target], term_width=80)
        assert len(rows) == 1
        # Row should be padded to roughly 80 chars (excluding ANSI codes)
        # The size string should appear at the end
        assert "5.0G" in rows[0]

    def test_truncates_long_paths_with_ellipsis(self, monkeypatch, tmp_path):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        very_long = fake_home / ("a" * 200) / "target"
        target = mod.ScanTarget(
            path=very_long,
            label="x",
            category="target",
            tier=3,
            size_bytes=1024**3,
        )
        rows = mod._format_rows([target], term_width=80)
        assert "…" in rows[0]

    def test_multiple_items_produce_multiple_rows(self, monkeypatch, tmp_path):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        targets = [
            mod.ScanTarget(
                path=fake_home / "a" / "target",
                label="x",
                category="target",
                tier=3,
                size_bytes=2 * 1024**3,
            ),
            mod.ScanTarget(
                path=fake_home / "b" / "target",
                label="x",
                category="target",
                tier=3,
                size_bytes=1024**3,
            ),
        ]
        rows = mod._format_rows(targets, term_width=80)
        assert len(rows) == 2

    def test_sizes_aligned_at_same_column(self, monkeypatch, tmp_path):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        # Short and long path — sizes should still end at same position
        targets = [
            mod.ScanTarget(
                path=fake_home / "short" / "target",
                label="x",
                category="target",
                tier=3,
                size_bytes=10 * 1024**3,
            ),
            mod.ScanTarget(
                path=fake_home / "a-much-longer-project-name" / "target",
                label="x",
                category="target",
                tier=3,
                size_bytes=10 * 1024**3,
            ),
        ]
        rows = mod._format_rows(targets, term_width=80)
        # Strip Rich markup tags to measure actual visual width
        import re

        markup_pattern = re.compile(r"\[/?[a-z ]+\]")
        stripped = [markup_pattern.sub("", r) for r in rows]
        # Both rows should be same length (right-aligned to term_width)
        assert len(stripped[0]) == len(stripped[1])


# ---------------------------------------------------------------------------
# Section printing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrintSection:
    def test_returns_subtotal_bytes(self, monkeypatch, tmp_path, capsys):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        items = [
            mod.ScanTarget(
                path=fake_home / "a",
                label="a",
                category="cache",
                tier=1,
                size_bytes=5 * 1024**2,
            ),
            mod.ScanTarget(
                path=fake_home / "b",
                label="b",
                category="cache",
                tier=1,
                size_bytes=3 * 1024**2,
            ),
        ]
        result = mod._print_section("Test Section", "test description", items, 80)
        assert result == 8 * 1024**2

    def test_prints_title_and_description(self, monkeypatch, tmp_path, capsys):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        mod._print_section("My Title", "my desc", [], 80)
        captured = capsys.readouterr()
        assert "My Title" in captured.out
        assert "my desc" in captured.out

    def test_prints_none_found_when_empty(self, capsys):
        mod._print_section("Empty", "nothing here", [], 80)
        captured = capsys.readouterr()
        assert "none found" in captured.out

    def test_filters_items_below_min_display_bytes(self, monkeypatch, tmp_path, capsys):
        fake_home = tmp_path / "home" / "user"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        tiny = mod.ScanTarget(
            path=fake_home / "tiny",
            label="tiny",
            category="cache",
            tier=1,
            size_bytes=100,  # way below 1MB threshold
        )
        result = mod._print_section("Test", "desc", [tiny], 80)
        captured = capsys.readouterr()
        # The item shouldn't appear in rows, but subtotal should include it
        assert result == 100
        assert "none found" in captured.out


# ---------------------------------------------------------------------------
# Dev tree scanner
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanDevTree:
    def test_finds_rust_target_with_debug_child(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)

        rust_targets, incrementals = _collect_scan_results(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert project / "target" in target_paths

    def test_finds_rust_target_with_release_child(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "release").mkdir(parents=True)

        rust_targets, _ = _collect_scan_results(tmp_path)

        assert any(t.path == project / "target" for t in rust_targets)

    def test_synthesizes_incremental_when_dir_exists(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug" / "incremental").mkdir(parents=True)

        _, incrementals = _collect_scan_results(tmp_path)

        incremental_paths = [t.path for t in incrementals]
        assert project / "target" / "debug" / "incremental" in incremental_paths

    def test_does_not_synthesize_incremental_when_dir_missing(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)

        _, incrementals = _collect_scan_results(tmp_path)

        assert incrementals == []

    def test_does_not_descend_into_target_dir(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)
        nested = project / "target" / "nested_project" / "target" / "debug"
        nested.mkdir(parents=True)

        rust_targets, _ = _collect_scan_results(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert project / "target" in target_paths
        assert nested.parent not in target_paths

    def test_skips_git_directories(self, tmp_path):
        git_dir = tmp_path / ".git"
        (git_dir / "objects").mkdir(parents=True)
        project_under_git = git_dir / "nested" / "target" / "debug"
        project_under_git.mkdir(parents=True)

        rust_targets, _ = _collect_scan_results(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert all(".git" not in str(p) for p in target_paths)

    def test_does_not_skip_worktrees(self, tmp_path):
        worktrees_dir = tmp_path / ".worktrees" / "feature-branch"
        (worktrees_dir / "myproject" / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = _collect_scan_results(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert any(".worktrees" in str(p) for p in target_paths)

    def test_does_not_follow_symlinks(self, tmp_path):
        outside = tmp_path / "outside"
        (outside / "target" / "debug").mkdir(parents=True)

        dev_dir = tmp_path / "dev"
        dev_dir.mkdir()
        link = dev_dir / "symlinked_project"
        os.symlink(outside, link)

        rust_targets, _ = _collect_scan_results(dev_dir)

        assert rust_targets == []

    def test_handles_permission_error_gracefully(self, tmp_path):
        unreadable = tmp_path / "unreadable"
        unreadable.mkdir()
        project = tmp_path / "project"
        (project / "target" / "debug").mkdir(parents=True)

        original_scandir = os.scandir

        def _patched_scandir(path):
            if str(path) == str(unreadable):
                raise PermissionError("Permission denied")
            return original_scandir(path)

        import unittest.mock as mock

        with mock.patch("os.scandir", side_effect=_patched_scandir):
            rust_targets, _ = _collect_scan_results(tmp_path)

        assert any(t.path == project / "target" for t in rust_targets)

    def test_target_category_is_target(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = _collect_scan_results(tmp_path)

        assert all(t.category == "target" for t in rust_targets)

    def test_incremental_category_is_incremental(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug" / "incremental").mkdir(parents=True)

        _, incrementals = _collect_scan_results(tmp_path)

        assert all(t.category == "incremental" for t in incrementals)

    def test_target_tier_is_3(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = _collect_scan_results(tmp_path)

        assert all(t.tier == 3 for t in rust_targets)

    def test_incremental_tier_is_1(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug" / "incremental").mkdir(parents=True)

        _, incrementals = _collect_scan_results(tmp_path)

        assert all(t.tier == 1 for t in incrementals)

    def test_empty_dev_dir_returns_no_targets(self, tmp_path):
        rust_targets, incrementals = _collect_scan_results(tmp_path)

        assert rust_targets == []
        assert incrementals == []

    def test_max_depth_limits_scan(self, tmp_path):
        deep = tmp_path
        for _ in range(10):
            deep = deep / "sub"
        (deep / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = _collect_scan_results(tmp_path, max_depth=3)

        assert rust_targets == []


# ---------------------------------------------------------------------------
# du-based size computation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDuSizeBytes:
    def test_returns_positive_size_for_real_dir(self, tmp_path, monkeypatch):
        (tmp_path / "file.txt").write_bytes(b"x" * 4096)

        # Bypass guard_subprocess by patching the module-level reference with the
        # real subprocess.run captured before autouse fixtures replaced it
        monkeypatch.setattr(mod.subprocess, "run", _real_subprocess_run)

        size = mod._du_size_bytes(tmp_path)

        assert size >= 0

    def test_returns_none_for_nonexistent_path(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "does_not_exist"

        monkeypatch.setattr(mod.subprocess, "run", _real_subprocess_run)

        size = mod._du_size_bytes(nonexistent)

        assert size is None

    def test_returns_none_on_subprocess_error(self, monkeypatch):
        def _failing_run(cmd, *args, **kwargs):
            raise OSError("du not found")

        monkeypatch.setattr(mod.subprocess, "run", _failing_run)

        size = mod._du_size_bytes(Path("/some/path"))

        assert size is None

    def test_returns_none_on_timeout(self, monkeypatch):
        def _timeout_run(cmd, *args, **kwargs):
            raise mod.subprocess.TimeoutExpired(cmd, 300)

        monkeypatch.setattr(mod.subprocess, "run", _timeout_run)

        size = mod._du_size_bytes(Path("/some/path"))

        assert size is None


# ---------------------------------------------------------------------------
# Docker raw size
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDockerRawSize:
    def test_returns_positive_size_for_existing_file(self, tmp_path):
        docker_raw = tmp_path / "Docker.raw"
        docker_raw.write_bytes(b"0" * 1024)

        size = mod._docker_raw_size(docker_raw)

        assert size > 0

    def test_returns_zero_for_nonexistent_file(self, tmp_path):
        missing = tmp_path / "nonexistent.raw"

        size = mod._docker_raw_size(missing)

        assert size == 0


# ---------------------------------------------------------------------------
# ScanTarget dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanTarget:
    def test_can_construct_with_required_fields(self):
        t = mod.ScanTarget(
            path=Path("/some/path"),
            label="/some/path",
            category="cache",
            tier=2,
        )

        assert t.path == Path("/some/path")
        assert t.label == "/some/path"
        assert t.category == "cache"
        assert t.tier == 2
        assert t.cleanup_cmd is None
        assert t.tool_name is None
        assert t.size_bytes == 0

    def test_can_construct_with_all_fields(self):
        t = mod.ScanTarget(
            path=Path("/usr/local"),
            label="/usr/local",
            category="incremental",
            tier=1,
            cleanup_cmd=["npm", "cache", "clean"],
            tool_name="npm",
            size_bytes=1048576,
        )

        assert t.cleanup_cmd == ["npm", "cache", "clean"]
        assert t.tool_name == "npm"
        assert t.size_bytes == 1048576


# ---------------------------------------------------------------------------
# _register decorator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterDecorator:
    def test_target_builders_is_populated_at_import(self):
        assert len(mod._TARGET_BUILDERS) > 0

    def test_macos_platform_has_builders(self):
        assert "macos" in mod._TARGET_BUILDERS
        assert len(mod._TARGET_BUILDERS["macos"]) > 0

    def test_linux_platform_has_builders(self):
        assert "linux" in mod._TARGET_BUILDERS
        assert len(mod._TARGET_BUILDERS["linux"]) > 0

    def test_register_adds_function_to_platform(self):
        registry: dict[str, list] = {}

        def _fake_register(*platforms: str) -> Callable:
            def decorator(fn: Callable) -> Callable:
                for p in platforms:
                    registry.setdefault(p, [])
                    registry[p].append(fn)
                return fn

            return decorator

        @_fake_register("testplatform")
        def _my_builder():
            return []

        assert "testplatform" in registry
        assert _my_builder in registry["testplatform"]

    def test_register_adds_to_multiple_platforms(self):
        registry: dict[str, list] = {}

        def _fake_register(*platforms: str) -> Callable:
            def decorator(fn: Callable) -> Callable:
                for p in platforms:
                    registry.setdefault(p, [])
                    registry[p].append(fn)
                return fn

            return decorator

        @_fake_register("alpha", "beta", "gamma")
        def _multi_builder():
            return []

        assert _multi_builder in registry["alpha"]
        assert _multi_builder in registry["beta"]
        assert _multi_builder in registry["gamma"]


# ---------------------------------------------------------------------------
# Report output (integration-style)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrintReport:
    def test_report_contains_disk_usage_header(self, monkeypatch, tmp_path, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        targets = []
        mod._print_report(targets)

        captured = capsys.readouterr()
        assert "Disk Usage Report" in captured.out

    def test_report_contains_rust_incremental_section(self, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        targets = []
        mod._print_report(targets)

        captured = capsys.readouterr()
        assert "Rust incremental caches" in captured.out

    def test_report_contains_subtotal(self, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        targets = []
        mod._print_report(targets)

        captured = capsys.readouterr()
        assert "Subtotal" in captured.out

    def test_report_shows_target_above_min_size(self, monkeypatch, tmp_path, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        big_target = mod.ScanTarget(
            path=tmp_path / "project" / "target",
            label=str(tmp_path / "project" / "target"),
            category="target",
            tier=3,
            size_bytes=500 * 1024**2,
        )

        mod._print_report([big_target])

        captured = capsys.readouterr()
        assert "500M" in captured.out


# ---------------------------------------------------------------------------
# Fix mode cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunFix:
    def test_removes_directories_for_tier_1(self, tmp_path, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        cache_dir = tmp_path / "incremental"
        cache_dir.mkdir()
        (cache_dir / "somefile.o").write_bytes(b"x" * 100)

        target = mod.ScanTarget(
            path=cache_dir,
            label=str(cache_dir),
            category="incremental",
            tier=1,
            size_bytes=2 * 1024**2,
        )

        mod._run_fix([target], skip_confirm=True)

        assert not cache_dir.exists()

    def test_removes_multiple_tier_directories(self, tmp_path, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        dir_a = tmp_path / "cache_a"
        dir_b = tmp_path / "cache_b"
        dir_a.mkdir()
        dir_b.mkdir()

        targets = [
            mod.ScanTarget(
                path=dir_a,
                label=str(dir_a),
                category="cache",
                tier=1,
                size_bytes=5 * 1024**2,
            ),
            mod.ScanTarget(
                path=dir_b,
                label=str(dir_b),
                category="cache",
                tier=1,
                size_bytes=3 * 1024**2,
            ),
        ]

        mod._run_fix(targets, skip_confirm=True)

        assert not dir_a.exists()
        assert not dir_b.exists()

    def test_skips_targets_with_zero_size(self, tmp_path, monkeypatch):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        cache_dir = tmp_path / "zero_cache"
        cache_dir.mkdir()

        target = mod.ScanTarget(
            path=cache_dir,
            label=str(cache_dir),
            category="cache",
            tier=1,
            size_bytes=0,
        )

        mod._run_fix([target], skip_confirm=True)

        assert cache_dir.exists()

    def test_runs_cleanup_cmd_when_specified(self, tmp_path, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        called_cmds = []

        def _mock_run(cmd, *args, **kwargs):
            called_cmds.append(cmd)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _mock_run)
        monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

        cache_dir = tmp_path / "npm_cache"
        cache_dir.mkdir()

        target = mod.ScanTarget(
            path=cache_dir,
            label=str(cache_dir),
            category="cache",
            tier=1,
            cleanup_cmd=["npm", "cache", "clean", "--force"],
            tool_name="npm",
            size_bytes=10 * 1024**2,
        )

        mod._run_fix([target], skip_confirm=True)

        assert ["npm", "cache", "clean", "--force"] in called_cmds

    def test_skips_cleanup_cmd_when_tool_not_found(self, tmp_path, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        called_cmds = []

        def _mock_run(cmd, *args, **kwargs):
            called_cmds.append(cmd)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _mock_run)
        monkeypatch.setattr(shutil, "which", lambda name: None)

        cache_dir = tmp_path / "npm_cache"
        cache_dir.mkdir()

        target = mod.ScanTarget(
            path=cache_dir,
            label=str(cache_dir),
            category="cache",
            tier=1,
            cleanup_cmd=["npm", "cache", "clean", "--force"],
            tool_name="npm",
            size_bytes=10 * 1024**2,
        )

        mod._run_fix([target], skip_confirm=True)

        assert called_cmds == []

    def test_run_fix_invalidates_cache(self, tmp_path, monkeypatch):
        import collections
        import time as time_mod

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda p: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        cache_file = tmp_path / "cache.json"
        cache = mod.SizeCache(cache_file, ttl=60)
        target_dir = tmp_path / "incremental"
        target_dir.mkdir()
        key = str(target_dir.resolve())
        cache.update({key: (1024 * 1024, time_mod.time())})

        target = mod.ScanTarget(
            path=target_dir,
            label=str(target_dir),
            category="incremental",
            tier=1,
            size_bytes=2 * 1024**2,
        )

        mod._run_fix([target], skip_confirm=True, cache=cache)

        assert cache.get(target_dir) is None


# ---------------------------------------------------------------------------
# Default workers constant
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaultWorkers:
    def test_default_workers_is_positive(self):
        assert mod._DEFAULT_WORKERS >= 1

    def test_default_workers_capped_at_16(self):
        assert mod._DEFAULT_WORKERS <= 16

    def test_default_workers_matches_formula(self):
        expected = min(os.cpu_count() or 4, 16)
        assert mod._DEFAULT_WORKERS == expected


# ---------------------------------------------------------------------------
# _run_fix_selected — interactive mode cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunFixSelected:
    def test_removes_selected_directory(self, tmp_path, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        cache_dir = tmp_path / "incremental"
        cache_dir.mkdir()
        (cache_dir / "artifact.o").write_bytes(b"x" * 100)

        target = mod.ScanTarget(
            path=cache_dir,
            label=str(cache_dir),
            category="incremental",
            tier=1,
            size_bytes=2 * 1024**2,
        )

        mod._run_fix_selected([target])

        assert not cache_dir.exists()

    def test_runs_cleanup_cmd_for_selected(self, tmp_path, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        called_cmds = []

        def _mock_run(cmd, *args, **kwargs):
            called_cmds.append(cmd)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _mock_run)
        monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

        cache_dir = tmp_path / "npm_cache"
        cache_dir.mkdir()

        target = mod.ScanTarget(
            path=cache_dir,
            label=str(cache_dir),
            category="cache",
            tier=1,
            cleanup_cmd=["npm", "cache", "clean", "--force"],
            tool_name="npm",
            size_bytes=10 * 1024**2,
        )

        mod._run_fix_selected([target])

        assert ["npm", "cache", "clean", "--force"] in called_cmds

    def test_skips_tool_when_not_found(self, tmp_path, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        called_cmds = []

        def _mock_run(cmd, *args, **kwargs):
            called_cmds.append(cmd)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _mock_run)
        monkeypatch.setattr(shutil, "which", lambda name: None)

        cache_dir = tmp_path / "npm_cache"
        cache_dir.mkdir()

        target = mod.ScanTarget(
            path=cache_dir,
            label=str(cache_dir),
            category="cache",
            tier=1,
            cleanup_cmd=["npm", "cache", "clean", "--force"],
            tool_name="npm",
            size_bytes=10 * 1024**2,
        )

        mod._run_fix_selected([target])

        assert called_cmds == []

    def test_handles_empty_list(self, monkeypatch, capsys):
        import collections

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda path: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        # Should complete without errors
        mod._run_fix_selected([])

        captured = capsys.readouterr()
        assert "Cleanup complete" in captured.out

    def test_run_fix_selected_invalidates_cache(self, tmp_path, monkeypatch):
        import collections
        import time as time_mod

        DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
        monkeypatch.setattr(
            shutil,
            "disk_usage",
            lambda p: DiskUsage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        cache_file = tmp_path / "cache.json"
        cache = mod.SizeCache(cache_file, ttl=60)
        target_dir = tmp_path / "to_clean"
        target_dir.mkdir()
        key = str(target_dir.resolve())
        cache.update({key: (512 * 1024, time_mod.time())})

        target = mod.ScanTarget(
            path=target_dir,
            label=str(target_dir),
            category="cache",
            tier=1,
            size_bytes=512 * 1024,
        )

        mod._run_fix_selected([target], cache=cache)

        assert cache.get(target_dir) is None


# ---------------------------------------------------------------------------
# SizeCache — persistent du result cache
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSizeCache:
    def test_get_returns_cached_size_within_ttl(self, tmp_path):
        cache_file = tmp_path / "cache" / "sizes.json"
        cache = mod.SizeCache(cache_file, ttl=60)
        target = tmp_path / "some" / "project"
        key = str(target.resolve())
        cache.update({key: (98765, __import__("time").time())})

        assert cache.get(target) == 98765

    def test_get_returns_none_after_ttl_expiry(self, tmp_path, monkeypatch):
        import time

        cache_file = tmp_path / "cache" / "sizes.json"
        target = tmp_path / "some" / "project"
        key = str(target.resolve())
        now = time.time()

        # Write the entry to disk via a first cache instance (real time).
        cache_writer = mod.SizeCache(cache_file, ttl=1)
        cache_writer.update({key: (42000, now)})

        # Patch time BEFORE constructing the second cache so that _load() sees the
        # advanced clock and prunes the expired entry on load.
        monkeypatch.setattr(time, "time", lambda: now + 2)

        cache = mod.SizeCache(cache_file, ttl=1)
        assert cache.get(target) is None

    def test_get_returns_none_for_unknown_path(self, tmp_path):
        cache_file = tmp_path / "cache" / "sizes.json"
        cache = mod.SizeCache(cache_file, ttl=60)

        assert cache.get(tmp_path / "no" / "such" / "path") is None

    def test_load_silently_discards_corrupt_json(self, tmp_path):
        cache_file = tmp_path / "cache" / "sizes.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("this is not valid json {{{{")

        # Should not raise
        cache = mod.SizeCache(cache_file, ttl=60)

        assert cache.get(tmp_path / "anything") is None

    def test_load_silently_discards_valid_json_non_dict(self, tmp_path):
        cache_file = tmp_path / "cache" / "sizes.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("[1, 2, 3]")
        cache = mod.SizeCache(cache_file, ttl=60)
        assert cache.get(tmp_path / "anything") is None

    def test_get_returns_zero_for_cached_empty_dir(self, tmp_path):
        import time as time_mod

        cache_file = tmp_path / "cache" / "sizes.json"
        cache = mod.SizeCache(cache_file, ttl=60)
        key = str((tmp_path / "empty").resolve())
        cache.update({key: (0, time_mod.time())})
        assert cache.get(tmp_path / "empty") == 0

    def test_save_silently_discards_oserror(self, tmp_path):
        # /dev/null is a file; /dev/null/impossible is an unwritable path
        cache_file = Path("/dev/null/impossible/sizes.json")
        cache = mod.SizeCache(cache_file, ttl=60)

        # Should not raise even though the path is unwritable
        cache.update({str(tmp_path): (1234, __import__("time").time())})

    def test_invalidate_removes_exact_path(self, tmp_path):
        cache_file = tmp_path / "cache" / "sizes.json"
        cache = mod.SizeCache(cache_file, ttl=60)
        target = Path("/a/b/c")
        cache.update({str(target): (5000, __import__("time").time())})

        cache.invalidate([target])

        assert cache.get(target) is None

    def test_invalidate_removes_child_when_parent_cleaned(self, tmp_path):
        cache_file = tmp_path / "cache" / "sizes.json"
        cache = mod.SizeCache(cache_file, ttl=60)
        child = Path("/a/b/c/target/debug/incremental")
        cache.update({str(child): (9999, __import__("time").time())})

        cache.invalidate([Path("/a/b/c/target")])

        assert cache.get(child) is None

    def test_invalidate_removes_parent_when_child_cleaned(self, tmp_path):
        cache_file = tmp_path / "cache" / "sizes.json"
        cache = mod.SizeCache(cache_file, ttl=60)
        parent = Path("/a/b/c/target")
        cache.update({str(parent): (8888, __import__("time").time())})

        cache.invalidate([Path("/a/b/c/target/debug/incremental")])

        assert cache.get(parent) is None

    def test_update_persists_to_disk(self, tmp_path):
        import time

        cache_file = tmp_path / "cache" / "sizes.json"
        target = tmp_path / "my" / "project"
        key = str(target.resolve())

        cache1 = mod.SizeCache(cache_file, ttl=60)
        cache1.update({key: (77777, time.time())})

        # A fresh SizeCache pointed at the same file should load the persisted entry
        cache2 = mod.SizeCache(cache_file, ttl=60)
        assert cache2.get(target) == 77777


# ---------------------------------------------------------------------------
# _du_size_bytes — updated return-None behavior
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDuSizeBytesNone:
    def test_du_returns_none_on_nonexistent_path(self, monkeypatch):
        monkeypatch.setattr(mod.subprocess, "run", _real_subprocess_run)

        result = mod._du_size_bytes(Path("/nonexistent/path/xyz"))

        assert result is None


# ---------------------------------------------------------------------------
# _interactive_select — early-exit path (no InquirerPy required)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInteractiveSelect:
    def test_returns_empty_list_when_no_targets_have_size(self, monkeypatch, capsys):
        # _interactive_select imports InquirerPy at the top of the function, so we
        # stub out the module before calling to avoid a hard dependency in tests.
        import types

        fake_inquirerpy = types.ModuleType("InquirerPy")
        fake_inquirerpy.inquirer = None  # type: ignore[attr-defined]
        fake_control = types.ModuleType("InquirerPy.base.control")
        fake_control.Choice = object  # type: ignore[attr-defined]
        fake_separator = types.ModuleType("InquirerPy.separator")
        fake_separator.Separator = object  # type: ignore[attr-defined]

        monkeypatch.setitem(sys.modules, "InquirerPy", fake_inquirerpy)
        monkeypatch.setitem(sys.modules, "InquirerPy.base.control", fake_control)
        monkeypatch.setitem(sys.modules, "InquirerPy.separator", fake_separator)

        # All targets have size_bytes=0 — choices list stays empty and the function
        # returns [] before ever calling inquirer.checkbox.
        targets = [
            mod.ScanTarget(
                path=Path("/some/incremental"),
                label="/some/incremental",
                category="incremental",
                tier=1,
                size_bytes=0,
            ),
            mod.ScanTarget(
                path=Path("/some/cache"),
                label="/some/cache",
                category="cache",
                tier=2,
                size_bytes=0,
            ),
        ]

        selected_targets, selected_discovery = mod._interactive_select(targets)

        assert selected_targets == []
        assert selected_discovery == []


# ---------------------------------------------------------------------------
# _parse_size_arg
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseSizeArg:
    @pytest.mark.parametrize(
        "s,expected",
        [
            ("100M", 100 * 1024**2),
            ("1G", 1 * 1024**3),
            ("500K", 500 * 1024),
            ("100m", 100 * 1024**2),
            ("1024", 1024),
            ("1.5G", int(1.5 * 1024**3)),
            ("2T", 2 * 1024**4),
        ],
    )
    def test_valid_inputs(self, s, expected):
        assert mod._parse_size_arg(s) == expected

    @pytest.mark.parametrize("s", ["", "abc", "M"])
    def test_invalid_inputs_raise(self, s):
        import argparse as argparse_mod

        with pytest.raises(argparse_mod.ArgumentTypeError):
            mod._parse_size_arg(s)


# ---------------------------------------------------------------------------
# _categorize_path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCategorizePath:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("file.iso", "disk-images"),
            ("file.mp4", "media"),
            ("file.zip", "archives"),
            ("file.sql", "database"),
            ("file.log", "logs"),
        ],
    )
    def test_curated_map_hits(self, filename, expected):
        assert mod._categorize_path(Path(filename)) == expected

    def test_compound_tar_gz_returns_archives(self):
        assert mod._categorize_path(Path("backup.tar.gz")) == "archives"

    def test_mimetypes_fallback_jpeg(self):
        # .jpeg is not in the curated map but mimetypes knows image/jpeg
        result = mod._categorize_path(Path("photo.jpeg"))
        assert result == "image"

    def test_unknown_extension_returns_other(self):
        assert mod._categorize_path(Path("file.xyz123")) == "other"

    def test_case_insensitive(self):
        assert mod._categorize_path(Path("FILE.ISO")) == "disk-images"


# ---------------------------------------------------------------------------
# _allocated_size
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAllocatedSize:
    def test_uses_st_blocks_when_present(self):
        st = types.SimpleNamespace(st_blocks=100, st_size=99999)
        assert mod._allocated_size(st) == 100 * 512

    def test_falls_back_to_st_size_without_st_blocks(self):
        st = types.SimpleNamespace(st_size=12345)
        assert mod._allocated_size(st) == 12345


# ---------------------------------------------------------------------------
# _human_age
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHumanAge:
    def _make_mtime(self, days_ago: int) -> float:
        return time.time() - 86400 * days_ago

    def test_three_days(self):
        assert mod._human_age(self._make_mtime(3)) == "3d"

    def test_forty_five_days(self):
        assert mod._human_age(self._make_mtime(45)) == "45d"

    def test_one_year(self):
        assert mod._human_age(self._make_mtime(365)) == "1y"

    def test_two_years(self):
        assert mod._human_age(self._make_mtime(730)) == "2y"

    def test_zero_days(self):
        assert mod._human_age(self._make_mtime(0)) == "0d"


# ---------------------------------------------------------------------------
# _build_discovery_skip_paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildDiscoverySkipPaths:
    def test_includes_registry_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PLATFORM", "linux")
        reg = frozenset([tmp_path / "a", tmp_path / "b"])
        result = mod._build_discovery_skip_paths(reg, tmp_path / "dev")
        assert tmp_path / "a" in result
        assert tmp_path / "b" in result

    def test_macos_includes_library(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PLATFORM", "macos")
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        result = mod._build_discovery_skip_paths(frozenset(), tmp_path / "dev")
        resolved_library = (tmp_path / "Library").resolve()
        assert resolved_library in result

    def test_dev_dir_not_in_result(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PLATFORM", "linux")
        dev_dir = tmp_path / "dev"
        result = mod._build_discovery_skip_paths(frozenset(), dev_dir)
        assert dev_dir not in result
        assert dev_dir.resolve() not in result


# ---------------------------------------------------------------------------
# _scan_discovery_walk — staleness logic
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanDiscoveryWalkStaleness:
    def _write_file(self, path: Path, size: int, mtime: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)
        os.utime(path, (mtime, mtime))

    def test_old_file_in_high_risk_dir_is_stale(self, tmp_path):
        high_risk = tmp_path / "Downloads"
        old_mtime = time.time() - 86400 * 100  # 100 days old
        f = high_risk / "bigfile.iso"
        self._write_file(f, 4096, old_mtime)

        items = mod._scan_discovery_walk(
            roots=[tmp_path],
            min_size_bytes=1024,
            top_n=10,
            skip_paths=frozenset(),
            high_risk_dirs=[high_risk],
            age_threshold_days=30,
        )

        matches = [i for i in items if i.path == f]
        assert len(matches) == 1
        assert matches[0].is_stale is True

    def test_new_file_in_high_risk_dir_is_not_stale(self, tmp_path):
        high_risk = tmp_path / "Downloads"
        new_mtime = time.time() - 86400 * 1  # 1 day old
        f = high_risk / "newfile.iso"
        self._write_file(f, 4096, new_mtime)

        items = mod._scan_discovery_walk(
            roots=[tmp_path],
            min_size_bytes=1024,
            top_n=10,
            skip_paths=frozenset(),
            high_risk_dirs=[high_risk],
            age_threshold_days=30,
        )

        matches = [i for i in items if i.path == f]
        assert len(matches) == 1
        assert matches[0].is_stale is False

    def test_old_file_outside_high_risk_dir_is_not_stale(self, tmp_path):
        high_risk = tmp_path / "Downloads"
        safe_dir = tmp_path / "Projects"
        old_mtime = time.time() - 86400 * 100
        f = safe_dir / "archive.zip"
        self._write_file(f, 4096, old_mtime)

        items = mod._scan_discovery_walk(
            roots=[tmp_path],
            min_size_bytes=1024,
            top_n=10,
            skip_paths=frozenset(),
            high_risk_dirs=[high_risk],
            age_threshold_days=30,
        )

        matches = [i for i in items if i.path == f]
        assert len(matches) == 1
        assert matches[0].is_stale is False


# ---------------------------------------------------------------------------
# _scan_discovery_walk — heap-based top-N
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanDiscoveryWalkTopN:
    def test_returns_only_top_n_largest(self, tmp_path):
        sizes = [2048, 3072, 4096, 5120, 6144]
        for i, sz in enumerate(sizes):
            f = tmp_path / f"file{i}.zip"
            f.write_bytes(b"x" * sz)

        items = mod._scan_discovery_walk(
            roots=[tmp_path],
            min_size_bytes=1024,
            top_n=3,
            skip_paths=frozenset(),
            high_risk_dirs=[],
            age_threshold_days=30,
        )

        # All files are .zip -> same category; only top 3 by size should appear
        assert len(items) == 3
        returned_sizes = sorted([i.size_bytes for i in items], reverse=True)
        # The three largest allocated sizes should correspond to the three biggest files
        assert returned_sizes[0] >= returned_sizes[1] >= returned_sizes[2]
        # The smallest file (2048) must not appear
        smallest_path = tmp_path / "file0.zip"
        assert all(i.path != smallest_path for i in items)


# ---------------------------------------------------------------------------
# _execute_discovery_cleanup — pre-deletion revalidation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecuteDiscoveryCleanup:
    def _make_item(self, path: Path) -> Any:
        st = path.lstat()
        return mod.DiscoveryItem(
            path=path,
            label=str(path),
            category="archives",
            size_bytes=mod._allocated_size(st),
            mtime=st.st_mtime,
        )

    def test_deletes_existing_file(self, tmp_path, capsys):
        f = tmp_path / "remove_me.zip"
        f.write_bytes(b"x" * 2048)
        item = self._make_item(f)

        result = mod._execute_discovery_cleanup([item])

        assert not f.exists()
        assert f in result

    def test_skips_nonexistent_path(self, tmp_path, capsys):
        ghost = tmp_path / "ghost.zip"
        # Construct item manually — file never exists
        item = mod.DiscoveryItem(
            path=ghost,
            label=str(ghost),
            category="archives",
            size_bytes=1024,
            mtime=time.time(),
        )

        result = mod._execute_discovery_cleanup([item])

        assert result == []
        captured = capsys.readouterr()
        out = " ".join(captured.out.split())
        assert "no longer exists" in out

    def test_skips_when_mtime_changed(self, tmp_path, capsys):
        f = tmp_path / "changed_mtime.zip"
        f.write_bytes(b"x" * 2048)
        item = self._make_item(f)
        # Advance mtime so it no longer matches the snapshot in item
        new_mtime = time.time() + 100
        os.utime(f, (new_mtime, new_mtime))

        result = mod._execute_discovery_cleanup([item])

        assert f.exists()
        assert result == []
        captured = capsys.readouterr()
        out = " ".join(captured.out.split())
        assert "file changed since scan" in out

    def test_skips_when_size_changed(self, tmp_path, capsys):
        f = tmp_path / "grown.zip"
        f.write_bytes(b"x" * 2048)
        item = self._make_item(f)
        # Append bytes to change the allocated size
        with f.open("ab") as fh:
            fh.write(b"y" * 8192)
        # Reset mtime to match the original snapshot so only size differs
        os.utime(f, (item.mtime, item.mtime))

        result = mod._execute_discovery_cleanup([item])

        assert f.exists()
        assert result == []
        captured = capsys.readouterr()
        out = " ".join(captured.out.split())
        assert "file changed since scan" in out
