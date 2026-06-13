"""Validate the real bundled config across shells.

`test_cli_e2e.py` already covers `validate --shells bash`. This adds a full
multi-shell validation (real `bash -n` + `zsh -n` against the bundled config),
which only runs where zsh is available — CI installs it on Linux; macOS ships it.
"""

from __future__ import annotations

import pytest

from tests.e2e.helpers import shell_available, strip_ansi


@pytest.mark.e2e
@pytest.mark.skipif(not shell_available("zsh"), reason="zsh not installed")
class TestValidateAllShells:
    def test_bash_and_zsh_configs_valid(self, run_cli):
        result = run_cli(["validate"])
        output = strip_ansi(result.stdout + result.stderr)
        assert result.returncode == 0, output
        assert "All configurations are valid" in output
        assert "syntax error" not in output.lower()
