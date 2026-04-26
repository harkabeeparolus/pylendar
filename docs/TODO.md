# TODO

## Completed feature notes

These were previously tracked as future plans and are already implemented.
See [manpage_comparison.md](manpage_comparison.md) for the broader BSD
calendar(1) comparison context.

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
