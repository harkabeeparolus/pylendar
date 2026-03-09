---
title: PYLENDAR
section: 1
header: General Commands Manual
date: March 2026
footer: pylendar 0.5.0
---
<!-- markdownlint-disable single-h1 -->

# NAME

**pylendar**, **calendar** — Python port of the BSD calendar(1) utility

# SYNOPSIS

**pylendar**
\[**-A** *num* | **-W** *num*]
\[**-B** *num*]
\[**-D** *sun|moon*]
\[**-F** *friday*]
\[**-f** *calendarfile*]
\[**-l** *longitude*]
\[**-t** *date*]
\[**-U** *utc-offset*]
\[**-V**]
\[**-v**]
\[**-w**]

# DESCRIPTION

The **pylendar** utility is a Python reimplementation of the BSD
**calendar**(1) command. It checks the current directory for a file named
*calendar* and displays lines that fall into the specified date range.
On the day before a weekend (normally Friday), events for the next three
days are displayed.

The program may be invoked as either **pylendar** or **calendar**.

The following options are available:

**-A** *num*
: Print lines from today and the next *num* business days (forward,
  future). Weekend days following "Friday" are included for free (they
  do not count against *num*). Default is 1, except on Fridays when the
  default is 3. **-A** and **-W** are mutually exclusive.

**-B** *num*
: Print lines from today and the previous *num* days (backward, past).
  Default 0.

**-D** *sun|moon*
: Print diagnostic sun or moon information and exit.

**-F** *friday*
: Set which day of the week is "Friday" (the day before the weekend
  begins). Day numbering follows BSD **tm_wday** convention: 0=Sun,
  1=Mon, ..., 5=Fri, 6=Sat. Default is 5.

**-f** *calendarfile*
: Use *calendarfile* as the default calendar file.

**-l** *longitude*
: East longitude for lunar and solar calculations. If neither longitude
  nor UTC offset is specified, the value is derived from the system
  timezone. If both are specified, UTC offset overrides longitude.

**-t** *date*
: Act like the specified value is "today" instead of using the current
  date. Accepts both FreeBSD format *dd*\[.*mm*\[.*year*]] and
  OpenBSD/Debian format \[[[*cc*]*yy*]*mm*]*dd*. If *yy* is between 69
  and 99, *cc* defaults to 19; otherwise 20. Also accepts ISO 8601
  *YYYY-MM-DD* format.

**-U** *utc-offset*
: UTC offset in hours (e.g., -8 for PST, 1 for CET). If neither UTC
  offset nor longitude is specified, the value is derived from the
  system timezone. If both are specified, UTC offset overrides longitude.

**-V**, **--version**
: Print version information and exit.

**-v**, **--verbose**
: Increase verbosity (can be used multiple times).

**-W** *num*
: Print lines from today and the next *num* calendar days (forward,
  future). No Friday/weekend expansion is applied.
  **-A** and **-W** are mutually exclusive.

**-w**
: Print the day of the week name in front of each event. Follows the
  OpenBSD/Debian convention (not NetBSD, where **-w** means extra
  Friday days).

# FILE FORMAT

## Directives

To handle calendars in a national locale, specify `LANG=<locale_name>`
in the calendar file as early as possible.

To provide local names for ordinal sequences, specify:
`SEQUENCE=<first> <second> <third> <fourth> <fifth> <last>`
in the calendar file as early as possible.

## Special Date Names

The following special date names are recognized:

| Name | Description |
|---|---|
| Easter | Catholic Easter. |
| Paskha | Orthodox Easter. |
| NewMoon | The lunar New Moon. |
| FullMoon | The lunar Full Moon. |
| MarEquinox | The solar equinox in March. |
| JunSolstice | The solar solstice in June. |
| SepEquinox | The solar equinox in September. |
| DecSolstice | The solar solstice in December. |
| ChineseNewYear | The first day of the Chinese year. |

These names may be reassigned to their local names via an assignment
like `Easter=Pasen` in the calendar file.

The names of the recognized special dates may be followed by a positive
or negative integer offset, like: `Easter+3` or `Paskha-4`.

