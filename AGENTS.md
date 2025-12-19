# AGENTS.md

CLI tool to manage shell configurations (bash, zsh, git) by installing "managed sections" into user config files while preserving existing content.

## Application Commands

| Command | Description | Example |
|---------|-------------|---------|
| `setup` | First-time setup (sync deps + install git hooks) | `uv run shell-configs setup` |
| `install` | Install or update managed sections | `uv run shell-configs install` |
| `status` | Show sync status (✓ Synced, ⚠ Outdated, ✗ Not installed) | `uv run shell-configs status` |
| `diff` | Show differences between repository and installed configs | `uv run shell-configs diff` |
| `uninstall` | Remove managed sections | `uv run shell-configs uninstall` |
| `validate` | Validate configuration file syntax | `uv run shell-configs validate` |
| `list-shells` | List all available shell configurations | `uv run shell-configs list-shells` |
| `info` | Show installation source and version info | `shell-configs info` |
| `upgrade` | Check for and install available updates | `shell-configs upgrade` |
| `completions install` | Install shell tab completion | `shell-configs completions install` |
| `completions bash` | Output bash completion script | `shell-configs completions bash` |
| `completions zsh` | Output zsh completion script | `shell-configs completions zsh` |
| `completions uninstall` | Remove shell completion | `shell-configs completions uninstall` |

**Common options:** `--shells bash,zsh`, `--dry-run`, `--force`

## Development Commands

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
```

## Project Structure

```
src/shell_configs/
├── cli.py              # Click CLI entry point
├── config.py           # ConfigReader for reading configs
├── manager.py          # ConfigManager for install/uninstall operations
├── display.py          # Rich console output utilities
├── completions.py      # Shell completion management (install/uninstall)
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
└── config/             # Bundled config files
    ├── bash/
    │   └── bashrc      # Main bash config
    ├── zsh/
    │   └── zshrc       # Main zsh config
    ├── git/
    │   └── ignore      # Global gitignore
    ├── shared-scripts/
    │   └── git-prompt.sh  # Git prompt script (vendored)
    ├── shared.sh       # Shared shell config (bash/zsh)
    └── shared.gitconfig   # Shared git config
tests/
├── conftest.py         # Fixtures: temp_dir, mock_home, test_repo, cli_runner
├── unit/               # Unit tests (-m unit)
└── integration/        # Integration tests (-m integration, -m cli)
```

## Bundled Shell Utilities

The managed configs include these shell utilities (sourced when installed):

**Git Worktree Management (`wt` command):**
```bash
wt add <branch> [--open] [--base <branch>]  # Create worktree
wt list                                      # List worktrees (shows [MERGED], [ORPHAN] status)
wt cd <branch>                               # Navigate to worktree
wt rm <branch> [--force]                     # Remove worktree
wt prune [--force] [--orphans]               # Clean up merged/orphan worktrees
wt orphans                                   # List orphaned worktrees
```

**Python/Node Utilities:**
- `pytest_coverage` - Run pytest with coverage
- `python_package_versions <pkg>` - Check PyPI versions
- `npm_package_versions <pkg>` - Check npm versions for @block scope

**AI Tool Helpers:**
- `run_goose_recipe <recipe>` - Run Goose recipe interactively
- `query_goose_database <sql>` - Query Goose sessions DB
- `mcp_inspector` - Launch MCP inspector

**General:**
- `extract <file>` - Extract archives (tar.gz, zip, etc.)
- `docker_cleanup` - Prune Docker images and containers

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
8. **Worktree auto-prune removed:** `wt add` no longer auto-prunes worktrees. New branches created from main won't be immediately deleted. Use `wt list` to see `[MERGED]` and `[ORPHAN]` markers, then run `wt prune` manually when needed. Implementation: Orphan detection is consolidated in `_wt_is_orphan()` helper (used by `_wt_ls`, `_wt_prune`, `_wt_orphans`)
9. **GitHub CLI Required (Private Repo):** This repository is PRIVATE. All GitHub operations (PRs, issues, releases, checks) MUST use `gh` CLI commands with authentication. Standard GitHub API calls will fail. Examples:
   - Create PR: `gh pr create --title "..." --body "..."`
   - View issue: `gh issue view 123`
   - Check PR status: `gh pr checks`
   - **Never** use `curl https://api.github.com/...` directly

## Key Files by Task

| Task | Files |
|------|-------|
| Add CLI command | `src/shell_configs/cli.py` |
| Add shell type | `src/shell_configs/shells/` + `registry.py` |
| Change install behavior | `src/shell_configs/manager.py` |
| Add bundled config | `src/shell_configs/config/{shell}/` |
| Modify shell utilities (wt, extract, etc.) | `src/shell_configs/config/shared.sh` |
| Modify completion logic | `src/shell_configs/completions.py` |
| Fix test fixtures | `tests/conftest.py` |
