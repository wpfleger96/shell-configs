# shell-configs

Manage shell configuration files across machines with version control.

## Features

- **Non-destructive**: Preserves existing configurations while adding managed sections
- **Multi-shell support**: Works with Bash, Zsh, and Git configurations
- **Version controlled**: Store shared configs in a git repository
- **Safe operations**: Creates timestamped backups before modifications
- **Syntax validation**: Validate configuration syntax before installation
- **Included utilities**: Git worktree management, shell aliases, and productivity tools

## Getting Started

### Installation

**From GitHub (Development)**

Install from GitHub to get the latest development code:

```bash
uv tool install git+ssh://git@github.com/wpfleger96/shell-configs.git
```

**From Cloned Repository**

```bash
cd shell-configs
uv run shell-configs setup
```

### Quick Start with Just

This project uses [just](https://github.com/casey/just) for task automation.

**Install just:**
```bash
# macOS
brew install just
# Linux
cargo install just  # or: sudo apt install just (Ubuntu 23.04+)
# Windows
choco install just
```

**Common commands:**
| Command | Description |
|---------|-------------|
| `just` | Quick quality checks (sync, type-check, lint, format check) |
| `just setup` | First-time setup (sync deps + install git hooks) |
| `just check` | Quick quality checks (no tests) |
| `just check-all` | All checks including tests |
| `just test` | Run all tests |
| `just test-unit` | Run unit tests only |
| `just test-integration` | Run integration tests only |
| `just test-cli` | Run CLI tests only |
| `just test-cov` | Run tests with coverage report |
| `just lint` | Fix linting issues |
| `just format` | Auto-format code |
| `just type-check` | Run mypy type checking |
| `just pre-commit` | Full pre-commit workflow |
| `just --list` | List all available commands |

## Commands

See [CLI Reference](docs/CLI_REFERENCE.md) for complete command documentation.

**Quick start examples:**
- `uv run shell-configs setup` - Install shell-configs permanently (with auto-upgrade check)
- `uv run shell-configs install` - Install or update managed sections
- `uv run shell-configs status` - Show sync status (✓ Synced, ⚠ Outdated, ✗ Not installed)
- `shell-configs upgrade` - Check for and install available updates (shows changelog)

### Common Options

- `--shells bash,zsh` - Operate on specific shells only
- `--dry-run` - Preview changes without applying
- `-y` / `--yes` - Auto-confirm without prompting

### Backup Management

shell-configs automatically creates timestamped backups before modifying configs. By default, it keeps the 5 most recent backups per file and auto-removes older ones.

**Cleanup options:**
- `--keep N` - Keep N most recent backups (overrides default)
- `--dry-run` - Show what would be deleted
- `-y` / `--yes` - Auto-confirm without prompting

## Included Utilities

After installing shell-configs, you get productivity aliases and functions:

### Git Worktree Management

Manage multiple branches simultaneously with streamlined commands:

```bash
wt add feature-auth --open    # Create worktree and open in editor
wt add feature-auth --base dev # Create from specific base branch
wt list                       # Show all worktrees with [MERGED] and [ORPHAN] markers
wt cd feature-auth            # Navigate to worktree
wt rm feature-auth            # Remove worktree
wt orphans                    # List orphaned/stale worktrees
wt prune                      # Remove merged worktrees
wt prune --orphans            # Also remove orphaned/stale worktrees
```

Worktrees stored in `.worktrees/` (auto-gitignored). Prompt shows `[wt]` and git status when in worktree. Tab completion for branches and commands.

**Customize:** Set `WT_DIR` (default: `.worktrees`) and `WT_EDITOR` (default: `cursor`).

### Git Aliases

Common operations shortened:

```bash
# Basic operations
ga / gaa          # git add / git add .
gc -m "msg"       # git commit
gd / gds          # git diff / diff --staged
gl / gla          # git log (last 15 / all, graph)
gf                # git fetch
gp / gpu          # git pull / push
gs                # git status
gch / gchb        # git checkout / checkout -b

# Stash operations
gst / gstu        # git stash / stash -u (with untracked)
gstp              # git stash pop

# Useful shortcuts
gundo / gunstage  # Undo last commit / unstage files
grecover          # Reset to ORIG_HEAD (undo rebase/merge)
safepull          # Safe pull (fetch + merge, no rebase)
sync-fork         # Sync fork with upstream/main
yeet              # Amend last commit (no edit)
yeet_to_github    # Amend + force push with lease

# History & inspection
grl               # git reflog
gwhatchanged      # Show what changed since last pull
recent_commits    # Formatted log by date
```

**Git config aliases** (also available): `st`, `co`, `br`, `ci`, `unstage`, `last`, `lg`, `amend`

### Development Tools

```bash
# Python
pytest_coverage              # Run pytest with coverage report
python_package_versions pkg  # Check available versions

# Node
npm_package_versions pkg     # Check NPM package versions

# Docker
docker_cleanup              # Remove unused images/containers

# AI Tools - Claude Code
ccusage                      # Claude Code usage stats
ccviewer                     # View Claude Code sessions
run_claude_code_logger       # Start logging proxy
claude_with_logger           # Run Claude with logging

# AI Tools - Goose
run_goose_recipe recipe      # Run Goose recipe interactively
query_goose_database "sql"   # Query Goose sessions database
mcp_inspector                # Run MCP inspector
```

### Other Utilities

```bash
ll                      # ls -la
extract file.zip        # Extract any archive format
unlock_file file.dmg    # Remove macOS quarantine (zsh only)
```

### Git Configuration Enhancements

- **Auto-setup remote:** `git push` automatically sets up remote tracking
- **Default branch:** `main` (not master)
- **Rerere enabled:** Automatically reuse recorded merge conflict resolutions
- **Merge conflict style:** diff3 (shows original, theirs, and yours)

## Configuration Guide

### Directory Structure

```
shell-configs/
└── config/
    ├── bash/
    │   └── bashrc              # Main bash config
    ├── zsh/
    │   └── zshrc               # Main zsh config
    ├── git/
    │   └── ignore              # Global gitignore → ~/.config/git/
    ├── shared-scripts/
    │   └── git-prompt.sh       # Git prompt script (vendored)
    ├── shared.sh               # Shared shell config (bash/zsh)
    └── shared.gitconfig        # Shared git config
```

## License

MIT
