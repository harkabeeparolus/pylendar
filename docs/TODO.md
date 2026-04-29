# TODO

## Architecture Improvements

### DateExpr: Set Generation vs. Predicate Interface

Currently, `DateExpr.resolve(year)` generates all possible dates matching an expression for a given year (returning a `set[date]`). For wildcard types (like "every day"), this generates up to 366 dates per line. These sets are then intersected with `dates_to_check` (which is typically just 1-3 days depending on `-A` and `-B` flags).

**Proposed Design:**
Refactor `DateExpr` to have a `matches(date: datetime.date) -> bool` interface instead. Checking the 1-3 target days against the rule, rather than generating the whole year's permutations to do a set intersection, changes this from an $O(\text{DaysInYear})$ operation per line to an $O(\text{DatesToCheck})$ operation. This is architecturally cleaner and performant.

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
