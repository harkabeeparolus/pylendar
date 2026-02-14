# Justfile for pylendar project

# All commands need to be very simple and cross-platform compatible,
# so they work both in bash and Powershell.

# Default recipe lists all available commands
_default:
    @just --list

# Run all checks (lint + test)
check: lint test

# Format code and fix linting issues
fix: ruff-fix

# Run the main application (for testing)
run *ARGS:
    uv run pylendar {{ARGS}}

# Install dependencies
install:
    uv sync

# Build the package (sdist + wheel)
build:
    uv build

# Run all tests
test *ARGS:
    uv run pytest {{ARGS}}

# Run all linting tools
[group('details')]
lint: ruff-check ruff-format pylint mypy ty

# Run ruff checks
[group('details')]
ruff-check:
    uv run ruff check .

# Run ruff formatting check
[group('details')]
ruff-format:
    uv run ruff format --check .

# Fix ruff issues automatically
[group('details')]
ruff-fix:
    uv run ruff check --fix .
    uv run ruff format .

# Run pylint
[group('details')]
pylint:
    uv run pylint src/ test/

# Run mypy type checking
[group('details')]
mypy:
    uv run mypy src/

# Run ty type checking
[group('details')]
ty:
    uv run ty check

# Run tests with coverage
[group('details')]
_test-coverage:
    uv run pytest --cov=pylendar --cov-report=term-missing

# Show project status
status:
    @echo "Python version:"
    @uv run python --version
    @echo ""
    @echo "Installed packages:"
    @uv tree --outdated
    @echo ""
    @echo "Project info:"
    @uv run python -c "import pylendar; print(f'pylendar version: {pylendar.__version__ if hasattr(pylendar, \"__version__\") else \"dev\"}')" 2>/dev/null || echo "pylendar: not installed/importable"
