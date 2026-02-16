# Future Plans

Features missing from pylendar compared to BSD calendar(1) implementations.
See [manpage_comparison.md](manpage_comparison.md) for full details.

## Missing CLI Flags

- **`-W num`** — Forward *num* days, skipping weekends (FreeBSD, macOS).
- **`-F friday`** — Configurable "Friday" day number (FreeBSD, macOS).
  Default is 5. Affects both `-W` and the default 3-day look-ahead.