## Date Formats

Lines should begin with a date specification, followed by a tab
character, followed by the event description. The following date formats
are supported:

**Fixed dates:**

- *MM/DD* — e.g., `07/09`
- *Month DD* — e.g., `Jul 9`, `July 9`
- *DD Month* — e.g., `01 Jan`
- *Month/DD* — e.g., `apr/01`
- *YYYY/M/D* — e.g., `2026/2/17` (specific year)
- *YYYY-MM-DD* — e.g., `2026-02-17` (ISO 8601; pylendar extension)

**Recurring and wildcard dates:**

- *\* DD* — DDth of every month (e.g., `* 15`)
- *DD \** — DDth of every month, reversed (e.g., `15 *`)
- *\*\** or *\* \** — every day of the year
- *Month\** or *Month \** — every day of that month (e.g., `June*`)
- *Month* (alone) — the 1st of that month
- *Weekday* (alone) — every occurrence of that weekday (e.g., `Friday`)

**Weekday-based dates:**

- *Month Wkday+N* — Nth weekday of a month (e.g., `May Sun+2`)
- *Month Wkday-N* — last Nth weekday of a month (e.g., `May Mon-1`)
- *MM/Wkday+N* — Nth weekday of numbered month (e.g., `03/Sun-1`)
- *MM/WkdayOrd* — using ordinal names (e.g., `10/MonSecond`)
- *Month/WkdayOrd* — with optional day offset (e.g., `Oct/SatFourth-2`)
- *\* Wkday+N* — Nth weekday of every month (e.g., `* Fri+3`)
- *WkdayOrd Month* — ordinal weekday then month (e.g., `SunFirst Aug`)
- *Wkday>Month DD* — weekday strictly after a date (e.g., `Sat>Jun 19`)
- *Wkday<Month DD* — weekday strictly before a date (e.g., `Sun<Dec 25`)
- *Wkday>DD Month* — same, with day before month (e.g., `Sat>19 Jun`)
- *Wkday<DD Month* — same, with day before month
- *Wkday>MM/DD* — same, with numeric month (e.g., `Sat>06/19`)
- *Wkday<MM/DD* — same, with numeric month

The anchor date may include an offset in days: `Sun<Dec 25-7` means
"Sunday before December 18" (i.e., the anchor is shifted by -7 days
before the weekday search). The anchor date itself is never matched
(strict before/after). This is a pylendar extension.

Weekdays may use the ordinal names First, Second, Third, Fourth, Fifth,
and Last.

**Special dates:**

- *Easter*, *Paskha*, *ChineseNewYear*, etc.
- *Special+/-N* — offset from a special date (e.g., `Easter-2`)

## Age Syntax

If an event description contains a four-digit year in square brackets
(e.g., `[1990]`), **pylendar** replaces it with the calculated age
(current year minus that year). This is a pylendar extension not found
in any BSD implementation.

## Other Conventions

By convention, dates followed by an asterisk ("\*") are not fixed, i.e.,
they change from year to year.

Day descriptions start after the first tab character in the line; if the
line does not contain a tab character, it is not displayed. If the first
character in the line is a tab character, it is treated as a continuation
of the previous line.

# PREPROCESSOR

The calendar file is preprocessed by **SimpleCPP**, a limited internal
preprocessor that handles **#include** directives and strips C-style
comments (`/* ... */` and `//`). The `//` form is only recognized at the
beginning of a line or after whitespace, so that URLs in calendar entries
are preserved.

