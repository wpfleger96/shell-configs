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
    shfmt -f . | grep -v git-prompt.sh | xargs shellcheck

format-python-check:
    uvx ruff format . --check

format-shell-check:
    shfmt -f . | grep -v git-prompt.sh | xargs shfmt -d

# Code Quality - Fix variants
lint-python:
    uvx ruff check . --fix

format-python:
    uvx ruff format .

format-shell:
    shfmt -f . | grep -v git-prompt.sh | xargs shfmt -w

# Composite quality checks
check: sync type-check lint-python-check lint-shell-check format-python-check format-shell-check
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
ci: sync type-check lint-python-check lint-shell-check format-python-check format-shell-check test
    @echo "CI checks passed"
