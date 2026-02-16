# Future Plans

Features missing from pylendar compared to BSD calendar(1) implementations.
See [manpage_comparison.md](manpage_comparison.md) for full details.

## Missing Special Days

- **ChineseNewYear** — First day of the Chinese year (FreeBSD, macOS).

## Missing Date Format

- **Bare month name** — e.g., `June\tEvery June 1st.` should match the
  1st of that month. All four BSDs support this. The parser handles bare
  weekday names but not bare month names.

## Missing CLI Flags

- **`-W num`** — Forward *num* days, skipping weekends (FreeBSD, macOS).
- **`-F friday`** — Configurable "Friday" day number (FreeBSD, macOS).
  Default is 5. Affects both `-W` and the default 3-day look-ahead.
- **`-w`** — Print day-of-week name in front of each event (OpenBSD, Debian).
