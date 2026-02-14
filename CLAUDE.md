# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pylendar is a Python port of the BSD `calendar(1)` utility. It parses calendar files and displays upcoming relevant dates within a configurable date range.

## Build and Development Commands

Uses `uv` for package management, `ruff` + `pylint` for linting, and `mypy` (strict) + `ty` for type checking. Run pylint on both `src/` and `test/`. A `Justfile` is provided for convenience (`just check` runs everything).

```bash
uv sync                  # install to venv
ruff check --fix         # linting
uv run pylint src test   # linting
ruff format              # format source code
uv run mypy src          # type checking (strict mode)
uv run ty check          # type checking
uv run pylendar          # run pylendar CLI
```

## Architecture

The codebase is intentionally a single file (`src/pylendar/pylendar.py`, ~600 lines) so it could be used as a standalone script in the future, via PEP 723 inline script metadata. But during development we build it as a normal Python package.

Three main components:

### Core Classes

- **Event** - Dataclass representing a calendar event (date + description), implements date-based sorting
- **DateStringParser** - Parses date strings supporting multiple formats: MM/DD, "Month DD", wildcard "* DD", and special dates like Easter
- **SimpleCPP** - C/C++ preprocessor emulator that handles `#include` directives and removes C-style comments from calendar files

### Main Flow

`main()` → `cli()` → find calendar file → preprocess with SimpleCPP → parse special dates → calculate date range → collect matching events → sort → output

### Key Behaviors

- **Friday logic**: Default "ahead" is 3 days on Fridays, 1 day otherwise
- **Age calculation**: `[YYYY]` syntax in events calculates and displays age
- **BSD compatibility**: Searches default paths (~/.calendar, XDG_CONFIG_HOME/calendar, /etc/calendar, etc.)

## Testing

Tests are in `test/` directory:

- `test_cpp.py` - SimpleCPP preprocessor tests (includes, circular detection)
- `test_ahead_behind.py` - Date range calculation with Friday special cases
- `test_date_sorting_e2e.py` - Integration tests for event sorting with mixed date formats

## Linting and Type Checking

Ruff is configured with strict "ALL" rules. Pylint runs on both `src/` and `test/` directories. Both allow f-string interpolation in logging. Mypy runs in strict mode; ty is also used. Type stubs for `astronomy-engine` are in `typings/`.
