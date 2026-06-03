# This file is managed by github-config. Do not edit manually.
# https://github.com/wpfleger96/github-config

# Settings
set dotenv-load := false

# Default recipe: quick quality check without tests
default: sync type-check lint-python-check lint-shell-check format-python-check format-shell-check

# Setup & Dependencies
sync:
    uv sync

# Code Quality - Check variants
type-check:
    uv run mypy .

lint-python-check:
    uvx ruff check .

lint-shell-check:
    shfmt -f . | grep -v git-prompt.sh | grep -v iterm2-shell-integration | grep -v 'src/shell_configs/scripts/' | xargs shellcheck

format-python-check:
    uvx ruff format . --check

format-shell-check:
    shfmt -f . | grep -v git-prompt.sh | grep -v iterm2-shell-integration | grep -v 'src/shell_configs/scripts/' | xargs shfmt -d

# Code Quality - Fix variants
lint-python:
    uvx ruff check . --fix

format-python:
    uvx ruff format .

format-shell:
    shfmt -f . | grep -v git-prompt.sh | grep -v iterm2-shell-integration | grep -v 'src/shell_configs/scripts/' | xargs shfmt -w

# Composite quality checks (lint-check/format-check used by CI workflow)
lint-check: lint-python-check lint-shell-check

format-check: format-python-check format-shell-check

check: sync type-check lint-check format-check
    @echo "Quick quality checks passed"

check-all: check test
    @echo "All quality checks and tests passed"

pre-commit: sync type-check lint-python lint-shell-check format-python format-shell test
    @echo "Pre-commit checks passed"

# Testing
test:
    uv run pytest

test-unit:
    uv run pytest -m unit

test-integration:
    uv run pytest -m integration

test-e2e:
    uv run pytest tests/e2e -m e2e --no-cov

# Build & Package
build: sync
    uv build

clean-build:
    rm -rf dist/ build/ src/*.egg-info

rebuild: clean-build build

# CI workflow (matches CI steps)
ci: sync type-check lint-python-check lint-shell-check format-python-check format-shell-check test
    @echo "CI checks passed"

import? 'local.just'
