"""Tests for display helpers and formatting utilities."""

from __future__ import annotations

import io

import pytest

from rich.console import Console

from shell_configs.display import (
    ICON_ERROR,
    ICON_SUCCESS,
    ICON_WARNING,
    _console_override,
    dim,
    get_status_indicator,
    print_dim,
    print_error,
    print_label,
    print_operation_result,
    print_section,
    print_success,
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


class TestPrintHelpers:
    @pytest.mark.parametrize(
        "helper,icon,message",
        [
            (print_error, "✗", "something broke"),
            (print_success, "✓", "it worked"),
        ],
    )
    def test_prints_icon_and_message(self, capture, helper, icon, message):
        helper(message)
        out = _output(capture)
        assert icon in out
        assert message in out

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
    def test_indent_two(self, capture):
        print_success("msg", indent=2)
        raw = capture.getvalue()
        assert raw.startswith("  ")


class TestPrintOperationResult:
    def test_created(self, capture):
        print_operation_result(OperationResult.CREATED, "created file")
        assert "✓" in _output(capture)
        assert "created file" in _output(capture)

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
