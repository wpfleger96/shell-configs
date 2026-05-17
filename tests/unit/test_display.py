"""Tests for display helpers, icon constants, and formatting utilities."""

from __future__ import annotations

import io

import pytest

from rich.console import Console

from shell_configs.display import (
    ICON_ADD,
    ICON_BUILTIN,
    ICON_DASH,
    ICON_DONE,
    ICON_ERROR,
    ICON_HINT,
    ICON_INFO,
    ICON_PROGRESS,
    ICON_SKIPPED,
    ICON_SUCCESS,
    ICON_UNCHANGED,
    ICON_WARNING,
    ICON_WOULD,
    _console_override,
    dim,
    get_status_indicator,
    print_add,
    print_builtin,
    print_dim,
    print_done,
    print_error,
    print_hint,
    print_info,
    print_label,
    print_operation_result,
    print_progress,
    print_section,
    print_skipped,
    print_success,
    print_unchanged,
    print_warning,
    print_would,
)
from shell_configs.manager import OperationResult


@pytest.fixture()
def capture():
    buf = io.StringIO()
    con = Console(file=buf, highlight=False, no_color=True, width=120)
    token = _console_override.set(con)
    yield buf
    _console_override.reset(token)


def _output(buf: io.StringIO) -> str:
    return buf.getvalue().strip()


class TestDimBuilder:
    def test_wraps_text(self):
        assert dim("hello") == "[dim]hello[/dim]"

    def test_empty_string(self):
        assert dim("") == "[dim][/dim]"


class TestPrintHelpers:
    def test_print_error(self, capture):
        print_error("something broke")
        assert "✗" in _output(capture)
        assert "something broke" in _output(capture)

    def test_print_warning(self, capture):
        print_warning("watch out")
        assert "⚠" in _output(capture)
        assert "watch out" in _output(capture)

    def test_print_info(self, capture):
        print_info("fyi")
        assert "ℹ" in _output(capture)
        assert "fyi" in _output(capture)

    def test_print_hint(self, capture):
        print_hint("try this")
        assert "»" in _output(capture)
        assert "try this" in _output(capture)

    def test_print_success(self, capture):
        print_success("it worked")
        assert "✓" in _output(capture)
        assert "it worked" in _output(capture)

    def test_print_done(self, capture):
        print_done("already done")
        assert "✓" in _output(capture)
        assert "already done" in _output(capture)

    def test_print_unchanged(self, capture):
        print_unchanged("no change")
        assert "•" in _output(capture)
        assert "no change" in _output(capture)

    def test_print_skipped(self, capture):
        print_skipped("skipped it")
        assert "○" in _output(capture)
        assert "skipped it" in _output(capture)

    def test_print_would(self, capture):
        print_would("would do thing")
        assert "→" in _output(capture)
        assert "would do thing" in _output(capture)

    def test_print_add(self, capture):
        print_add("new-item")
        assert "+" in _output(capture)
        assert "new-item" in _output(capture)

    def test_print_progress(self, capture):
        print_progress("Installing...")
        assert "⟳" in _output(capture)
        assert "Installing..." in _output(capture)

    def test_print_builtin(self, capture):
        print_builtin("some.extension")
        assert "!" in _output(capture)
        assert "some.extension" in _output(capture)

    def test_print_dim(self, capture):
        print_dim("muted text")
        assert "muted text" in _output(capture)

    def test_print_label(self, capture):
        print_label("Platform", "macOS")
        out = _output(capture)
        assert "Platform:" in out
        assert "macOS" in out

    def test_print_section(self, capture):
        print_section("My Section")
        assert "My Section" in _output(capture)


class TestIndent:
    def test_indent_zero(self, capture):
        print_success("msg")
        raw = capture.getvalue()
        assert not raw.startswith(" ")

    def test_indent_two(self, capture):
        print_success("msg", indent=2)
        raw = capture.getvalue()
        assert raw.startswith("  ")

    def test_indent_four(self, capture):
        print_error("msg", indent=4)
        raw = capture.getvalue()
        assert raw.startswith("    ")

    def test_indent_six(self, capture):
        print_warning("msg", indent=6)
        raw = capture.getvalue()
        assert raw.startswith("      ")


class TestPrintOperationResult:
    def test_created(self, capture):
        print_operation_result(OperationResult.CREATED, "created file")
        assert "✓" in _output(capture)
        assert "created file" in _output(capture)

    def test_updated(self, capture):
        print_operation_result(OperationResult.UPDATED, "updated file")
        assert "✓" in _output(capture)

    def test_removed(self, capture):
        print_operation_result(OperationResult.REMOVED, "removed file")
        assert "✓" in _output(capture)

    def test_already_synced(self, capture):
        print_operation_result(OperationResult.ALREADY_SYNCED, "no change")
        assert "•" in _output(capture)

    def test_not_found(self, capture):
        print_operation_result(OperationResult.NOT_FOUND, "missing")
        assert "⚠" in _output(capture)

    def test_error(self, capture):
        print_operation_result(OperationResult.ERROR, "failed")
        assert "✗" in _output(capture)


class TestGetStatusIndicator:
    def test_not_exists(self):
        result = get_status_indicator(synced=False, exists=False)
        assert "Not installed" in result
        assert ICON_ERROR in result

    def test_exists_synced(self):
        result = get_status_indicator(synced=True, exists=True)
        assert "Synced" in result
        assert ICON_SUCCESS in result

    def test_exists_not_synced(self):
        result = get_status_indicator(synced=False, exists=True)
        assert "Outdated" in result
        assert ICON_WARNING in result


class TestIconConstants:
    @pytest.mark.parametrize(
        "icon,glyph",
        [
            (ICON_SUCCESS, "✓"),
            (ICON_DONE, "✓"),
            (ICON_UNCHANGED, "•"),
            (ICON_SKIPPED, "○"),
            (ICON_ERROR, "✗"),
            (ICON_WARNING, "⚠"),
            (ICON_INFO, "ℹ"),
            (ICON_HINT, "»"),
            (ICON_PROGRESS, "⟳"),
            (ICON_WOULD, "→"),
            (ICON_ADD, "+"),
            (ICON_BUILTIN, "!"),
            (ICON_DASH, "-"),
        ],
    )
    def test_icon_contains_glyph(self, icon, glyph):
        assert glyph in icon

    def test_success_is_green(self):
        assert "[green]" in ICON_SUCCESS

    def test_done_is_dim(self):
        assert "[dim]" in ICON_DONE

    def test_error_is_red(self):
        assert "[red]" in ICON_ERROR

    def test_warning_is_yellow(self):
        assert "[yellow]" in ICON_WARNING
