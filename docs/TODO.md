# Future Plans

Features missing from pylendar compared to BSD calendar(1) implementations.
See [manpage_comparison.md](manpage_comparison.md) for full details.
It summarizes key findings from the `*.1.md` manpage reference copies.

## ~~NetBSD wildcard extensions~~ (done)

Implemented: `**`/`* *`, `June*`/`June *`, `*15`, `15 *`.

## ~~`LANG=` locale support~~ (done)

Implemented: `LANG=` directive layers localized month/weekday names
alongside English names via `calendar.different_locale()`. Warns and
falls back if the requested locale is not installed.

## ~~`SEQUENCE=` ordinal localization~~ (done)

Implemented: `SEQUENCE=` directive adds localized ordinal keywords
alongside English ones (`first`–`fifth`, `last`).
