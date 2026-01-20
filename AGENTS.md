# AGENTS.md

Python CLI tool for managing shell configuration files (bash, zsh, git) across machines with version control, non-destructive installation via managed sections.

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
├── cli.py                      # Click CLI commands (install, status, diff, etc.)
├── manager.py                  # ConfigManager - insert/remove managed sections
├── config.py                   # ConfigReader - reads config/ directory
├── display.py                  # Rich console output formatting
├── signing.py                  # SSH signing key validation/setup
├── completions.py              # Shell completion generation
├── platform.py                 # Platform detection (Linux/macOS/WSL)
├── shells/                     # Shell implementations
│   ├── base.py                 # Shell ABC (ConfigFile, validation interface)
│   ├── bash.py, zsh.py         # Bash/Zsh shell implementations
│   ├── git.py                  # Git config handler
│   ├── cursor.py               # Cursor IDE WSL config
│   └── registry.py             # ShellRegistry for shell discovery
├── bootstrap/                  # Bootstrap/auto-update system
│   ├── config.py               # AutoUpdateConfig (backup retention)
│   ├── installer.py            # Tool installation via uv
│   ├── updater.py              # Update checking/installation
│   └── version.py              # Version comparison
├── packages/                   # Package management
│   └── packages.py             # Tool package definitions
└── config/                     # Managed shell configs (installed by tool)
    ├── bash/bashrc, zsh/zshrc  # Shell-specific configs
    ├── shared.sh               # Shared shell config
    └── shared.gitconfig        # Shared git config
tests/
├── conftest.py         # Fixtures (mock_home, test_repo, cli_runner)
├── unit/               # Fast unit tests (mock filesystem)
└── integration/        # Integration tests (real files)
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

- **Python 3.13** (requires >=3.10)
- **CLI:** Click 8.1+
- **Output:** Rich 13.0+ (console formatting)
- **Config:** PyYAML 6.0+, Pydantic 2.12+
- **Package manager:** uv
- **Task runner:** just
- **Linting:** ruff (isort, pyflakes, pyupgrade, bugbear)
- **Type checking:** mypy (strict mode)
- **Testing:** pytest + pytest-cov
- **Shell linting:** shellcheck + shfmt

## Key Patterns

**Managed Section Pattern:**
ConfigManager inserts/removes config sections delimited by markers:
```bash
##### shell-configs Managed Config #####
# User config preserved above
<managed content>
##### End shell-configs Managed Config #####
```

**Shell Abstraction:**
Each shell (bash, zsh, git) implements `Shell` ABC from `shells/base.py`:
- `get_config_files()` → list of ConfigFile (name, path, repo_config_name)
- `validate_syntax(content)` → (is_valid, error_message)
- Uses abstract `_get_validation_command()` for shell-specific validation

**Registry Pattern:**
`ShellRegistry` auto-discovers shell implementations:
```python
from shell_configs.shells.registry import get_registry
registry = get_registry()
selected_shells, invalid = registry.filter_by_names(["bash", "zsh"])
```

**Test Isolation:**
`mock_home` fixture patches BOTH `HOME` env var AND `Path.home()` to ensure full isolation (conftest.py:38-52).

**Backup Management:**
Timestamped backups with retention limit (default 5, see `AutoUpdateConfig`).

## Testing

```bash
# Run all tests
just test                            # Coverage enabled by default

# Run by marker
just test-unit                       # -m unit
just test-integration                # -m integration
just test-cli                        # -m cli

# Run specific tests
uv run pytest tests/unit/test_manager.py::test_insert_section
uv run pytest -k "test_install"      # Match by name
uv run pytest -v                     # Verbose output
```

**Test structure:**
- `unit/` - Fast tests with mocked filesystem (marker: `@pytest.mark.unit`)
- `integration/` - Real filesystem operations (marker: `@pytest.mark.integration`)
- Fixtures in `conftest.py`: `mock_home`, `test_repo`, `cli_runner`, `temp_dir`

## Common Gotchas

1. **Mock HOME completely:** Tests use `mock_home` fixture which patches BOTH `HOME` env var AND `Path.home()` staticmethod. Only mocking environ is insufficient if code uses `Path.home()` directly (conftest.py:38-52).

2. **Config directory mocking:** Use `test_repo` fixture - it patches `get_config_dir()`

3. **Shell formatting:** `shfmt` excludes `git-prompt.sh` (vendored file via justfile:19,25). Don't modify it.

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

10. **Local development vs installed tool** - **CRITICAL**: Always use `uv run shell-configs` when developing locally:
   - **Local dev (from repo)**: `uv run shell-configs <command>` → runs YOUR local code changes directly
   - **Installed tool (any directory)**: `shell-configs <command>` → runs installed version from `~/.local/share/uv/tools/`
   - Running `shell-configs` without `uv run` will NOT reflect your local changes
   - **NEVER use editable install** (`uv pip install -e .`) - risks conflicts with installed version, unnecessary complexity

11. **WSL platform detection:** Tests force Platform.LINUX (conftest.py:12-28) to prevent accidental Windows file modifications. Test WSL-specific code with explicit platform mocks.

12. **Backup retention:** Default 5 backups per config (AutoUpdateConfig). Old backups auto-cleaned after operations.

13. **Validation before install:** All configs validated via shell-specific commands (bash -n, zsh -n, git config --list) before installation.

14. **JSON config handling:** ConfigManager strips outer brackets for JSON/JSONC files when comparing managed sections (manager.py:86-100).

15. **uv sync required:** Run `just sync` or `uv sync` after pulling to ensure dependencies match lockfile.

## Key Files by Task

| Task | Files |
|------|-------|
| Add CLI command | `src/shell_configs/cli.py` |
| Modify config installation logic | `src/shell_configs/manager.py` (ConfigManager) |
| Add new shell support | `src/shell_configs/shells/` (new class extends Shell ABC) |
| Change config reading | `src/shell_configs/config.py` (ConfigReader) |
| Modify output formatting | `src/shell_configs/display.py` |
| Add SSH signing logic | `src/shell_configs/signing.py` |
| Change auto-update behavior | `src/shell_configs/bootstrap/updater.py` |
| Add package definitions | `src/shell_configs/packages/packages.py` |
| Modify test fixtures | `tests/conftest.py` |
| Add shell configs | `src/shell_configs/config/{bash,zsh,git}/` |
| Modify shell utilities (wt, extract, etc.) | `src/shell_configs/config/shared.sh` |
| Modify completion logic | `src/shell_configs/completions.py` |
