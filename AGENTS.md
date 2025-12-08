# AGENTS.md

CLI tool to manage shell configurations (bash, zsh, git) by installing "managed sections" into user config files while preserving existing content.

## Quick Commands

```bash
just sync              # Install dependencies
just check             # Quick quality checks (type, lint, format)
just test              # Run all tests with coverage
just test-unit         # Unit tests only
just test-integration  # Integration tests
just test-cli          # CLI tests
just ci                # Full CI workflow
just pre-commit        # Pre-commit checks with auto-fix
```

## Project Structure

```
src/shell_configs/
├── cli.py              # Click CLI entry point
├── config.py           # ConfigReader for reading configs
├── manager.py          # ConfigManager for install/uninstall operations
├── display.py          # Rich console output utilities
├── completions.py      # Shell completion installation
├── shells/
│   ├── base.py         # Abstract Shell base class
│   ├── bash.py         # Bash implementation
│   ├── zsh.py          # Zsh implementation
│   ├── git.py          # Git config implementation
│   └── registry.py     # ShellRegistry for shell lookup
├── bootstrap/          # System-wide install & auto-update
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

## Key Files by Task

| Task | Files |
|------|-------|
| Add CLI command | `src/shell_configs/cli.py` |
| Add shell type | `src/shell_configs/shells/` + `registry.py` |
| Change install behavior | `src/shell_configs/manager.py` |
| Add bundled config | `src/shell_configs/config/{shell}/` |
| Fix test fixtures | `tests/conftest.py` |
