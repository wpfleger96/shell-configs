import sys

import pytest

from tests.e2e.helpers import strip_ansi


@pytest.mark.e2e
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsSpecific:
    def test_powershell_listed(self, run_cli):
        result = run_cli(["list-shells"])
        output = strip_ansi(result.stdout + result.stderr)
        assert "PowerShell" in output

    def test_completions_powershell(self, run_cli):
        result = run_cli(["completions", "status"])
        output = strip_ansi(result.stdout + result.stderr)
        assert "powershell" in output.lower()
