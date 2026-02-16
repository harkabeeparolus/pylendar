# BSD calendar(1) Manpage Comparison

Comparison of four implementations of the `calendar(1)` utility.

## General

| | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **Manpage date** | Dec 17, 2023 | Dec 17, 2023 | Feb 21, 2025 | Jun 1, 2016 | Jan 29, 2019 |
| **Version** | macOS 26.3 | FreeBSD 15.0 | OpenBSD-current | NetBSD 10.1 | bsdmainutils 12.1.8 |
| **Lineage** | FreeBSD fork | — | independent | independent | OpenBSD fork |
| **Preprocessor** | internal limited cpp | internal limited cpp | external cpp(1) | external cpp(1) | external cpp(1) |
| **`//` comments** | yes | yes | no | no | no |
| **`CALENDAR_DIR` env var** | no | no | yes | yes | yes |

## Command-Line Options

| Flag | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **`-A` *num*** | forward *num* days | forward *num* days | forward *num* days | — | forward *num* days |
| **`-a`** | mail all users | mail all users | mail all users | mail all users | mail all users |
| **`-B` *num*** | backward *num* days | backward *num* days | backward *num* days | — | backward *num* days |
| **`-b`** | — | — | Cyrillic mode | — | Cyrillic mode |
| **`-D` *moon\|sun*** | lunar/solar info | lunar/solar info | — | — | — |
| **`-d`** | debug date info | debug date info | — | — | — |
| **`-e` *num*** | — | — | — | — | Friday-only look-ahead |
| **`-F` *friday*** | set "Friday" day | set "Friday" day | — | — | — |
| **`-f` *file*** | calendar file | calendar file | calendar file | calendar file | calendar file |
| **`-l`** | longitude | longitude | — | look-ahead days | look-ahead days |
| **`-t`** | `dd[.mm[.year]]` | `dd[.mm[.year]]` | `[[[cc]yy]mm]dd` | — | `[[[cc]yy]mm]dd` |
| **`-d` *date*** | — | — | — | `MMDD[[YY]YY]` | — |
| **`-U` *offset*** | UTC offset | UTC offset | — | — | — |
| **`-v`** | — | — | — | print version | — |
| **`-W` *num*** | forward, skip weekends | forward, skip weekends | — | — | — |
| **`-w`** | — | — | print weekday name | extra Friday days | print weekday name |
| **`-x`** | — | — | — | no `CPP_RESTRICTED` | — |

## Date Format Features

| Feature | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **`*` (every month)** | yes | yes | yes | yes | yes |
| **`**` (every day)** | — | — | — | yes | — |
| **`*15` (15th monthly)** | — | — | — | yes | — |
| **`June*` (every day of month)** | — | — | — | yes | — |
| **`YYYY/M/D` dates** | yes | yes | — | — | — |
| **Ordinal weekdays** (`Sun+2`, `SunLast`) | yes | yes | yes | — | yes |

## Special Days

| Special day | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **Easter** | yes | yes | yes | — | yes |
| **Paskha** | yes | yes | yes | — | yes |
| **NewMoon** | yes | yes | — | — | — |
| **FullMoon** | yes | yes | — | — | — |
| **MarEquinox** | yes | yes | — | — | — |
| **JunSolstice** | yes | yes | — | — | — |
| **SepEquinox** | yes | yes | — | — | — |
| **DecSolstice** | yes | yes | — | — | — |
| **ChineseNewYear** | yes | yes | — | — | — |

## Calendar File Variables

| Variable | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **`LANG=`** | yes | yes | yes | — | yes |
| **`SEQUENCE=`** | yes | yes | — | — | — |
| **`Easter=`** (rename) | yes | yes | yes | — | yes |
| **`Paskha=`** (rename) | yes | yes | yes | — | yes |
| **`CALENDAR=`** (Julian/Gregorian) | — | — | yes | — | yes |
| **`BODUN=`** (Cyrillic) | — | — | yes | — | yes |
| **`RECIPIENT_EMAIL=`** | — | — | yes | — | — |
| **`utf-8` pseudo-locale** | — | — | — | — | yes |