If an included file is not referenced by a full pathname, **pylendar**
searches for it using the same order of precedence described in
[FILES](#files).

When an `#include` path begins with a bare locale name (e.g.,
`uk_UA/calendar.all`), **pylendar** falls back to matching directories
with an encoding suffix (e.g., `uk_UA.KOI8-U/`). UTF-8 directories are
preferred when multiple encodings exist. This allows BSD calendar
collections that use bare locale names in their includes to work
without renaming directories.

Included files must be valid UTF-8. Files that cannot be decoded as
UTF-8 are skipped with a warning.

Files are included at most once (once-only inclusion), so include guards
are not needed.

Other preprocessor directives (`#define`, `#ifdef`, `#ifndef`, `#else`,
`#endif`, `#undef`, `#warning`, `#error`) are silently ignored. This is
a deliberate design choice: no real-world calendar files use these
directives beyond include guards, which are already handled by the
once-only inclusion behavior.

# FILES

| Path | Description |
|---|---|
| *calendar* | File in the current directory. |
| *~/.calendar* | Calendar home directory. |
| *$XDG_CONFIG_HOME/calendar* | XDG calendar directory (pylendar extension). |
| */etc/calendar* | System-wide calendar directory. |
| */usr/share/calendar* | System-wide shared calendar files. |
| */usr/local/share/calendar* | Locally installed calendar files. |

The default search order when looking for a calendar file is: current
directory, ~/.calendar, $XDG_CONFIG_HOME/calendar, /etc/calendar,
/usr/share/calendar, /usr/local/share/calendar. The **-f** option or the
**CALENDAR_DIR** environment variable override this search.

# ENVIRONMENT

**CALENDAR_DIR**
: If set, use this directory to find the calendar file. Supported for
  compatibility with OpenBSD, NetBSD, and Debian.

**XDG_CONFIG_HOME**
: Base directory for user configuration. **pylendar** searches
  *$XDG_CONFIG_HOME/calendar* as part of the default search path.
  Defaults to *~/.config* if not set. This is a pylendar extension.

# COMPATIBILITY

**pylendar** aims for broad compatibility with BSD **calendar**(1)
implementations (FreeBSD, macOS, OpenBSD, NetBSD, and Debian). The
following differences exist:

**-A / -W semantics match macOS/FreeBSD**
: **-A** counts business days, expanding weekends for free (matching
  macOS/FreeBSD). **-W** counts plain calendar days with no expansion
  (also matching macOS/FreeBSD). The default (no flag) matches all
  implementations.

**No -a or -d options**
: The **-a** flag (mail all users) is intentionally not implemented.
  Email delivery is out of scope. The **-d** flag (debug date info)
  is not implemented; use **-v** for verbose output instead.

**Age \[YYYY] syntax**
: The `[YYYY]` age calculation in event descriptions is a pylendar
  addition not found in any BSD implementation.

**Preprocessor: #include only**
: **pylendar** processes only **#include** directives and C-style
  comments. Other preprocessor directives are silently ignored.
  Once-only inclusion eliminates the need for include guards.

**astronomy-engine for precise calculations**
: Lunar and solar calculations use the **astronomy-engine** library
  for precise results, rather than the BSD approximation formulas.

**XDG_CONFIG_HOME**
: Added to the default calendar file search paths (not in any BSD).

**ISO 8601 date format**
: *YYYY-MM-DD* date format is accepted (not in any BSD).

**-t accepts multiple formats**
: Accepts both FreeBSD (*dd.mm[.year]*) and OpenBSD/Debian
  (*[[[cc]yy]mm]dd*) formats, as well as ISO 8601.

**-w follows OpenBSD/Debian**
: Prints weekday name in front of each event, following the
  OpenBSD/Debian convention. NetBSD uses **-w** to mean extra Friday
  look-ahead days.

**Once-only inclusion**
: Included files are automatically processed at most once. No include
  guards are needed, unlike BSD implementations that use **cpp**(1).

**Weekday before/after date**
: The *Wkday>Date* and *Wkday<Date* syntax for finding the nearest
  weekday strictly after or before a fixed date is a pylendar extension
  not found in any BSD implementation.

**NetBSD extensions**
: Supports NetBSD date format extensions (DD \*, \*\*, Month\*) alongside
  FreeBSD/macOS features.

# SEE ALSO

cal(1)

# HISTORY

The **calendar** command first appeared in Version 7 AT&T UNIX.
**pylendar** is a Python reimplementation supporting features from
FreeBSD, macOS, OpenBSD, NetBSD, and Debian variants.

# AUTHORS

Fredrik Mellström
