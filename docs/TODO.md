# TODO

## Active

### Redesign `OffsetDateExpr.variable` to drop type-ignore suppressions

`OffsetDateExpr.variable` is a `@property` overriding a `ClassVar[bool]` on
the `DateExpr` base class. This requires a `# type: ignore[override]` for
mypy and a `# pyright: ignore[reportIncompatibleVariableOverride]` (or a
module-wide silence) for basedpyright.

Investigate whether the `variable` API can be redesigned so that delegation
in `OffsetDateExpr` no longer triggers an incompatible-override diagnostic.
Sketches:

- Convert `variable` to a method (e.g. `is_variable()`) on all `DateExpr`
  subclasses — uniform method override, no ClassVar/property conflict.
- Set `variable` as a frozen instance attribute in `__post_init__` via
  `object.__setattr__`, with a matching field declaration.
- Make `variable` a `@property` on the base class too, so all overrides are
  property-to-property.

Tradeoff: invasive change to a load-bearing class hierarchy (~6 subclasses)
for the benefit of removing two suppression comments.

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
