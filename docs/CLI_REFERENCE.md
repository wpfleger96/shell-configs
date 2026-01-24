# shell-configs CLI Reference

Auto-generated from `--help`. Do not edit manually.

This is the complete CLI reference for shell-configs. For quick start examples and usage guides, see [README.md](../README.md).

## `shell-configs`

```
Usage: shell-configs [OPTIONS] COMMAND [ARGS]...

  Manage shell configuration files across machines.

Options:
  --version  Show version and check for updates
  --help     Show this message and exit.

Commands:
  cleanup      Clean up old backup files created by shell-configs.
  completions  Manage shell tab completion.
  diff         Show differences between repository and installed...
  info         Show installation source and version info for shell-configs.
  install      Install or update managed configuration sections.
  list-shells  List all available shell configurations.
  packages     Manage system packages required by shell-configs.
  setup        One-command setup for shell-configs.
  signing      Validate SSH signing key is registered with GitHub.
  status       Show the status of managed configurations.
  uninstall    Remove managed configuration sections.
  upgrade      Upgrade shell-configs to the latest version from GitHub.
  validate     Validate configuration file syntax.
```

## `shell-configs cleanup`

```
Usage: shell-configs cleanup [OPTIONS]

  Clean up old backup files created by shell-configs.

Options:
  --dry-run       Show what would be deleted without deleting
  --keep INTEGER  Number of backups to keep per config file
  -y, --yes       Auto-confirm without prompting
  --help          Show this message and exit.
```

## `shell-configs completions`

```
Usage: shell-configs completions [OPTIONS] COMMAND [ARGS]...

  Manage shell tab completion.

Options:
  --help  Show this message and exit.

Commands:
  bash       Output bash completion script for manual installation.
  install    Install shell completion to config file.
  status     Show shell completion installation status.
  uninstall  Remove shell completion from config file.
  zsh        Output zsh completion script for manual installation.
```

## `shell-configs completions bash`

```
Usage: shell-configs completions bash [OPTIONS]

  Output bash completion script for manual installation.

Options:
  --help  Show this message and exit.
```

## `shell-configs completions install`

```
Usage: shell-configs completions install [OPTIONS]

  Install shell completion to config file.

Options:
  --shell [bash|zsh]  Shell type (auto-detected if not specified)
  --help              Show this message and exit.
```

## `shell-configs completions status`

```
Usage: shell-configs completions status [OPTIONS]

  Show shell completion installation status.

Options:
  --help  Show this message and exit.
```

## `shell-configs completions uninstall`

```
Usage: shell-configs completions uninstall [OPTIONS]

  Remove shell completion from config file.

Options:
  --shell [bash|zsh]  Shell type (auto-detected if not specified)
  --help              Show this message and exit.
```

## `shell-configs completions zsh`

```
Usage: shell-configs completions zsh [OPTIONS]

  Output zsh completion script for manual installation.

Options:
  --help  Show this message and exit.
```

## `shell-configs diff`

```
Usage: shell-configs diff [OPTIONS]

  Show differences between repository and installed configurations.

Options:
  --shells TEXT  Comma-separated list of shells to diff
  --help         Show this message and exit.
```

## `shell-configs info`

```
Usage: shell-configs info [OPTIONS]

  Show installation source and version info for shell-configs.

  Displays how shell-configs was installed (GitHub) along with current version
  and update availability.

Options:
  --help  Show this message and exit.
```

## `shell-configs install`

```
Usage: shell-configs install [OPTIONS]

  Install or update managed configuration sections.

Options:
  --shells TEXT  Comma-separated list of shells to install (e.g.,
                 bash,zsh,git)
  --dry-run      Show what would be done without doing it
  -y, --yes      Auto-confirm without prompting
  --help         Show this message and exit.
```

## `shell-configs list-shells`

```
Usage: shell-configs list-shells [OPTIONS]

  List all available shell configurations.

Options:
  --help  Show this message and exit.
```

## `shell-configs packages`

```
Usage: shell-configs packages [OPTIONS] COMMAND [ARGS]...

  Manage system packages required by shell-configs.

Options:
  --help  Show this message and exit.

Commands:
  install    Install required system packages.
  status     Show status of required packages.
  uninstall  Uninstall managed system packages.
```

## `shell-configs packages install`

```
Usage: shell-configs packages install [OPTIONS]

  Install required system packages.

Options:
  --dry-run  Show what would be installed
  -y, --yes  Auto-confirm without prompting
  --help     Show this message and exit.
```

## `shell-configs packages status`

```
Usage: shell-configs packages status [OPTIONS]

  Show status of required packages.

Options:
  --help  Show this message and exit.
```

## `shell-configs packages uninstall`

```
Usage: shell-configs packages uninstall [OPTIONS]

  Uninstall managed system packages.

Options:
  --dry-run  Show what would be uninstalled
  -y, --yes  Auto-confirm without prompting
  --help     Show this message and exit.
```

## `shell-configs setup`

```
Usage: shell-configs setup [OPTIONS]

  One-command setup for shell-configs.

  Installs shell-configs globally via uv tool install, sets up shell
  configurations, and optionally installs tab completions.

  Run this after installing with uvx: uvx shell-configs setup

Options:
  -y, --yes           Auto-confirm without prompting
  --dry-run           Show what would be done
  --shells TEXT       Comma-separated shells to install
  --skip-completions  Skip shell completion setup
  --skip-packages     Skip package installation
  --help              Show this message and exit.
```

## `shell-configs signing`

```
Usage: shell-configs signing [OPTIONS]

  Validate SSH signing key is registered with GitHub.

Options:
  --fix          Auto-register SSH key if not registered for signing
  -v, --verbose  Show detailed key information
  --help         Show this message and exit.
```

## `shell-configs status`

```
Usage: shell-configs status [OPTIONS]

  Show the status of managed configurations.

Options:
  --shells TEXT  Comma-separated list of shells to check
  --help         Show this message and exit.
```

## `shell-configs uninstall`

```
Usage: shell-configs uninstall [OPTIONS]

  Remove managed configuration sections.

Options:
  --shells TEXT  Comma-separated list of shells to uninstall
  -y, --yes      Auto-confirm without prompting
  --help         Show this message and exit.
```

## `shell-configs upgrade`

```
Usage: shell-configs upgrade [OPTIONS]

  Upgrade shell-configs to the latest version from GitHub.

  Examples:     shell-configs upgrade             # Check and install updates
  shell-configs upgrade --check     # Only check for updates     shell-configs
  upgrade -y          # Auto-confirm installation

Options:
  --check    Check for updates without installing
  --force    Force reinstall even if up to date
  -y, --yes  Auto-confirm installation without prompting
  --help     Show this message and exit.
```

## `shell-configs validate`

```
Usage: shell-configs validate [OPTIONS]

  Validate configuration file syntax.

Options:
  --shells TEXT  Comma-separated list of shells to validate
  --help         Show this message and exit.
```

