# pylendar

A Python port of the classic BSD `calendar(1)` reminder tool. You keep a
plain-text file of dates, and `pylendar` tells you which ones are coming up.

```console
$ pylendar -w -A30
Sun Jun 21*	Summer solstice ☀️
Wed Jul  1	Canada Day 🍁
Sat Jul  4	US Independence Day 🦅
Tue Jul 14	World Emoji Day 🙌
```

## Why it exists

The BSD `calendar` program has been around since Version 7 AT&T UNIX, and the
idea behind it is wonderfully simple: a text file where every line is a date
and a description, and the program prints whatever falls in the next few days.
No database, no sync service, no account to sign up for. Just a file you can
grep, diff, and keep in version control alongside everything else.

That simplicity is exactly why it's still worth using. The catch is that the
BSD variants have drifted apart over the decades. FreeBSD, macOS, OpenBSD,
NetBSD, and Debian each grew their own set of date formats and flags, and none
of them are easy to get running on a modern Linux box or inside a Python
project.

`pylendar` brings the idea back as a single, lightweight Python program that:

- **reads them all.** It understands the date formats from every major BSD
  variant, so calendar files you already have just work.
- **adds a few niceties.** ISO 8601 dates (`2026-02-17`), automatic age
  calculation (`Pat turns [1990]` becomes `Pat turns 36`), and weekday-relative
  dates like `Sun<Dec 25` (the last Sunday before Christmas).
- **gets the astronomy right.** Moon phases, equinoxes, and solstices are
  pinned down precisely with the `astronomy-engine` library instead of the old
  approximation formulas. Easter and the Chinese New Year land on the right day
  every year, too.
- **runs anywhere Python does**, and installs in a single command.

One thing it leaves out on purpose: the BSD `calendar -a` mode, where a daily
cron job runs as root, reads every user's calendar file, and emails each person
their upcoming events. `pylendar` only ever runs as you, on your own files, and
never sends mail. If you want a daily reminder, schedule `pylendar` yourself
with cron or a systemd timer.

## Installing

The fastest way to try it, without installing anything permanently, is with
[`uv`](https://docs.astral.sh/uv/):

```console
$ uvx pylendar
```

To keep it around as a tool on your `PATH`:

```console
$ uv tool install pylendar
```

Or add it to a project:

```console
$ uv add pylendar
```

It also installs with `pip install pylendar`. You'll need Python 3.11 or newer.

## Getting started

Create a starter calendar file with a few commented examples to copy from:

```console
$ pylendar --init
pylendar: starter calendar written to ~/.calendar/calendar
```

Each line is a date, a single tab, and a description:

```
Jan 1	New Year's Day
Jul 4	US Independence Day [1776]
2028-07-14	Start of the LA Olympics
* 15	Mid-month reminder
May/MonSecond	2nd Monday in May
Easter	Easter Sunday
DecSolstice	Winter solstice
```

Add your own dates, then run it:

```console
$ pylendar
```

By default `pylendar` shows today's events, plus the next three days when you
run it on a Friday. A few options worth knowing:

- `-A 30` looks 30 days ahead
- `-w` prints the weekday name in front of each event
- `-t 2026-12-20` pretends it's a different day

Run `pylendar --help` for the full list, or `man pylendar` for the complete
date-format reference.

## Documentation

The [manpage](docs/pylendar.1.md) is the authoritative reference for every
supported date format, command-line option, file-search path, and BSD
compatibility note.

## See also

- [FreeBSD `calendar(1)` man page](https://man.freebsd.org/cgi/man.cgi?calendar)
- [The Debian `bsdmainutils` package](https://packages.debian.org/source/bookworm/bsdmainutils)

## License

BSD 3-Clause. See [LICENSE](LICENSE).
