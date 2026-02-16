---
title: CALENDAR
section: 1
header: General Commands Manual
date: February 21, 2025
footer: OpenBSD-current
---

## NAME

**calendar** — reminder service

## SYNOPSIS

**calendar**
\[**-abw**]
\[**-A** *num*]
\[**-B** *num*]
\[**-f** *calendarfile*]
\[**-t** \[\[\[*cc*]*yy*]*mm*]*dd*]

## DESCRIPTION

The **calendar** utility checks the current directory or the directory
specified by the `CALENDAR_DIR` environment variable for a file named
*calendar* and displays lines that begin with either today's date or
tomorrow's. On Fridays, events on Friday through Monday are displayed.

The options are as follows:

**-A** *num*
: Print lines from today and the next *num* days (forward, future).

**-a**
: Process the "calendar" files of all users and mail the results to
  them. This requires superuser privileges.

**-B** *num*
: Print lines from today and the previous *num* days (backward, past).

**-b**
: Enforce special date calculation mode for Cyrillic calendars.

**-f** *calendarfile*
: Use *calendarfile* as the default calendar file.

**-t** \[\[\[*cc*]*yy*]*mm*]*dd*
: Act like the specified value is "today" instead of using the current
  date. If *yy* is specified, but *cc* is not, a value for *yy*
  between 69 and 99 results in a *cc* value of 19. Otherwise, a *cc*
  value of 20 is used.

**-w**
: Print day of the week name in front of each event.

To handle calendars in your national code table you can specify
`LANG=<locale_name>` in the calendar file as early as possible. To
handle national Easter names in the calendars, `Easter=<national_name>`
(for Catholic Easter) or `Paskha=<national_name>` (for Orthodox Easter)
can be used.

The `CALENDAR` variable can be used to specify the style. Only "Julian"
and "Gregorian" styles are currently supported. Use `CALENDAR=` to
return to the default (Gregorian).

The `RECIPIENT_EMAIL` variable can be used to specify the recipient of
daily mails.

To enforce special date calculation mode for Cyrillic calendars you
should specify `LANG=<local_name>` and `BODUN=<bodun_prefix>` where
\<local_name> can be ru_RU.UTF-8, uk_UA.UTF-8 or by_BY.UTF-8.

Other lines should begin with a month and day. They may be entered in
almost any format, either numeric or as character strings. If proper
locale is set, national months and weekdays names can be used. A single
asterisk ("\*") matches every month. A day without a month matches that
day of every week. A month without a day matches the first of that
month. Two numbers default to the month followed by the day. Lines with
leading tabs default to the last entered date, allowing multiple line
specifications for a single date. "Easter" (may be followed by a
positive or negative integer) is Easter for this year. "Paskha" (may be
followed by a positive or negative integer) is Orthodox Easter for this
year. Weekdays may be followed by `-4` ... `+5` (aliases last, first,
second, third, fourth) for moving events like "the last Monday in
April".

By convention, dates followed by an asterisk ("\*") are not fixed, i.e.,
change from year to year.

Day descriptions start after the first \<tab> character in the line; if
the line does not contain a \<tab> character, it is not displayed. If the
first character in the line is a \<tab> character, it is treated as a
continuation of the previous description.

The **calendar** file is preprocessed by cpp(1), allowing the inclusion
of shared files such as company holidays or meetings. If the shared file
is not referenced by a full pathname, cpp(1) searches in the current (or
home) directory first, and then in the directory */usr/share/calendar*.
Empty lines and lines protected by the C commenting syntax `/* ... */`
are ignored.

Some possible calendar entries (\<tab> characters highlighted by `\t`
sequence):

```
LANG=C
Easter=Ostern

#include <calendar.usholiday>
#include <calendar.birthday>

6/15\tJune 15 (if ambiguous, will default to month/day).
Jun. 15\tJune 15.
15 June\tJune 15.
Thursday\tEvery Thursday.
June\tEvery June 1st.
15 *\t15th of every month.

May Sun+2\tsecond Sunday in May (Muttertag)
04/SunLast\tlast Sunday in April,
\tsummer time in Europe
Easter\tEaster
Ostern-2\tGood Friday (2 days before Easter)
Paskha\tOrthodox Easter
```

## FILES

| Path | Description |
|---|---|
| *calendar* | file in current directory. |
| *~/.calendar* | directory in the user's home directory (which **calendar** changes into, if it exists). |
| *~/.calendar/calendar* | calendar file to use if no calendar file exists in the current directory. |
| *~/.calendar/nomail* | **calendar** will not send mail if this file exists. |
| *calendar.all* | international and national calendar files. |
| *calendar.birthday* | births and deaths of famous (and not-so-famous) people. |
| *calendar.canada* | Canadian holidays. |
| *calendar.christian* | Christian holidays (should be updated yearly by the local system administrator so that roving holidays are set correctly for the current year). |
| *calendar.computer* | days of special significance to computer people. |
| *calendar.croatian* | Croatian calendar. |
| *calendar.discord* | Discordian calendar (all rites reversed). |
| *calendar.fictional* | fantasy and fiction dates (mostly LOTR). |
| *calendar.french* | French calendar. |
| *calendar.german* | German calendar. |
| *calendar.history* | miscellaneous history. |
| *calendar.holiday* | other holidays (including the not-well-known, obscure, and really obscure). |
| *calendar.judaic* | Jewish holidays (should be updated yearly by the local system administrator so that roving holidays are set correctly for the current year). |
| *calendar.music* | musical events, births, and deaths (strongly oriented toward rock 'n' roll). |
| *calendar.nz* | New Zealand calendar. |
| *calendar.openbsd* | OpenBSD related events. |
| *calendar.pagan* | pagan holidays, celebrations and festivals. |
| *calendar.russian* | Russian calendar. |
| *calendar.space* | cosmic history. |
| *calendar.uk* | UK calendar. |
| *calendar.ushistory* | U.S. history. |
| *calendar.usholiday* | U.S. holidays. |
| *calendar.world* | world wide calendar. |

## SEE ALSO

at(1), cal(1), cpp(1), mail(1), cron(8)

## STANDARDS

The **calendar** program previously selected lines which had the correct
date anywhere in the line. This is no longer true: the date is only
recognized when it occurs at the beginning of a line.

## HISTORY

A **calendar** command appeared in Version 7 AT&T UNIX.

## BUGS

**calendar** doesn't handle all Jewish holidays or moon phases.
