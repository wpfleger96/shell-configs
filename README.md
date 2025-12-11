# shell-configs

Manage shell configuration files across machines with version control.

## Features

- **Non-destructive**: Preserves existing configurations while adding managed sections
- **Multi-shell support**: Works with Bash, Zsh, and Git configurations
- **Version controlled**: Store shared configs in a git repository
- **Safe operations**: Creates timestamped backups before modifications
- **Syntax validation**: Validate configuration syntax before installation

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

| Command | Description | Example |
|---------|-------------|---------|
| `install` | Install or update managed sections | `uv run shell-configs install` |
| `status` | Show sync status (✓ Synced, ⚠ Outdated, ✗ Not installed) | `uv run shell-configs status` |
| `diff` | Show differences between repository and installed configs | `uv run shell-configs diff` |
| `uninstall` | Remove managed sections | `uv run shell-configs uninstall` |
| `validate` | Validate configuration file syntax | `uv run shell-configs validate` |
| `list-shells` | List all available shell configurations | `uv run shell-configs list-shells` |

### Common Options

- `--shells bash,zsh` - Operate on specific shells only
- `--dry-run` - Preview changes without applying
- `--force` - Skip confirmation prompts

## Configuration Guide

### Directory Structure

```
shell-configs/
├── config/
│   ├── bash/
│   │   ├── bashrc              # Main bash config
│   │   └── *.sh                # Additional bash scripts → ~/.bash/
│   ├── zsh/
│   │   ├── zshrc               # Main zsh config
│   │   └── *.sh                # Additional zsh scripts → ~/.zsh/
│   ├── git/
│   │   ├── ignore              # Global gitignore → ~/.config/git/
│   │   └── *                   # Other git configs → ~/.config/git/
│   ├── shared-scripts/
│   │   └── *.sh                # Shared scripts → ~/.bash/ and ~/.zsh/
│   ├── shared.sh               # Shared shell config (bash/zsh)
│   └── shared.gitconfig        # Shared git config
```

## License

MIT
