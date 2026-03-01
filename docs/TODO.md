# Future Plans

Features missing from pylendar compared to BSD calendar(1) implementations.
See [manpage_comparison.md](manpage_comparison.md) for full details.
It summarizes key findings from the `*.1.md` manpage reference copies.

## ~~NetBSD wildcard extensions~~ (done)

Implemented: `**`/`* *`, `June*`/`June *`, `*15`, `15 *`.

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
