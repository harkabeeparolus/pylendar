# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pylendar is a Python port of the BSD `calendar(1)` utility. It parses calendar files and displays upcoming relevant dates within a configurable date range. The manpage source (`docs/pylendar.1.md`) is the authoritative reference for supported date formats, CLI options, file format, and compatibility notes.

## Build and Development Commands

Uses `uv` for package management, `ruff` + `pylint` for linting, and `mypy` (strict) + `ty` + `basedpyright` for type checking. Run pylint on both `src/` and `test/`. A `Justfile` is provided for convenience; run `just check` after every complete code change.

```bash
uv sync                  # install to venv
just check               # lint, autofix, format, typecheck, and test
just test -v test/test_foo.py  # run pytest with optional flags
just coverage -v         # run pytest with --cov, and any other optional flags
uv run pylendar          # run pylendar CLI
just build_man           # build manpage (requires pandoc)
```

## Design

This command tries to be compatible with old versions. Copies of various manpages are available in `docs/*.1.md`. There is a comparison in `docs/manpage_comparison.md`.

There is test data from FreeBSD default calendar files in the `calendars/` subdirectory.

## Architecture

The codebase is intentionally a single file (`src/pylendar/pylendar.py`, ~1400 lines) so it could be used as a standalone script in the future, via PEP 723 inline script metadata. But during development we build it as a normal Python package.

Three main components:

### Core Classes

- **Event** - Dataclass representing a calendar event (date + description), implements date-based sorting
- **DateStringParser** - Parses date strings in several categories: fixed dates (MM/DD, "Month DD", ISO 8601), recurring/wildcard patterns, weekday-based expressions, and special dates (Easter, solstices, moon phases, etc.). See `docs/pylendar.1.md` for the complete list.
- **SimpleCPP** - C/C++ preprocessor emulator that handles `#include` directives and removes C-style comments from calendar files

### Main Flow

`main()` → `cli()` → find calendar file → preprocess with SimpleCPP → parse special dates → calculate date range → collect matching events → sort → output

### Key Behaviors

- **Friday logic**: Default "ahead" is 3 days on Fridays, 1 day otherwise
- **Age calculation**: `[YYYY]` syntax in events calculates and displays age
- **BSD compatibility**: Searches default paths (~/.calendar, XDG_CONFIG_HOME/calendar, /etc/calendar, etc.)

## Testing

Tests use bare functions (no classes). Group related tests with `# --- section name ---` comment banners. Encode context that a class name would have provided into the function name prefix instead (e.g. `test_replace_age_*`, `test_seasons_*`).

Tests are in `test/` directory:

- `test_astronomical.py` - Astronomical special dates (moon phases and seasons)
- `test_cpp.py` - SimpleCPP preprocessor tests (includes, circular detection, edge cases)
- `test_date_sorting_e2e.py` - Integration tests for event sorting with mixed date formats, plus unit-level edge cases (age replacement, Event comparison, impossible dates, unparseable lines)
- `test_directives.py` - LANG= and SEQUENCE= directive parsing, special-date aliases, DateStringParser edge cases
- `test_find_calendar.py` - Calendar file discovery, CALENDAR_DIR support, and fallback paths
- `test_friday_weekend_flags.py` - -F (friday) and -W (weekend-ignore) flags
- `test_longitude_utc.py` - UTC offset, longitude, and astronomical date flags
- `test_parse_today.py` - -t flag date parsing (various formats)
- `test_weekday_relative.py` - `Wkday<Date` / `Wkday>Date` weekday-relative-to-date syntax
- `test_weekday_flag.py` - -w (weekday) flag output formatting

Coverage is at 97% with branch coverage enabled. Untestable boilerplate (dependency `ImportError` guards, `KeyboardInterrupt` handler, `if __name__ == "__main__"`, and the `utcoffset() is None` fallback) is marked `# pragma: no cover`.

## Linting and Type Checking

Ruff is configured with strict "ALL" rules. Pylint runs on both `src/` and `test/` directories. Both allow f-string interpolation in logging. Mypy runs in strict mode; ty and basedpyright (in `"all"` mode) also run. Type stubs for `astronomy-engine` are in `typings/`.

## Manpage

The pylendar manpage source is `docs/pylendar.1.md` in Pandoc GFM Markdown format
with YAML front matter. Run `just build_man` to convert it to troff format at
`share/man/man1/pylendar.1` using pandoc. The built manpage is included in the
wheel via hatchling shared-data and is not checked into git.

When adding or changing command-line options, date format support, file search
paths, or other user-visible behavior, update `docs/pylendar.1.md` to match.
When bumping the version, update the `footer` field in the YAML front matter.

## Releasing

1. Update `footer` in `docs/pylendar.1.md` to the new version
2. Bump `__version__` in `src/pylendar/pylendar.py`
3. `just check` — must pass
4. Commit with message `Version X.Y.Z`
5. `git tag vX.Y.Z && git push && git push --tags`
6. Create a **draft** GitHub release from the tag (`gh release create vX.Y.Z --draft`)
   — Do not publish the release, because it would trigger CI → PyPI. A human will do this manually.

### Release notes style

Use a few emojis in section headings to match prior releases (e.g. 🛠️ 🐛 ✨ 🗓️ 🚀 📚).
Draft the notes technically, then run `/humanizer` on the text before publishing
to make it clear and friendly to a general audience.
