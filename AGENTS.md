# AGENTS.md

CLI tool to manage shell configurations (bash, zsh, git) by installing "managed sections" into user config files while preserving existing content.

## Quick Commands

```bash
# Setup & Quality Checks
just sync              # Install dependencies with uv
just                   # Default: quick quality checks (no tests)
just check             # Quick quality checks (type, lint, format)
just check-all         # All quality checks including tests
just ci                # Full CI workflow (matches GitHub Actions)
just pre-commit        # Pre-commit checks with auto-fix

# Testing
just test              # Run all tests with coverage
just test-unit         # Unit tests only (pytest -m unit)
just test-integration  # Integration tests (pytest -m integration)
just test-cli          # CLI tests (pytest -m cli)
just test-cov          # Tests with coverage report
just test-nocov        # Tests without coverage overhead

# Code Quality - Fix variants
just lint-python       # Fix Python linting issues (ruff --fix)
just format-python     # Auto-format Python code (ruff format)
just format-shell      # Auto-format shell scripts (shfmt -w)

# Code Quality - Check variants (CI mode)
just type-check        # Run mypy type checking (strict mode)
just lint-python-check # Check Python linting (ruff check)
just lint-shell-check  # Check shell scripts (shellcheck)
just format-python-check # Check Python formatting
just format-shell-check  # Check shell formatting

# CLI Development Helpers
just cli-install       # Test install command (dry-run)
just cli-status        # Test status command
just cli-validate      # Test validate command

# Installation & Upgrades
uv run shell-configs setup     # First-time setup (sync deps + install git hooks)
uv run shell-configs upgrade   # Check for and install updates from GitHub
```

## Project Structure

```
src/shell_configs/
├── cli.py              # Click CLI entry point
├── config.py           # ConfigReader for reading configs
├── manager.py          # ConfigManager for install/uninstall operations
├── display.py          # Rich console output utilities
├── completions.py      # Shell completion installation
├── installer.py        # Legacy installer (use bootstrap instead)
├── shells/
│   ├── base.py         # Abstract Shell base class
│   ├── bash.py         # Bash implementation
│   ├── zsh.py          # Zsh implementation
│   ├── git.py          # Git config implementation
│   └── registry.py     # ShellRegistry for shell lookup
├── bootstrap/          # System-wide install & auto-update
│   ├── installer.py    # uv tool install utilities
│   ├── updater.py      # GitHub update checking
│   ├── version.py      # Version comparison
│   └── config.py       # Auto-update config management
└── config/             # Bundled config files (bash/, zsh/, git/)
tests/
├── conftest.py         # Fixtures: temp_dir, mock_home, test_repo, cli_runner
├── unit/               # Unit tests (-m unit)
└── integration/        # Integration tests (-m integration, -m cli)
```

## Tech Stack

- Python 3.10+ (src layout)
- uv (package manager)
- click (CLI), rich (output), pyyaml
- mypy (strict mode), ruff (lint+format), pytest

## Key Patterns

**Shell implementations:** Extend `Shell` base class in `src/shell_configs/shells/base.py`. Implement: `name`, `display_name`, `get_config_files()`, `_get_validation_command()`, `_get_temp_suffix()`.

**Registry pattern:** Register shells in `src/shell_configs/shells/registry.py`.

**Marker-based sections:** Managed content uses markers:
```
##### shell-configs Managed Config #####
<content>
##### End shell-configs Managed Config #####
```

**Test fixtures:** Use `mock_home` for HOME isolation, `test_repo` for config mocking.

## Testing

```bash
just test              # All tests (default: with coverage)
just test-unit         # uv run pytest -m unit
just test-integration  # uv run pytest -m integration
just test-cli          # uv run pytest -m cli
just test-nocov        # Without coverage overhead
```

Markers: `unit`, `integration`, `cli`, `bootstrap`

## Common Gotchas

1. **Mock HOME properly:** Tests use `mock_home` fixture which patches `HOME` env var
2. **Config directory mocking:** Use `test_repo` fixture - it patches `get_config_dir()`
3. **Shell formatting:** `shfmt` excludes `git-prompt.sh` (vendored file)
4. **CLI runner width:** Tests set `COLUMNS=200` to prevent output wrapping
5. **Type checking:** mypy strict mode enabled - full type hints required
6. **Installation method:** Package is private - install via `uv tool install git+ssh://git@github.com/wpfleger96/shell-configs.git` (not PyPI)
7. **Shell linting:** `shellcheck` and `shfmt` both exclude `git-prompt.sh` automatically via justfile grep filter

## Key Files by Task

| Task | Files |
|------|-------|
| Add CLI command | `src/shell_configs/cli.py` |
| Add shell type | `src/shell_configs/shells/` + `registry.py` |
| Change install behavior | `src/shell_configs/manager.py` |
| Add bundled config | `src/shell_configs/config/{shell}/` |
| Fix test fixtures | `tests/conftest.py` |
