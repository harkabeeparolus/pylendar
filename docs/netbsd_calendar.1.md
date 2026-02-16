---
title: CALENDAR
section: 1
header: General Commands Manual
date: June 1, 2016
footer: NetBSD 10.1
---

## NAME

**calendar** — reminder service

## SYNOPSIS

**calendar**
\[**-avx**]
\[**-d** *MMDD*\[\[*YY*]*YY*]]
\[**-f** *file*]
\[**-l** *days*]
\[**-w** *days*]

## DESCRIPTION

The **calendar** utility checks the current directory or the directory
specified by the `CALENDAR_DIR` environment variable for a file named
*calendar* and displays lines that begin with either today's date or
tomorrow's. On Fridays, events on Friday through Monday are displayed.

The following options are available:

**-a**
: Process the "calendar" files of all users and mail the results to
  them. This requires super-user privileges.

**-d** *MMDD*\[\[*YY*]*YY*]
: Display lines for the given date. By default, the current date is
  used. The year, which may be given in either two or four digit
  format, is used only for purposes of determining whether the given
  date falls on a Friday in that year (see below). If the year is not
  specified, the current year is assumed.

**-f** *file*
: Display matching calendar files from the given filename. By default,
  the following filenames are checked for: *~/calendar*,
  *~/.calendar*, */etc/calendar* and the first which is found is used.

**-l** *days*
: Causes the program to "look ahead" a given number of days (default
  one) from the specified date and display their entries as well.

**-v**
: Causes **calendar** to print version information for itself, and
  then exit.

**-w** *days*
: Causes the program to add the specified number of days to the "look
  ahead" number if and only if the day specified is a Friday. The
  default value is two, which causes **calendar** to print entries
  through the weekend on Fridays.

**-x**
: Causes **calendar** not to set the `CPP_RESTRICTED` environment
  variable.

Lines should begin with a month and day. They may be entered in almost
any format, either numeric or as character strings. A single asterisk
("\*") matches every month, or every day if a month has been provided.
Two asterisks ("\*\*") matches every day of the year. A day without a
month matches that day of every week. A month without a day matches the
first of that month. Two numbers default to the month followed by the
day. Lines with leading tabs default to the last entered date, allowing
multiple line specifications for a single date.

By convention, dates followed by an asterisk are not fixed, i.e., change
from year to year.

Day descriptions start after the first \<tab> character in the line; if
the line does not contain a \<tab> character, it is not displayed. If the
first character in the line is a \<tab> character, it is treated as a
continuation of the previous line.

The **calendar** file is preprocessed by cpp(1), allowing the inclusion
of shared files such as lists of company holidays or meetings. If the
shared file is not referenced by a full pathname, cpp(1) searches in the
current (or home) directory first, and then in the directory
*/usr/share/calendar*. Empty lines and lines protected by the C
commenting syntax `/* ... */` are ignored.

Some possible calendar entries (\<tab> characters highlighted by `\t`
sequence):

```
#include <calendar.usholiday>
#include <calendar.birthday>

6/15\tJune 15 (if ambiguous, will default to month/day).
Jun. 15\tJune 15.
15 June\tJune 15.
Thursday\tEvery Thursday.
June\tEvery June 1st.
15 *\t15th of every month.
*15\t15th of every month.
June*\tEvery day of June.
**\tEvery day.
```

## FILES

| Path | Description |
|---|---|
| *calendar.birthday* | Births and deaths of famous (and not-so-famous) people. |
| *calendar.christian* | Christian holidays. This calendar should be updated yearly by the local system administrator so that roving holidays are set correctly for the current year. |
| *calendar.computer* | Days of special significance to computer people. |
| *calendar.history* | Everything else, mostly U.S. historical events. |
| *calendar.holiday* | Other holidays, including the not-well-known, obscure, and really obscure. |
| *calendar.judaic* | Jewish holidays. This calendar should be updated yearly by the local system administrator so that roving holidays are set correctly for the current year. |
| *calendar.lotr* | Important dates in the Lord of the Rings series. |
| *calendar.music* | Musical events, births, and deaths. Strongly oriented toward rock 'n' roll. |
| *calendar.netbsd* | Important dates in the history of the NetBSD project. |
| *calendar.usholiday* | U.S. holidays. This calendar should be updated yearly by the local system administrator so that roving holidays are set correctly for the current year. |

## COMPATIBILITY

The **calendar** program previously selected lines which had the correct
date anywhere in the line. This is no longer true, the date is only
recognized when it occurs first on the line. In NetBSD 3.0, the
**calendar** command was modified to search the user's home directory
instead of the current directory by default.

## SEE ALSO

at(1), cpp(1), cron(8)

## HISTORY

A **calendar** command appeared in Version 7 AT&T UNIX.

## BUGS

**calendar** doesn't handle events that move around from year to year,
i.e., "the last Monday in April". The **-a** option ignores the user's
`CALENDAR_DIR` environment variable.
