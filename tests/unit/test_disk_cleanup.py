"""Unit tests for the disk-cleanup standalone script."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import types

from collections.abc import Callable
from pathlib import Path

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
# Terminal width
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTermWidth:
    def test_returns_terminal_columns(self, monkeypatch):
        monkeypatch.setattr(
            os, "get_terminal_size", lambda *a: os.terminal_size((120, 40))
        )
        assert mod._term_width() == 120

    def test_falls_back_to_100_on_os_error(self, monkeypatch):
        def _raise(*args, **kwargs):
            raise OSError("not a terminal")

        monkeypatch.setattr(os, "get_terminal_size", _raise)
        assert mod._term_width() == 100

    def test_falls_back_to_100_on_value_error(self, monkeypatch):
        def _raise(*args, **kwargs):
            raise ValueError("bad fd")

        monkeypatch.setattr(os, "get_terminal_size", _raise)
        assert mod._term_width() == 100


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
        # Strip ANSI codes to measure actual visual width
        import re

        ansi_pattern = re.compile(r"\033\[[0-9;]*m")
        stripped = [ansi_pattern.sub("", r) for r in rows]
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

        rust_targets, incrementals = mod._scan_dev_tree(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert project / "target" in target_paths

    def test_finds_rust_target_with_release_child(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "release").mkdir(parents=True)

        rust_targets, _ = mod._scan_dev_tree(tmp_path)

        assert any(t.path == project / "target" for t in rust_targets)

    def test_synthesizes_incremental_when_dir_exists(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug" / "incremental").mkdir(parents=True)

        _, incrementals = mod._scan_dev_tree(tmp_path)

        incremental_paths = [t.path for t in incrementals]
        assert project / "target" / "debug" / "incremental" in incremental_paths

    def test_does_not_synthesize_incremental_when_dir_missing(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)

        _, incrementals = mod._scan_dev_tree(tmp_path)

        assert incrementals == []

    def test_does_not_descend_into_target_dir(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)
        nested = project / "target" / "nested_project" / "target" / "debug"
        nested.mkdir(parents=True)

        rust_targets, _ = mod._scan_dev_tree(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert project / "target" in target_paths
        assert nested.parent not in target_paths

    def test_skips_git_directories(self, tmp_path):
        git_dir = tmp_path / ".git"
        (git_dir / "objects").mkdir(parents=True)
        project_under_git = git_dir / "nested" / "target" / "debug"
        project_under_git.mkdir(parents=True)

        rust_targets, _ = mod._scan_dev_tree(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert all(".git" not in str(p) for p in target_paths)

    def test_does_not_skip_worktrees(self, tmp_path):
        worktrees_dir = tmp_path / ".worktrees" / "feature-branch"
        (worktrees_dir / "myproject" / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = mod._scan_dev_tree(tmp_path)

        target_paths = [t.path for t in rust_targets]
        assert any(".worktrees" in str(p) for p in target_paths)

    def test_does_not_follow_symlinks(self, tmp_path):
        outside = tmp_path / "outside"
        (outside / "target" / "debug").mkdir(parents=True)

        dev_dir = tmp_path / "dev"
        dev_dir.mkdir()
        link = dev_dir / "symlinked_project"
        os.symlink(outside, link)

        rust_targets, _ = mod._scan_dev_tree(dev_dir)

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
            rust_targets, _ = mod._scan_dev_tree(tmp_path)

        assert any(t.path == project / "target" for t in rust_targets)

    def test_target_category_is_target(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = mod._scan_dev_tree(tmp_path)

        assert all(t.category == "target" for t in rust_targets)

    def test_incremental_category_is_incremental(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug" / "incremental").mkdir(parents=True)

        _, incrementals = mod._scan_dev_tree(tmp_path)

        assert all(t.category == "incremental" for t in incrementals)

    def test_target_tier_is_3(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = mod._scan_dev_tree(tmp_path)

        assert all(t.tier == 3 for t in rust_targets)

    def test_incremental_tier_is_1(self, tmp_path):
        project = tmp_path / "myproject"
        (project / "target" / "debug" / "incremental").mkdir(parents=True)

        _, incrementals = mod._scan_dev_tree(tmp_path)

        assert all(t.tier == 1 for t in incrementals)

    def test_empty_dev_dir_returns_no_targets(self, tmp_path):
        rust_targets, incrementals = mod._scan_dev_tree(tmp_path)

        assert rust_targets == []
        assert incrementals == []

    def test_max_depth_limits_scan(self, tmp_path):
        deep = tmp_path
        for _ in range(10):
            deep = deep / "sub"
        (deep / "target" / "debug").mkdir(parents=True)

        rust_targets, _ = mod._scan_dev_tree(tmp_path, max_depth=3)

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

    def test_returns_zero_for_nonexistent_path(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "does_not_exist"

        monkeypatch.setattr(mod.subprocess, "run", _real_subprocess_run)

        size = mod._du_size_bytes(nonexistent)

        assert size == 0

    def test_returns_zero_on_subprocess_error(self, monkeypatch):
        def _failing_run(cmd, *args, **kwargs):
            raise OSError("du not found")

        monkeypatch.setattr(mod.subprocess, "run", _failing_run)

        size = mod._du_size_bytes(Path("/some/path"))

        assert size == 0

    def test_returns_zero_on_timeout(self, monkeypatch):
        def _timeout_run(cmd, *args, **kwargs):
            raise mod.subprocess.TimeoutExpired(cmd, 300)

        monkeypatch.setattr(mod.subprocess, "run", _timeout_run)

        size = mod._du_size_bytes(Path("/some/path"))

        assert size == 0


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