## Preprocessor Directives

| Directive | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **`#include`** | yes | yes | yes (via cpp) | yes (via cpp) | yes (via cpp) |
| **`#define`** | yes | yes | yes (via cpp) | yes (via cpp) | yes (via cpp) |
| **`#undef`** | yes | yes | yes (via cpp) | yes (via cpp) | yes (via cpp) |
| **`#ifdef`** | yes | yes | yes (via cpp) | yes (via cpp) | yes (via cpp) |
| **`#ifndef`** | yes | yes | yes (via cpp) | yes (via cpp) | yes (via cpp) |
| **`#else`** | yes | yes | yes (via cpp) | yes (via cpp) | yes (via cpp) |
| **`#warning`** | yes | yes | — | — | — |
| **`#error`** | yes | yes | — | — | — |

Note: macOS/FreeBSD implement a limited cpp internally; OpenBSD, NetBSD,
and Debian invoke the external cpp(1) preprocessor (which supports the
full directive set).

## File Search Paths

| Path | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **current directory** | 1st | 1st | 1st | 1st | 1st |
| **`~/calendar`** | — | — | — | 1st | — |
| **`~/.calendar`** | 2nd | 2nd | 2nd | 2nd | 2nd |
| **`/etc/calendar`** | — | — | — | 3rd | — |
| **`/usr/local/share/calendar`** | 3rd | 3rd | — | — | — |
| **`/usr/share/calendar`** | 4th | 4th | fallback | fallback | fallback |

## Bundled Calendar Files

| File | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| *calendar.all* | — | yes | yes | — | yes |
| *calendar.australia* | — | yes | — | — | — |
| *calendar.birthday* | — | yes | yes | yes | yes |
| *calendar.canada* | — | — | yes | — | yes |
| *calendar.christian* | — | yes | yes | yes | yes |
| *calendar.computer* | — | yes | yes | yes | yes |
| *calendar.croatian* | — | yes | yes | — | yes |
| *calendar.discord* | — | — | yes | — | yes |
| *calendar.dutch* | — | yes | — | — | — |
| *calendar.fictional* | — | — | yes | — | yes |
| *calendar.freebsd* | — | yes | — | — | — |
| *calendar.french* | — | yes | yes | — | yes |
| *calendar.german* | — | yes | yes | — | yes |
| *calendar.history* | — | yes | yes | yes | yes |
| *calendar.holiday* | — | yes | yes | yes | yes |
| *calendar.judaic* | — | yes | yes | yes | yes |
| *calendar.lotr* | — | — | — | yes | — |
| *calendar.music* | — | yes | yes | yes | yes |
| *calendar.netbsd* | — | — | — | yes | — |
| *calendar.newzealand* | — | yes | — | — | — |
| *calendar.nz* | — | — | yes | — | yes |
| *calendar.openbsd* | — | — | yes | — | yes |
| *calendar.pagan* | — | — | yes | — | yes |
| *calendar.russian* | — | yes | yes | — | yes |
| *calendar.southafrica* | — | yes | — | — | — |
| *calendar.space* | — | — | yes | — | yes |
| *calendar.uk* | — | — | yes | — | yes |
| *calendar.ushistory* | — | — | yes | — | yes |
| *calendar.usholiday* | — | yes | yes | yes | yes |
| *calendar.world* | — | yes | yes | — | yes |

Note: macOS does not document bundled calendar files in its manpage.

## Manpage Sections

| Section | macOS | FreeBSD | OpenBSD | NetBSD | Debian |
|---|---|---|---|---|---|
| **FILE FORMAT** | yes (separate) | yes (separate) | no (in DESCRIPTION) | no (in DESCRIPTION) | no (in DESCRIPTION) |
| **COMPATIBILITY** | yes | yes | — | yes | yes |
| **STANDARDS** | — | — | yes | — | yes |
| **NOTES** | yes | yes | — | — | — |
