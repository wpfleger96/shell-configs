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

```bash
cd shell-configs
uv sync
```

### Quick Start

1. **Initialize your repository**:
   ```bash
   mkdir ~/shell-configs && cd ~/shell-configs
   mkdir -p config/{bash,zsh,git,shared-scripts}
   ```

2. **Add your shared configurations**:
   ```bash
   echo "alias ll='ls -la'" > config/bash/bashrc
   echo "alias ll='ls -la'" > config/zsh/zshrc
   ```

3. **Install and check status**:
   ```bash
   uv run shell-configs install
   uv run shell-configs status
   ```

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

### Additional Files

Files in config directories (except main config files like `bashrc`) are automatically installed as additional files:

| Source Directory | Installed To | Purpose |
|-----------------|--------------|---------|
| `config/bash/` | `~/.bash/` | Bash-specific scripts |
| `config/zsh/` | `~/.zsh/` | Zsh-specific scripts |
| `config/shared-scripts/` | `~/.bash/` and `~/.zsh/` | Scripts shared across shells |
| `config/git/` | `~/.config/git/` | Git configuration files |

**Example:** `config/shared-scripts/git-prompt.sh` is installed to both `~/.bash/git-prompt.sh` and `~/.zsh/git-prompt.sh`, then sourced by each shell's configuration.

### Shared Configuration

Reduce duplication by using shared config files:

- **`config/shared.sh`** - Common settings for bash/zsh (aliases, functions, environment variables)
- **`config/shared.gitconfig`** - Common git settings (aliases, core settings, colors)

When installed, shared configs are combined with shell-specific configs using subsection markers:

```bash
##### shell-configs Managed Config #####
### Shared Config ###
alias ll='ls -la'
export EDITOR=vim

### Shell-Specific Config ###
export HISTSIZE=10000
export PS1='\u@\h:\w\$ '
##### End shell-configs Managed Config #####
```

**Guidelines:**
- **Shared:** Universal aliases, environment variables, POSIX functions
- **Shell-specific:** History settings, prompts, shell options (shopt/setopt)
- **Machine-specific:** User name/email, GPG keys (add outside managed sections)

## How It Works

When you run `shell-configs install`, the tool:

1. Reads configuration files from the `config/` directory
2. Inserts them into your shell config files with clear markers
3. Creates backups before making changes

The installed configuration looks like this:

```bash
# Your existing .bashrc content
export PATH="/usr/local/bin:$PATH"

##### shell-configs Managed Config #####
alias ll='ls -la'
alias gs='git status'
##### End shell-configs Managed Config #####
```

On subsequent installs, the managed section is updated in-place while preserving all other content.

## Backups

Before any modification, `shell-configs` creates timestamped backups:

```
~/.bashrc.shell-configs-backup.20250115-143022
```

These backups allow you to recover previous configurations if needed.

## Example: Work and Personal Machines

On your work laptop with company-specific configurations:

```bash
# ~/.bashrc (before)
export COMPANY_VAR="value"
source /opt/company/bashrc

# ~/.bashrc (after shell-configs install)
export COMPANY_VAR="value"
source /opt/company/bashrc

##### shell-configs Managed Config #####
alias ll='ls -la'
alias gs='git status'
##### End shell-configs Managed Config #####
```

Your personal shared configs coexist with company configs. Update across machines:

```bash
# On machine A: make changes
echo "alias gp='git push'" >> config/bash/bashrc
git commit -am "Add git push alias" && git push

# On machine B: sync
git pull && uv run shell-configs install
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit

# Run integration tests only
uv run pytest -m integration

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing
```

### Code Quality

```bash
# Run linting and formatting
./script/code_quality.sh

# Run linting, formatting, and tests
RUN_TESTS=1 ./script/code_quality.sh
```

## Troubleshooting

### "Not in a shell-configs repository"

Make sure you're running commands from within the repository directory. The tool looks for a `config/` directory to identify the repository root.

### Validation Errors

If validation fails, check the syntax of your configuration files:

```bash
# Test bash syntax
bash -n config/bash/bashrc

# Test zsh syntax
zsh -n config/zsh/zshrc

# Test git config syntax
git config --list --file config/shared.gitconfig
```

### Permission Errors

Ensure you have write permissions to your config files:

```bash
ls -l ~/.bashrc ~/.zshrc ~/.gitconfig
```

## License

MIT

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting:

```bash
RUN_TESTS=1 ./script/code_quality.sh
```
