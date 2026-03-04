# Justfile for pylendar project

# All commands need to be very simple and cross-platform compatible,
# so they work both in bash and Powershell.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# Default recipe lists all available commands
_default:
    @just --list

# Autofix, lint, typecheck, and test
check: fix lint test

# Run the main application
run *ARGS:
    uv run pylendar {{ARGS}}

# Install dependencies
install:
    uv sync

# Build manpage from Markdown source (requires pandoc)
[unix]
build_man:
    mkdir -p share/man/man1
    pandoc docs/pylendar.1.md -s -t man -o share/man/man1/pylendar.1
    printf '.so man1/pylendar.1\n' > share/man/man1/calendar.1

# Build the package (sdist + wheel)
[unix]
build: build_man
    uv build

# Build the package (sdist + wheel, no manpage on Windows)
[windows]
build:
    uv build

# Run all tests
test *ARGS:
    uv run pytest {{ARGS}}

# Run tests with coverage report
coverage *ARGS:
    uv run pytest --cov --cov-report=term-missing {{ARGS}}

# Autofix ruff issues and format code
[group('details')]
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Run all linting and type checking tools
[group('details')]
lint: pylint mypy ty

# Run pylint (exit code 8 = warnings only, not errors)
[group('details')]
pylint:
    uv run pylint --fail-under=9.0 src/ test/

# Run mypy type checking (strict)
[group('details')]
mypy:
    uv run mypy src/

# Run ty type checking
[group('details')]
ty:
    uv run ty check

# Show project status
status:
    @echo "Python version:"
    @uv run python --version
    @echo ""
    @echo "Installed packages:"
    @uv tree --outdated
    @echo ""
    @echo "Project info:"
    @uv run pylendar --version
