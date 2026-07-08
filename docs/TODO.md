# TODO

## Pending

### 1.0 release

When releasing 1.0, flip the PyPI classifier in `pyproject.toml` from
`Development Status :: 4 - Beta` to `Development Status :: 5 -
Production/Stable`, in addition to the usual release checklist in
CLAUDE.md.

## Out of scope

### Full cpp directive support (`#define`, `#ifdef`, `#ifndef`, `#undef`, `#else`)

Permanently out of scope, until and unless someone demonstrates a real,
practical use case. SimpleCPP stays as simple as possible: `#include`
plus C-style comment stripping. No calendar collections observed in the
wild use cpp directives for anything other than include guards, and
those are already covered by SimpleCPP's once-only inclusion behavior
(see the PREPROCESSOR section of the manpage). Other directives are
silently ignored.

### Niche OpenBSD/Debian extensions

Also permanently out of scope, absent a demonstrated practical use case:

- **`CALENDAR=`** (Julian/Gregorian calendar switching; OpenBSD, Debian)
- **`BODUN=`** and the **`-b`** flag (Cyrillic "Old New Year" mode;
  OpenBSD, Debian) — already declared unsupported in the manpage
- **`RECIPIENT_EMAIL=`** (OpenBSD) — belongs with the `-a` mail mode,
  which is already out of scope: pylendar runs as the current user only
  and never sends email

Debian's **`utf-8` pseudo-locale** ("dates in the C locale,
descriptions in UTF-8") needs no work: `LANG=utf-8` is already in the
locale-skip set and is silently treated as the C locale, which matches
Debian semantics since pylendar input must be UTF-8 anyway.

## Completed feature notes

These were previously tracked as future plans and are already implemented.
See [manpage_comparison.md](manpage_comparison.md) for the broader BSD
calendar(1) comparison context.

## ~~DateExpr: set generation vs. predicate interface~~ (done)

Implemented in a45633f: `DateExpr.matches(date) -> bool` is now the
membership predicate the event-collection hot path uses, replacing the
per-line whole-year `resolve(year)` set intersection (up to 366 dates per
line) with an $O(\text{DatesToCheck})$ check against the 1-3 target days.
`resolve(year)` is kept for the `-t`/`resolve_today` enumeration path,
which has no candidate date in hand; a consistency test guards against
`matches`/`resolve` drift.

## ~~NetBSD wildcard extensions~~ (done)

Implemented: `**`/`* *`, `June*`/`June *`, `*15`, `15 *`.

## ~~`LANG=` locale support~~ (done)

Implemented: `LANG=` directive layers localized month/weekday names
alongside English names via `calendar.different_locale()`. Warns and
falls back if the requested locale is not installed.

## ~~`SEQUENCE=` ordinal localization~~ (done)

Implemented: `SEQUENCE=` directive adds localized ordinal keywords
alongside English ones (`first`–`fifth`, `last`).

## ~~Weekdays before/after certain dates~~ (done)

Implemented: `Wkday>Date` and `Wkday<Date` operator syntax finds the
nearest weekday strictly after or before a fixed anchor date. Anchor
formats: `Month DD`, `MM/DD`. Optional `+/-N` day offset adjusts the
anchor before the weekday search. Examples: `Sat>Jun 19` (Midsummer's
Eve), `Sun<Dec 25` (Fourth Advent), `Sun<Dec 25-7` (Third Advent).
