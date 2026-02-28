# Future Plans

Features missing from pylendar compared to BSD calendar(1) implementations.
See [manpage_comparison.md](manpage_comparison.md) for full details.
It summarizes key findings from the `*.1.md` manpage reference copies.

## Fix `-W` to skip weekends

Currently `-W num` behaves like `-A num` (counts calendar days). The
macOS/FreeBSD spec says `-W` should count only weekdays (business days),
so `-W 5` means 5 business days ahead, potentially spanning 7+ calendar
days. Also disables Friday look-ahead expansion.

## `CALENDAR_DIR` environment variable

OpenBSD, NetBSD, and Debian check the `CALENDAR_DIR` environment variable
for the calendar directory before falling back to the default search path.
Add to `find_calendar()`.

## `--version` flag

Standard CLI practice. NetBSD uses `-v` for this; we use `-v` for verbose,
so add as `-V/--version` only.

## NetBSD wildcard extensions

Three additional wildcard date patterns from NetBSD:

- `**` — every day of the year
- `June*` — every day of a specific month (month name immediately followed by `*`)
- `*15` — 15th of every month (no space, unlike existing `* 15`)

## `LANG=` locale support

Global directive, set once at the top of the main calendar file (before
`#include` lines), as specified by macOS, FreeBSD, OpenBSD, and Debian.
Merges localized month and weekday names into `DateStringParser`'s maps
**alongside** English names, which are always kept — so OS-provided
English calendar files continue to work when a non-English locale is
active. Uses Python's `calendar.different_locale()`. Should warn and fall
back gracefully if the requested locale is not installed on the OS.

## `SEQUENCE=` ordinal localization

macOS/FreeBSD feature. Allows renaming ordinal keywords (`first`,
`second`, `third`, `fourth`, `fifth`, `last`) to local equivalents via a
space-separated list. Global directive like `LANG=`. Updates
`ORDINAL_MAP`.
