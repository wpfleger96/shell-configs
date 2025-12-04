# Settings
set dotenv-load := false

# Default recipe: quick quality check without tests
default: sync type-check lint-check format-check

# Setup & Dependencies
sync:
    uv sync

install-hooks:
    @echo "Installing git hooks..."
    git config --local core.hooksPath .hooks
    @echo "Git hooks installed successfully"

setup: sync install-hooks
    @echo "Development environment setup complete"

# Code Quality - Check variants
type-check:
    uv run mypy .

lint-check:
    uvx ruff check .

format-check:
    uvx ruff format . --check

# Code Quality - Fix variants
lint:
    uvx ruff check . --fix

format:
    uvx ruff format .

# Composite quality checks
check: sync type-check lint-check format-check
    @echo "Quick quality checks passed"

check-all: check test
    @echo "All quality checks and tests passed"

pre-commit: sync type-check lint format test
    @echo "Pre-commit checks passed"

# Testing
test:
    uv run pytest

test-unit:
    uv run pytest -m unit

test-integration:
    uv run pytest -m integration

test-cli:
    uv run pytest -m cli

test-cov:
    uv run pytest --cov=src --cov-report=term-missing

test-nocov:
    uv run pytest -o addopts='-v'

# CLI Testing (development helpers)
cli-install:
    uv run shell-configs install --dry-run

cli-status:
    uv run shell-configs status

cli-validate:
    uv run shell-configs validate

# CI workflow (matches CI steps)
ci: sync type-check lint-check format-check test
    @echo "CI checks passed"
