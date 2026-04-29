#! /usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dateutil",
#     "astronomy-engine",
#     "lunardate",
# ]
# ///

"""An improved replacement for the BSD calendar utility, written in Python.

Reads a text file with dated events, and prints the events scheduled
for today and upcoming days. See the manpage for full documentation.
"""

import argparse
import calendar
import contextlib
import datetime
import functools
import locale
import logging
import os
import re
import sys
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Self, TypeAlias

try:
    import dateutil.easter
except ImportError:  # pragma: no cover
    sys.exit("Error: This script requires the 'python-dateutil' package.")

try:
    import astronomy
except ImportError:  # pragma: no cover
    sys.exit("Error: This script requires the 'astronomy-engine' package.")

try:
    from lunardate import LunarDate
except ImportError:  # pragma: no cover
    sys.exit("Error: This script requires the 'lunardate' package.")

STARTER_CALENDAR = """\
/* pylendar starter calendar. See `man pylendar` for the full date format
 * reference. Lines below are TAB-separated: <date><TAB><description>. */

/* Fixed dates */
Jan 1\tNew Year's Day
Jul 4\tUS Independence Day [1776]

/* ISO 8601 (pylendar extension) */
2028-07-14\tStart of the LA Olympics

/* Recurring: the 15th of every month */
* 15\tMid-month reminder

/* Weekday-of-month: 2nd Monday in May */
May/MonSecond\t2nd Monday in May

/* Astronomical specials */
Easter\tEaster Sunday
DecSolstice\tWinter solstice
"""

log = logging.getLogger("pylendar")

__version__ = "0.7.0"

XDG_CONFIG_HOME = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
DEFAULT_CALENDAR_PATHS: list[Path] = [
    Path.home() / ".calendar",
    XDG_CONFIG_HOME / "calendar",
    Path("/etc/calendar"),
    Path("/usr/share/calendar"),
    Path("/usr/local/share/calendar"),
]

ORDINAL_MAP: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "last": -1,
}
_LETTER = r"[^\W\d_]"  # Unicode letter (like [a-z] but locale-aware)
_NN = r"\d{1,2}"  # 1-or-2-digit number (month or day)
_DELTA = r"\d{1,3}"  # max ±999 days; 4+ digits look like a year

DateSet: TypeAlias = set[datetime.date]


class DateExpr(ABC):  # pylint: disable=too-few-public-methods
    """A date expression that resolves to concrete dates for a given year."""

    variable: ClassVar[bool] = True
    """Whether the resolved date changes from year to year.

    BSD calendar marks variable dates with an asterisk in the output.
    Fixed expressions like MM/DD and * DD override this to False.
    """

    @abstractmethod
    def resolve(self, year: int) -> DateSet:
        """Return the set of dates this expression matches in the given year."""


@dataclass(frozen=True)
class FixedDate(DateExpr):
    """A fixed month/day, optionally pinned to a specific year."""

    variable: ClassVar[bool] = False

    month: int
    day: int
    year: int | None = None

    def resolve(self, year: int) -> DateSet:
        """Return the single date, using the stored year if present."""
        try:
            y = self.year if self.year is not None else year
            return {datetime.date(y, self.month, self.day)}
        except ValueError:
            return set()


@dataclass(frozen=True)
class WildcardDay(DateExpr):
    """Matches the given day in every month (e.g., * 15)."""

    variable: ClassVar[bool] = False

    day: int

    def resolve(self, year: int) -> DateSet:
        """Return dates for this day in all 12 months of the given year."""
        dates: DateSet = set()
        for month in range(1, 13):
            with contextlib.suppress(ValueError):
                dates.add(datetime.date(year, month, self.day))
        return dates


@dataclass(frozen=True)
class EveryDay(DateExpr):
    """Matches every day of the year (e.g., **)."""

    variable: ClassVar[bool] = False

    def resolve(self, year: int) -> DateSet:
        """Return all dates in the given year."""
        jan1 = datetime.date(year, 1, 1)
        num_days = 366 if calendar.isleap(year) else 365
        return {jan1 + datetime.timedelta(days=d) for d in range(num_days)}


@dataclass(frozen=True)
class EveryDayOfMonth(DateExpr):
    """Matches every day of a specific month (e.g., June*)."""

    variable: ClassVar[bool] = False

    month: int

    def resolve(self, year: int) -> DateSet:
        """Return all dates in the given month."""
        num_days = calendar.monthrange(year, self.month)[1]
        return {datetime.date(year, self.month, d) for d in range(1, num_days + 1)}


@dataclass(frozen=True)
class ResolvedDate(DateExpr):
    """A pre-resolved date or set of dates (Easter, equinoxes, moon phases, etc.)."""

    dates: frozenset[datetime.date]

    @classmethod
    def of(cls, *dates: datetime.date) -> Self:
        """Create from one or more individual dates."""
        return cls(frozenset(dates))

    def resolve(self, year: int) -> DateSet:  # noqa: ARG002
        """Return all pre-resolved dates."""
        return set(self.dates)


def _find_nth_weekday(
    year: int, month: int, weekday: int, n: int
) -> datetime.date | None:
    """Find the Nth occurrence of a weekday in a given month.

    n > 0: count from start (1=first, 2=second, ..., 5=fifth)
    n < 0: count from end (-1=last, -2=second-to-last)
    Returns None if the occurrence doesn't exist (e.g. 5th Monday of Feb).
    """
    if n > 0:
        first_day = datetime.date(year, month, 1)
        days_ahead = (weekday - first_day.weekday()) % 7
        first_occurrence = first_day + datetime.timedelta(days=days_ahead)
        target = first_occurrence + datetime.timedelta(weeks=n - 1)
    else:
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime.date(year, month, last_day_num)
        days_back = (last_day.weekday() - weekday) % 7
        last_occurrence = last_day - datetime.timedelta(days=days_back)
        target = last_occurrence + datetime.timedelta(weeks=n + 1)
    return target if target.month == month else None


@dataclass(frozen=True)
class NthWeekdayOfMonth(DateExpr):
    """Nth weekday of a specific month (e.g., May Sun+2 for Mother's Day)."""

    month: int
    weekday: int
    n: int

    def resolve(self, year: int) -> DateSet:
        """Return the Nth weekday of the month, or empty if it doesn't exist."""
        result = _find_nth_weekday(year, self.month, self.weekday, self.n)
        return {result} if result else set()


@dataclass(frozen=True)
class NthWeekdayEveryMonth(DateExpr):
    """Nth weekday of every month (e.g., * Fri+3 for 3rd Friday of every month)."""

    weekday: int
    n: int

    def resolve(self, year: int) -> DateSet:
        """Return the Nth weekday for each of the 12 months."""
        return {
            r
            for m in range(1, 13)
            if (r := _find_nth_weekday(year, m, self.weekday, self.n))
        }


@dataclass(frozen=True)
class OffsetDate(DateExpr):
    """A computed date offset by a number of days (e.g., Easter-2 for Good Friday)."""

    base: DateExpr
    offset: int

    def resolve(self, year: int) -> DateSet:
        """Return base dates shifted by offset days."""
        delta = datetime.timedelta(days=self.offset)
        return {d + delta for d in self.base.resolve(year)}


@dataclass(frozen=True)
class EveryWeekday(DateExpr):
    """Every occurrence of a weekday in the year (e.g., Friday)."""

    weekday: int

    def resolve(self, year: int) -> DateSet:
        """Return all occurrences of this weekday in the given year."""
        jan1 = datetime.date(year, 1, 1)
        first = jan1 + datetime.timedelta(days=(self.weekday - jan1.weekday()) % 7)
        week = datetime.timedelta(weeks=1)
        return {day for w in range(53) if (day := first + week * w).year == year}


@dataclass(frozen=True)
class WeekdayRelativeToDate(DateExpr):
    """Weekday strictly before or after a fixed date (e.g., Sat>Jun 19)."""

    month: int
    day: int
    weekday: int  # 0=Mon ... 6=Sun
    direction: int  # -1 = before (<), +1 = after (>)
    anchor_offset: int = 0  # day offset applied to anchor before search

    def __post_init__(self) -> None:
        """Validate fields so resolution cannot enter invalid states."""
        if self.direction not in {-1, 1}:
            msg = f"direction must be -1 or 1, got {self.direction}"
            raise ValueError(msg)
        if not 0 <= self.weekday <= 6:  # noqa: PLR2004
            msg = f"weekday must be in range 0..6, got {self.weekday}"
            raise ValueError(msg)

    def resolve(self, year: int) -> DateSet:
        """Return the nearest weekday before/after the anchor date."""
        try:
            anchor = datetime.date(year, self.month, self.day) + datetime.timedelta(
                days=self.anchor_offset
            )
        except ValueError:
            return set()
        diff = (self.direction * (self.weekday - anchor.weekday())) % 7 or 7
        return {anchor + datetime.timedelta(days=diff * self.direction)}


def _display_path(path: Path) -> str:
    """Format a path for log messages, using ~ for paths under the home directory."""
    if path.is_relative_to(Path.home()):
        return f"~/{path.relative_to(Path.home())}"
    return str(path)


def main(argv: list[str] | None = None) -> None:
    """Run the calendar utility."""
    logging.basicConfig(
        level=logging.WARNING, format="pylendar: %(levelname)s: %(message)s"
    )
    try:
        return cli(argv)
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit("Interrupted by user.")


def cli(argv: list[str] | None = None) -> None:
    """Command-line interface for the calendar utility."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose >= 2:  # noqa: PLR2004
        level = logging.DEBUG
        fmt = "pylendar [%(levelname)s] %(message)s"
    elif args.verbose == 1:
        level = logging.INFO
        fmt = "pylendar: %(message)s"
    else:
        level = logging.WARNING
        fmt = "pylendar: %(levelname)s: %(message)s"

    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        root.handlers[0].setFormatter(logging.Formatter(fmt))

    utc_offset, longitude = resolve_coordinates(args.U, args.l)

    try:
        today = resolve_today(args.today, utc_offset)
    except (argparse.ArgumentTypeError, ValueError) as e:
        parser.error(str(e))

    if args.D:
        print_diagnostic(args.D, today.year, utc_offset, longitude)
        return

    if args.init:
        run_init()
        return

    calendar_path = resolve_calendar_path(args.file)
    if calendar_path is None:
        return

    friday = bsd_to_python_weekday(args.F)
    opts = CalendarOptions(
        ahead=args.W if args.W is not None else args.A,
        behind=args.B,
        friday=friday,
        expand_weekends=args.A is not None,
        weekday=args.w,
        utc_offset_hours=utc_offset,
        include_dirs=DEFAULT_CALENDAR_PATHS,
    )
    try:
        lines = process_calendar(calendar_path, today, opts)
    except (OSError, SyntaxError) as e:
        sys.exit(f"Error: Could not read calendar file: {e}")

    for line in lines:
        print(line)


@dataclass(frozen=True)
class CalendarDirectives:
    """Global directives parsed from a calendar file (LANG=, SEQUENCE=)."""

    lang: str | None = None
    sequence: tuple[str, ...] | None = None


@dataclass(frozen=True)
class CalendarOptions:
    """Options for calendar processing."""

    ahead: int | None = None
    behind: int = 0
    friday: int = 4
    expand_weekends: bool = False
    weekday: bool = False
    utc_offset_hours: float = 0
    include_dirs: Sequence[Path] = ()


def process_calendar(
    calendar_path: Path,
    today: datetime.date,
    options: CalendarOptions | None = None,
) -> list[str]:
    """Process a calendar file and return formatted event strings."""
    opts = options or CalendarOptions()
    processor = SimpleCPP(include_dirs=opts.include_dirs)
    calendar_lines = join_continuation_lines(processor.process_file(calendar_path))

    ahead_days = (
        opts.ahead
        if opts.ahead is not None
        else 3
        if today.weekday() == opts.friday
        else 1
    )
    behind_days = opts.behind
    dates_to_check = get_dates_to_check(
        today,
        ahead_days,
        behind_days,
        friday=opts.friday,
        expand_weekends=opts.expand_weekends,
    )
    years_to_check = {d.year for d in dates_to_check}
    date_exprs = parse_special_dates(
        calendar_lines, years_to_check, opts.utc_offset_hours
    )
    directives = extract_directives(calendar_lines)
    date_parser = DateStringParser(date_exprs, directives=directives)

    log.info(f"Today: {today}")
    log.info(f"Date range: {behind_days} days back, {ahead_days} days ahead")
    log.debug(f"dates_to_check = {dates_to_check}")
    log.debug(f"date_exprs = {date_exprs}")

    matching_events = [
        event
        for line in calendar_lines
        for event in get_matching_events(line, dates_to_check, date_parser)
    ]
    log.info(f"Found {len(matching_events)} event(s) in date range")
    return [
        format_event(event, weekday=opts.weekday) for event in sorted(matching_events)
    ]


def join_continuation_lines(lines: list[str]) -> list[str]:
    """Join tab-indented continuation lines with their parent line."""
    result: list[str] = []
    for line in lines:
        if line.startswith("\t") and result:
            # Continuation line - append to previous
            result[-1] += "\n" + line
        else:
            result.append(line)
    return result


@dataclass
class Event:
    """Represents a calendar event with date and description."""

    date: datetime.date
    description: str
    variable: bool = False

    def __post_init__(self) -> None:
        """Clean up the description by stripping whitespace."""
        self.description = self.description.strip()

    def __lt__(self, other: object) -> bool:
        """Enable sorting events by date."""
        if not isinstance(other, Event):
            return NotImplemented
        return self.date < other.date

    def __str__(self) -> str:
        """Format the event for display output."""
        star = "*" if self.variable else ""
        formatted_date = f"{self.date:%b} {self.date.day:2}{star}"
        return f"{formatted_date}\t{self.description}"


def format_event(event: Event, *, weekday: bool = False) -> str:
    """Format an event for display, optionally prepending the day-of-week name."""
    if weekday:
        prefix = f"{event.date:%a} "
        event_str = str(event)
        pad = " " * (len(prefix) + event_str.index("\t"))
        return prefix + event_str.replace("\n", "\n" + pad)
    return str(event)


def _parse_signed_int(match: re.Match[str], sign_group: int, value_group: int) -> int:
    """Extract a signed integer from regex match groups ('+', '3' → 3)."""
    sign = 1 if match.group(sign_group) == "+" else -1
    return sign * int(match.group(value_group))


class DateStringParser:  # pylint: disable=too-many-instance-attributes
    """Parser for date strings from calendar files.

    Note: This class is not thread-safe. During initialization, it uses
    ``calendar.different_locale()`` which temporarily mutates the global C-level
    locale state. If used as a library in a multi-threaded application,
    instantiating this class concurrently with other locale-dependent
    operations may cause race conditions.
    """

    month_map: dict[str, int]
    weekday_map: dict[str, int]
    ordinal_map: dict[str, int]
    ordinals_re: str

    _re_special_offset: re.Pattern[str]
    _re_full_date: re.Pattern[str]
    _re_slash_dd: re.Pattern[str]
    _re_mm_wkday_offset: re.Pattern[str]
    _re_month_wkday_offset: re.Pattern[str]
    _re_month_day_1: re.Pattern[str]
    _re_month_day_2: re.Pattern[str]
    _re_wildcard_wkday: re.Pattern[str]
    _re_wildcard_day: re.Pattern[str]
    _re_month_wildcard: re.Pattern[str]
    _re_mm_ord: re.Pattern[str]
    _re_month_ord_1: re.Pattern[str]
    _re_month_ord_2: re.Pattern[str]

    def __init__(
        self,
        date_exprs: dict[str, DateExpr] | None = None,
        *,
        directives: CalendarDirectives | None = None,
    ) -> None:
        """Initialize the parser with optional date expressions and directives."""
        self.date_exprs: dict[str, DateExpr] = date_exprs or {}
        dirs = directives or CalendarDirectives()

        # Start with system locale names
        self.month_map = self.build_month_map()
        self.weekday_map = self.build_weekday_map()

        # Layer C/English names on top
        with calendar.different_locale(("C", "UTF-8")):
            self._layer_locale_maps()

        # Layer LANG= locale names on top, if set
        lang_base = dirs.lang.lower().split(".")[0] if dirs.lang else None
        if lang_base and lang_base not in {"c", "posix", "utf-8", "utf8"}:
            try:
                lang_parts = dirs.lang.split(".", 1) if dirs.lang else []
                encoding = lang_parts[1] if len(lang_parts) > 1 else "UTF-8"
                lang_locale = (lang_parts[0], encoding)
                with calendar.different_locale(lang_locale):
                    self._layer_locale_maps()
                log.info(f"Using locale: {dirs.lang}")
            except locale.Error:
                log.warning(f"LANG={dirs.lang}: locale not available; ignoring")

        # Build per-instance ordinal map
        self.ordinal_map = dict(ORDINAL_MAP)
        if dirs.sequence:
            for word, n in zip(dirs.sequence, (1, 2, 3, 4, 5, -1), strict=True):
                self.ordinal_map[word.casefold()] = n
            log.info(f"Custom ordinal sequence: {dirs.sequence}")
        self.ordinals_re = "|".join(self.ordinal_map)

        # Precompile regexes used in parsing
        self._re_special_offset = re.compile(rf"({_LETTER}+)([+-])({_DELTA})")
        self._re_full_date = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")
        self._re_slash_dd = re.compile(rf"({_NN}|{_LETTER}+)/({_NN})")
        self._re_mm_wkday_offset = re.compile(rf"({_NN})/({_LETTER}+)([+-])({_DELTA})")
        self._re_month_wkday_offset = re.compile(
            rf"({_LETTER}+)\s+({_LETTER}+)([+-])({_DELTA})"
        )
        self._re_month_day_1 = re.compile(rf"({_LETTER}+)\s+({_NN})")
        self._re_month_day_2 = re.compile(rf"({_NN})\s+({_LETTER}+)")
        self._re_wildcard_wkday = re.compile(rf"\*\s+({_LETTER}+)([+-])({_DELTA})")
        self._re_wildcard_day = re.compile(r"\*\s*(\d{1,2})|(\d{1,2})\s+\*")
        self._re_month_wildcard = re.compile(rf"({_LETTER}+)\s*\*")

        ltr, ords = _LETTER, self.ordinals_re
        self._re_mm_ord = re.compile(rf"({_NN})/({ltr}+)({ords})([+-]{_DELTA})?")
        self._re_month_ord_1 = re.compile(rf"({ltr}+)/({ltr}+)({ords})([+-]{_DELTA})?")
        self._re_month_ord_2 = re.compile(rf"({_LETTER}+)({ords})\s+({_LETTER}+)")

    @staticmethod
    def build_month_map() -> dict[str, int]:
        """Build a locale-aware map of month names/abbreviations to numbers."""
        return {
            m.casefold(): n
            for s in (calendar.month_name, calendar.month_abbr)
            for n, m in enumerate(s)
            if m
        }

    @staticmethod
    def build_weekday_map() -> dict[str, int]:
        """Build a locale-aware map of weekday names/abbreviations to numbers."""
        return {
            d.casefold(): n
            for s in (calendar.day_name, calendar.day_abbr)
            for n, d in enumerate(s)
        }

    def _layer_locale_maps(self) -> None:
        """Update month/weekday maps from the currently active locale."""
        self.month_map.update(self.build_month_map())
        self.weekday_map.update(self.build_weekday_map())

    def parse(self, date_str: str) -> DateExpr | None:
        """Parse a date string from the calendar file.

        Supports special dates, aliases, and standard date formats.
        Pattern order matters — more specific patterns are tried first.
        """
        date_str = date_str.strip().casefold()

        # Special date with offset (e.g., Easter-2, FullMoon+1)
        # Must precede plain special-date lookup
        if match := self._re_special_offset.fullmatch(date_str):
            offset = _parse_signed_int(match, 2, 3)
            if base := self.date_exprs.get(match.group(1)):
                return OffsetDate(base, offset)

        # Plain special dates and aliases
        if date_expr := self.date_exprs.get(date_str):
            return date_expr

        # Standalone weekday (e.g., Friday) — checked before regex
        if date_str in self.weekday_map:
            return EveryWeekday(self.weekday_map[date_str])

        # Standalone month name (e.g., June) — matches the 1st of that month
        if date_str in self.month_map:
            return FixedDate(self.month_map[date_str], 1)

        # Weekday relative to date (e.g., Sat>Jun 19, Sun<Dec 25-7)
        if ("<" in date_str or ">" in date_str) and (
            result := self._parse_weekday_relative(date_str)
        ):
            return result

        return self._parse_format_patterns(date_str)

    def _parse_ordinal_weekday(self, date_str: str) -> DateExpr | None:
        """Parse BSD ordinal weekday formats (e.g., 10/MonSecond, Oct/SatFourth-2)."""
        if match := self._re_mm_ord.fullmatch(date_str):
            # MM/WkdayOrdinal with optional offset (e.g., 10/monsecond, 01/monthird)
            month = int(match.group(1))
        elif match := self._re_month_ord_1.fullmatch(date_str):
            # Month/WkdayOrdinal with optional offset (e.g., oct/satfourth-2)
            if (month_name := match.group(1)) not in self.month_map:
                return None
            month = self.month_map[month_name]
        else:
            return None

        if (wkday_name := match.group(2)) not in self.weekday_map:
            return None
        n = self.ordinal_map[match.group(3)]
        base: DateExpr = NthWeekdayOfMonth(month, self.weekday_map[wkday_name], n)
        if match.group(4):
            base = OffsetDate(base, int(match.group(4)))
        return base

    def _parse_full_date(self, date_str: str) -> DateExpr | None:
        """Parse YYYY/M/D or YYYY-MM-DD format (e.g., 2026/2/17, 2026-02-17)."""
        if match := self._re_full_date.fullmatch(date_str):
            return FixedDate(
                month=int(match.group(2)),
                day=int(match.group(3)),
                year=int(match.group(1)),
            )
        return None

    def _parse_slash_dd(self, date_str: str) -> DateExpr | None:
        """Parse MM/DD or Month/DD format (e.g., 07/21, apr/17)."""
        if match := self._re_slash_dd.fullmatch(date_str):
            g1 = match.group(1)
            month = int(g1) if g1.isdigit() else self.month_map.get(g1)
            if month is not None:
                return FixedDate(month, int(match.group(2)))
        return None

    def _parse_mm_wkday_offset(self, date_str: str) -> DateExpr | None:
        """Parse MM/Weekday+/-N format (e.g., 03/Sun-1, 11/Wed+3, 12/Sun+1)."""
        if match := self._re_mm_wkday_offset.fullmatch(date_str):
            month = int(match.group(1))
            wkday_name = match.group(2)
            if wkday_name in self.weekday_map:
                n = _parse_signed_int(match, 3, 4)
                return NthWeekdayOfMonth(month, self.weekday_map[wkday_name], n)
        return None

    def _parse_month_wkday_offset(self, date_str: str) -> DateExpr | None:
        """Parse Month Weekday+/-N format (e.g., May Sun+2, Nov Thu+4, May Mon-1)."""
        if match := self._re_month_wkday_offset.fullmatch(date_str):
            month_name, wkday_name = match.group(1), match.group(2)
            n = _parse_signed_int(match, 3, 4)
            if month_name in self.month_map and wkday_name in self.weekday_map:
                return NthWeekdayOfMonth(
                    self.month_map[month_name],
                    self.weekday_map[wkday_name],
                    n,
                )
        return None

    def _parse_month_day(self, date_str: str) -> DateExpr | None:
        """Parse Month DD or DD Month format (e.g., July 9, 01 Jan)."""
        if match := self._re_month_day_1.fullmatch(date_str):
            month_name, day = match.group(1), int(match.group(2))
        elif match := self._re_month_day_2.fullmatch(date_str):
            month_name, day = match.group(2), int(match.group(1))
        else:
            return None
        if month_name in self.month_map:
            return FixedDate(self.month_map[month_name], day)
        return None

    def _parse_wildcard_wkday(self, date_str: str) -> DateExpr | None:
        """Parse * Weekday+/-N format (e.g., * Fri+3)."""
        if match := self._re_wildcard_wkday.fullmatch(date_str):
            wkday_name = match.group(1)
            n = _parse_signed_int(match, 2, 3)
            if wkday_name in self.weekday_map:
                return NthWeekdayEveryMonth(self.weekday_map[wkday_name], n)
        return None

    def _parse_wildcard_day(self, date_str: str) -> DateExpr | None:
        """Parse * DD, *DD, or DD * format (e.g., * 9, *15, 15 *)."""
        if match := self._re_wildcard_day.fullmatch(date_str):
            return WildcardDay(int(match.group(1) or match.group(2)))
        return None

    def _parse_month_wildcard(self, date_str: str) -> DateExpr | None:
        """Parse Month* or Month * format (every day of that month, e.g., June*)."""
        if match := self._re_month_wildcard.fullmatch(date_str):
            month_name = match.group(1)
            if month_name in self.month_map:
                return EveryDayOfMonth(self.month_map[month_name])
        return None

    def _parse_wkday_ord_month(self, date_str: str) -> DateExpr | None:
        """Parse WkdayOrd Month format (e.g., SunFirst Aug, SunThird Jul)."""
        if match := self._re_month_ord_2.fullmatch(date_str):
            wkday_name = match.group(1)
            month_name = match.group(3)
            if wkday_name in self.weekday_map and month_name in self.month_map:
                n = self.ordinal_map[match.group(2)]
                return NthWeekdayOfMonth(
                    self.month_map[month_name],
                    self.weekday_map[wkday_name],
                    n,
                )
        return None

    _WKDAY_REL_RE: ClassVar[re.Pattern[str]] = re.compile(
        rf"(?P<wkday>{_LETTER}+)\s*(?P<dir>[<>])\s*(?P<anchor>.+)"
    )

    # Offset capped at 3 digits so 4-digit tails (e.g. Sun<Dec 25-2015)
    # aren't misparsed as anchor "Dec 25" with a -2015-day offset.
    _ANCHOR_OFFSET_RE: ClassVar[re.Pattern[str]] = re.compile(rf"(.+?)([+-]{_DELTA})?$")

    def _parse_weekday_relative(self, date_str: str) -> DateExpr | None:
        """Parse Wkday<Date or Wkday>Date format (e.g., Sat>Jun 19, Sun<Dec 25-7)."""
        match = self._WKDAY_REL_RE.fullmatch(date_str)
        if not match:
            return None

        wkday_name = match.group("wkday")
        if wkday_name not in self.weekday_map:
            return None
        weekday = self.weekday_map[wkday_name]
        direction = 1 if match.group("dir") == ">" else -1

        anchor_str = match.group("anchor").strip()
        # Extract optional +/-N offset from the anchor
        offset_match = self._ANCHOR_OFFSET_RE.fullmatch(anchor_str)
        if not offset_match:
            return None
        base_anchor = offset_match.group(1).strip()
        anchor_offset = int(offset_match.group(2)) if offset_match.group(2) else 0

        anchor_date = self._parse_month_day(base_anchor) or self._parse_slash_dd(
            base_anchor
        )
        if not isinstance(anchor_date, FixedDate):
            return None

        return WeekdayRelativeToDate(
            month=anchor_date.month,
            day=anchor_date.day,
            weekday=weekday,
            direction=direction,
            anchor_offset=anchor_offset,
        )

    def _parse_format_patterns(self, date_str: str) -> DateExpr | None:
        """Parse regex-based date format patterns."""
        # YYYY/M/D, YYYY-MM-DD, MM/Wkday+N, MM/WkdayOrd, Month/WkdayOrd,
        # Month/DD, or MM/DD
        if "/" in date_str or ("-" in date_str and date_str[0].isdigit()):
            return (
                self._parse_full_date(date_str)
                or self._parse_mm_wkday_offset(date_str)
                or self._parse_ordinal_weekday(date_str)
                or self._parse_slash_dd(date_str)
            )

        # Non-slash patterns, tried most-specific first
        return (
            self._parse_month_wkday_offset(date_str)
            or self._parse_month_day(date_str)
            or self._parse_month_wildcard(date_str)
            or (EveryDay() if re.fullmatch(r"\*\s*\*", date_str) else None)
            or self._parse_wildcard_wkday(date_str)
            or self._parse_wildcard_day(date_str)
            or self._parse_wkday_ord_month(date_str)
        )


def remove_comments(code: str) -> str:
    """Remove C-style block and line comments (does not handle nesting or strings)."""
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)  # Remove block comments
    # TODO(anyone): Regex truncates URLs like https://example.com  # noqa: FIX002
    # because it treats the "//" as a line comment.
    return re.sub(r"(?:^|\s)//.*", "", code)  # Remove line comments


class SimpleCPP:
    """A simple C/C++ preprocessor emulator."""

    def __init__(self, include_dirs: Sequence[Path | str]) -> None:
        """Initialize the preprocessor with include directories."""
        self.include_dirs: list[Path] = [Path(d) for d in include_dirs]
        self.included_files: set[Path] = set()

    def process_file(self, path: Path) -> list[str]:
        """Process a C/C++ source file, resolving includes and removing comments."""
        abs_path = path.resolve()
        if abs_path in self.included_files:
            log.info(f"Skipping (already included): {_display_path(abs_path)}")
            return []
        log.info(f"Processing: {_display_path(abs_path)}")
        self.included_files.add(abs_path)

        lines: list[str] = []
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            log.warning(f"Skipping {path.name}: not valid UTF-8")
            return []
        for line_num, line in enumerate(remove_comments(text).splitlines(), start=1):
            stripped = line.strip()

            if stripped.startswith("#include"):
                if match := re.match(r'#include\s+[<"]([^">]+)[">]', stripped):
                    include_target = Path(match.group(1))
                    include_file = self.resolve_include(include_target, abs_path.parent)
                    if include_file:
                        lines.extend(self.process_file(include_file))
                    else:
                        msg = f"Included file not found: {include_target}"
                        log.warning(msg)
                else:
                    msg = (
                        f"Malformed include directive in {_display_path(abs_path)}"
                        f":{line_num}: {line}"
                    )
                    raise SyntaxError(msg)
            elif stripped.startswith("#"):
                log.debug(f"Skipping preprocessor directive: {line}")
                continue
            else:
                lines.append(line)

        return lines

    def resolve_include(
        self, name: Path, look_first: Path | None = None
    ) -> Path | None:
        """Resolve an included file by searching standard directories.

        Looks in look_first (the parent directory of the file containing the
        #include directive) before falling back to include_dirs. This mirrors C
        preprocessor semantics — relative includes resolve from the including
        file's location — and avoids any dependence on the process cwd.
        """
        dirs = [look_first, *self.include_dirs] if look_first else self.include_dirs
        for base_dir in dirs:
            candidate = base_dir / name
            if candidate.is_file():
                return candidate.resolve()

        # Locale fallback: uk_UA/foo → uk_UA.KOI8-U/foo
        parts = name.parts
        first = parts[0]
        if (
            not name.is_absolute()
            and "_" in first
            and "." not in first
            and len(parts) > 1
        ):
            rest = Path(*parts[1:])
            for base_dir in dirs:
                for locale_dir in sorted(
                    base_dir.glob(first + ".*"),
                    key=lambda p: ("UTF-8" not in p.name, p.name),
                ):
                    if locale_dir.is_dir():
                        candidate = locale_dir / rest
                        if candidate.is_file():
                            log.debug(
                                f"Resolved include via locale fallback:"
                                f" {name} -> {candidate}"
                            )
                            return candidate.resolve()

        return None


def get_utc_offset_hours() -> float:
    """Derive UTC offset in hours from the system timezone."""
    local_dt = datetime.datetime.now().astimezone()
    utc_offset = local_dt.utcoffset()
    if utc_offset is None:  # pragma: no cover
        return 0.0
    return utc_offset.total_seconds() / 3600


def resolve_coordinates(
    utc_offset_flag: float | None,
    longitude_flag: float | None,
) -> tuple[float, float]:
    """Derive UTC offset and east longitude from -U and -l flags."""
    if utc_offset_flag is not None:
        longitude = (
            longitude_flag if longitude_flag is not None else utc_offset_flag * 15
        )
        return utc_offset_flag, longitude
    if longitude_flag is not None:
        return longitude_flag / 15, longitude_flag
    offset = get_utc_offset_hours()
    return offset, offset * 15


def get_seasons(year: int, utc_offset_hours: float = 0) -> dict[str, datetime.date]:
    """Get the dates of equinoxes and solstices for a given year."""
    return {
        name: dt.date() for name, dt in _get_season_datetimes(year, utc_offset_hours)
    }


def _search_moon_phases(
    year: int, phase_angle: int, utc_offset_hours: float
) -> list[datetime.datetime]:
    """Return all moon phase datetimes for a year with UTC offset applied."""
    # Start searching from December of the previous year to catch
    # phases that shift into the current year locally due to timezone offsets.
    start_time = astronomy.Time.Make(year - 1, 12, 1, 0, 0, 0)
    offset = datetime.timedelta(hours=utc_offset_hours)
    results: list[datetime.datetime] = []
    search_time = start_time
    while True:
        moon_phase = astronomy.SearchMoonPhase(phase_angle, search_time, 40)
        if moon_phase is None:
            break
        dt = moon_phase.Utc() + offset

        if dt.date().year == year:
            results.append(dt)
        elif dt.date().year > year:
            break

        search_time = astronomy.Time.AddDays(moon_phase, 1)
    return results


def get_moon_phases(year: int, utc_offset_hours: float = 0) -> dict[str, DateSet]:
    """Get all new and full moon dates for a given year."""
    return {
        name: {dt.date() for dt in _search_moon_phases(year, angle, utc_offset_hours)}
        for name, angle in [("newmoon", 0), ("fullmoon", 180)]
    }


def _fractional_day_of_year(dt: datetime.datetime) -> float:
    """Return the fractional day-of-year for a datetime (1-based, like tm_yday)."""
    jan1 = datetime.datetime(dt.year, 1, 1)
    elapsed = dt - jan1
    return elapsed.total_seconds() / 86400 + 1


def _format_frac(value: float) -> str:
    """Format a float with ~6 significant figures, like BSD %g."""
    return f"{value:.6g}"


def _get_season_datetimes(
    year: int, utc_offset_hours: float
) -> list[tuple[str, datetime.datetime]]:
    """Return equinox/solstice (keyword, datetime) pairs with UTC offset applied."""
    seasons = astronomy.Seasons(year)
    offset = datetime.timedelta(hours=utc_offset_hours)
    return [
        ("marequinox", seasons.mar_equinox.Utc() + offset),
        ("sepequinox", seasons.sep_equinox.Utc() + offset),
        ("junsolstice", seasons.jun_solstice.Utc() + offset),
        ("decsolstice", seasons.dec_solstice.Utc() + offset),
    ]


def print_diagnostic(mode: str, year: int, utc_offset: float, longitude: float) -> None:
    """Print diagnostic sun or moon information, then return."""
    print(f"UTCOffset: {_format_frac(utc_offset)}")
    print(f"eastlongitude: {_format_frac(longitude)}")

    _diag_labels = {
        "marequinox": "e[0]",
        "sepequinox": "e[1]",
        "junsolstice": "s[0]",
        "decsolstice": "s[1]",
    }
    if mode == "sun":
        print(f"Sun in {year}:")
        for name, dt in _get_season_datetimes(year, utc_offset):
            frac = _fractional_day_of_year(dt)
            ts = dt.strftime("%m-%d %H:%M:%S")
            print(f"{_diag_labels[name]} - {_format_frac(frac)} ({ts})")
    else:
        for label, angle in [("Full moon", 180), ("New moon", 0)]:
            dts = _search_moon_phases(year, angle, utc_offset)
            entries = " ".join(
                f"{_format_frac(_fractional_day_of_year(dt))} ({dt:%m-%d %H:%M:%S})"
                for dt in dts
            )
            print(f"{label} {year}:\t{entries}")


@functools.lru_cache
def _builtin_date_exprs(year: int, utc_offset_hours: float = 0) -> dict[str, DateExpr]:
    """Compute built-in special date expressions (Easter, seasons, moon phases, etc.).

    Cached so that both ``resolve_today`` and ``parse_special_dates`` share the
    same computation without paying the cost twice.  Callers that need to add
    aliases **must** copy the returned dict before mutating it.
    """
    date_exprs: dict[str, DateExpr] = {}

    date_exprs["easter"] = ResolvedDate.of(dateutil.easter.easter(year))
    date_exprs["paskha"] = ResolvedDate.of(
        dateutil.easter.easter(year, method=dateutil.easter.EASTER_ORTHODOX)
    )
    date_exprs["chinesenewyear"] = ResolvedDate.of(LunarDate(year, 1, 1).toSolarDate())

    date_exprs |= {
        name: ResolvedDate.of(date)
        for name, date in get_seasons(year, utc_offset_hours).items()
    }

    date_exprs |= {
        name: ResolvedDate(frozenset(dates))
        for name, dates in get_moon_phases(year, utc_offset_hours).items()
    }

    return date_exprs


def parse_special_dates(
    calendar_lines: list[str],
    years: Iterable[int],
    utc_offset_hours: float = 0,
) -> dict[str, DateExpr]:
    """Parse special date definitions and aliases from the calendar file.

    Built-ins are materialized for every year in ``years`` and unioned per
    keyword, so callers should pass the year set spanned by the date
    range under consideration.
    """
    merged: dict[str, frozenset[datetime.date]] = {}
    for y in years:
        for name, expr in _builtin_date_exprs(y, utc_offset_hours).items():
            if isinstance(expr, ResolvedDate):
                merged[name] = merged.get(name, frozenset()) | expr.dates
    date_exprs: dict[str, DateExpr] = {
        name: ResolvedDate(dates) for name, dates in merged.items()
    }

    # Parse aliases from calendar file
    for line in calendar_lines:
        if "=" in line and "\t" not in line:
            left, right = line.split("=", 1)
            left = left.strip().casefold()
            right = right.strip().casefold()
            # If either side is a known date expr, add the alias
            if left in date_exprs and right not in date_exprs:
                date_exprs[right] = date_exprs[left]
                log.debug(f"Date alias: {left} = {right}")
            elif right in date_exprs:
                date_exprs[left] = date_exprs[right]
                log.debug(f"Date alias: {left} = {right}")

    return date_exprs


def extract_directives(calendar_lines: list[str]) -> CalendarDirectives:
    """Extract LANG= and SEQUENCE= directives from preprocessed calendar lines.

    Directives are lines without tabs whose left-hand side is ``LANG`` or
    ``SEQUENCE`` (case-sensitive).  Last occurrence wins.

    Note: Unlike BSD calendar which evaluates LANG= and SEQUENCE= sequentially
    per-file or per-block, pylendar evaluates them globally for the entire
    merged input after SimpleCPP preprocessing. The last occurrence wins and
    applies everywhere. This is an intentional simplification, as most modern
    files use standard UTF-8 throughout.
    """
    lang: str | None = None
    sequence: tuple[str, ...] | None = None

    for line in calendar_lines:
        if "\t" in line or "=" not in line:
            continue
        left, right = line.split("=", 1)
        left = left.strip()
        right = right.strip()
        if left == "LANG":
            lang = right or None
        elif left == "SEQUENCE":
            words = right.split()
            if len(words) == 6:  # noqa: PLR2004
                sequence = tuple(words)
            else:
                log.warning(
                    f"SEQUENCE= requires exactly 6 words, got {len(words)}; ignoring"
                )

    return CalendarDirectives(lang=lang, sequence=sequence)


def _parse_dot_date(t_str: str) -> datetime.date:
    """Parse a macOS/FreeBSD dot-separated date: dd[.mm[.year]].

    Single-digit day/month values are accepted (e.g. ``5.6``).
    Year is taken literally — no two-digit heuristic is applied.
    """
    parts = t_str.split(".")
    if len(parts) < 2 or len(parts) > 3:  # noqa: PLR2004
        msg = f"Invalid dot-separated date (expected dd.mm or dd.mm.year): {t_str}"
        raise argparse.ArgumentTypeError(msg)
    try:
        dd = int(parts[0])
        mm = int(parts[1])
        year = int(parts[2]) if len(parts) == 3 else datetime.date.today().year  # noqa: PLR2004
    except ValueError:
        msg = f"Non-numeric value in dot-separated date: {t_str}"
        raise argparse.ArgumentTypeError(msg) from None
    try:
        return datetime.date(year, mm, dd)
    except ValueError:
        msg = f"Out-of-range dot-separated date: {t_str}"
        raise argparse.ArgumentTypeError(msg) from None


def _parse_legacy_today(t_str: str) -> datetime.date | None:
    """Try to parse -t as a legacy numeric or dot-separated format.

    Returns the parsed date, or ``None`` if the string is not a legacy format.
    """
    if "." in t_str:
        return _parse_dot_date(t_str)
    # cSpell:ignore mmdd, ccyymmdd
    if t_str.isdigit():
        today = datetime.date.today()
        match len(t_str):
            case 2:  # dd
                return datetime.date(today.year, today.month, int(t_str))
            case 4:  # mmdd
                return datetime.date(today.year, int(t_str[:2]), int(t_str[2:]))
            case 6:  # yymmdd
                yy = int(t_str[:2])
                mm = int(t_str[2:4])
                dd = int(t_str[4:])
                cc = 19 if 69 <= yy <= 99 else 20  # noqa: PLR2004  # 69-99 → 1900s
                return datetime.date(cc * 100 + yy, mm, dd)
            case 8:  # ccyymmdd
                return datetime.date(int(t_str[:4]), int(t_str[4:6]), int(t_str[6:]))
            case _:
                pass
    return None


def resolve_today(t_str: str | None, utc_offset_hours: float = 0) -> datetime.date:
    """Resolve the -t argument into a concrete date.

    Acceptable formats:
      - OpenBSD/Debian positional: dd, mmdd, yymmdd, ccyymmdd
      - macOS/FreeBSD dot-separated: dd.mm, dd.mm.year
      - Any pylendar date expression that resolves to exactly one date
        (including special dates like Easter that need UTC offset)

    Returns ``datetime.date.today()`` when *t_str* is ``None``.

    Raises:
        argparse.ArgumentTypeError: On invalid or ambiguous input.

    """
    if t_str is None:
        return datetime.date.today()

    t_str = t_str.strip()
    legacy = _parse_legacy_today(t_str)
    if legacy is not None:
        return legacy

    year = datetime.date.today().year
    date_exprs = _builtin_date_exprs(year, utc_offset_hours)
    date_expr = DateStringParser(date_exprs).parse(t_str)
    if date_expr is None:
        msg = f"Invalid -t date format: {t_str}"
        raise argparse.ArgumentTypeError(msg)

    resolved = date_expr.resolve(year)
    if not resolved:
        msg = f"Date does not resolve in year {year}: {t_str}"
        raise argparse.ArgumentTypeError(msg)
    if len(resolved) > 1:
        msg = f"Ambiguous -t date format (matches multiple dates): {t_str}"
        raise argparse.ArgumentTypeError(msg)
    return next(iter(resolved))


def get_dates_to_check(
    today: datetime.date,
    ahead: int = 1,
    behind: int = 0,
    *,
    friday: int = 4,
    expand_weekends: bool = False,
) -> DateSet:
    """Determine the set of dates to check for events, given -A and -B options."""
    day = datetime.timedelta(days=1)
    dates: DateSet = {today + day * d for d in range(-behind, 1)}
    if not expand_weekends:
        dates.update(today + day * d for d in range(1, ahead + 1))
        return dates
    # Business-day walk (macOS/FreeBSD -A): landing on the day after "Friday"
    # makes that step and the next free (don't decrement the counter).
    saturday, remaining, current, skip = (friday + 1) % 7, ahead, today, False
    while remaining > 0:
        current += day
        dates.add(current)
        if skip:
            skip = False
        elif current.weekday() == saturday:
            skip = True
        else:
            remaining -= 1
    return dates


def parse_bsd_weekday(value: str) -> int:
    """Parse BSD weekday number for -F (0=Sun .. 6=Sat)."""
    try:
        day = int(value)
    except ValueError as exc:
        msg = f"Invalid BSD weekday: {value}"
        raise argparse.ArgumentTypeError(msg) from exc
    if not 0 <= day <= 6:  # noqa: PLR2004
        msg = f"BSD weekday out of range [0-6]: {day}"
        raise argparse.ArgumentTypeError(msg)
    return day


def positive_int(value: str) -> int:
    """Argparse converter that accepts only non-negative integers."""
    num = int(value)
    if num < 0:
        msg = f"value must be >= 0, got {num}"
        raise ValueError(msg)
    return num


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the calendar utility."""
    parser = argparse.ArgumentParser(
        description=__doc__,
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create a starter calendar file at ~/.calendar/calendar and exit. "
        "Will not overwrite an existing file.",
    )
    parser.add_argument(
        "-f",
        dest="file",
        help="Path to the calendar file. Overrides the default search path.",
    )
    ahead_group = parser.add_mutually_exclusive_group()
    ahead_group.add_argument(
        "-A",
        type=positive_int,
        metavar="num",
        help="Print lines from today and next num business days (forward, future). "
        "Weekend days after 'Friday' are included for free. "
        "Defaults to 1, except on Fridays the default is 3.",
    )
    ahead_group.add_argument(
        "-W",
        type=positive_int,
        metavar="num",
        help="Print lines from today and next num calendar days (forward, future). "
        "No Friday/weekend expansion.",
    )
    parser.add_argument(
        "-B",
        type=positive_int,
        default=0,
        metavar="num",
        help="Print lines from today and previous num days (backward, past). "
        "Default 0.",
    )
    parser.add_argument(
        "-F",
        type=parse_bsd_weekday,
        default=5,
        metavar="friday",
        # Day numbering follows BSD tm_wday convention.
        help='Set which day is "Friday" (the day before the weekend). '
        "Day numbering: 0=Sun, 1=Mon, ..., 5=Fri, 6=Sat. Default 5.",
    )
    parser.add_argument(
        "-l",
        type=float,
        metavar="longitude",
        help="East longitude of your stranding. Default derived from UTC offset.",
    )
    parser.add_argument(
        "-U",
        type=float,
        metavar="utc-offset",
        help="UTC offset in hours (e.g. -8 for PST, 1 for CET). "
        "Default derived from system timezone.",
    )
    parser.add_argument(
        "-D",
        choices=["sun", "moon"],
        metavar="sun|moon",
        help="Print diagnostic sun or moon information and exit.",
    )
    parser.add_argument(
        "-t",
        metavar="date",
        dest="today",
        # Positional format from OpenBSD/Debian; dot-separated from macOS/FreeBSD.
        help="Act like the specified value is 'today' instead of using the current "
        "date. Accepts [[[cc]yy]mm]dd (if yy is between 69 and 99, cc defaults "
        "to 19; otherwise 20), dd.mm[.year], or any pylendar date expression "
        "that resolves to exactly one date.",
    )
    # NOTE: NetBSD uses -w for "extra Friday days" (different meaning).
    # We follow the OpenBSD/Debian convention.
    parser.add_argument(
        "-w",
        action="store_true",
        help="Print day of the week name in front of each event.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times).",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def bsd_to_python_weekday(bsd_wday: int) -> int:
    """Convert BSD tm_wday (0=Sun..6=Sat) to Python weekday (0=Mon..6=Sun)."""
    return (bsd_wday - 1) % 7


def replace_age_in_description(description: str, check_date: datetime.date) -> str:
    """Replace exactly one [YYYY] with calculated age in event description."""
    matches = re.findall(r"\[(\d{4})\]", description)
    if len(matches) == 1:
        year_val = int(matches[0])
        age = check_date.year - year_val
        return description.replace(f"[{matches[0]}]", str(age))
    return description


def get_matching_events(
    line: str,
    dates_to_check: DateSet,
    parser: DateStringParser,
) -> list[Event]:
    """Get events from this line that match any of the target dates."""
    if not line.strip() or "\t" not in line:
        return []

    date_str, event_description = line.split("\t", 1)

    expr = parser.parse(date_str)
    explicit_variable = False

    if expr is None and date_str.rstrip().endswith("*"):
        explicit_variable = True
        date_str = date_str.rstrip().removesuffix("*")
        expr = parser.parse(date_str)

    if expr is None:
        log.debug(f"Unparseable date expression: {date_str!r}")
        return []

    years = {d.year for d in dates_to_check}
    # Check adjacent years to catch expressions that shift across year boundaries
    # (e.g., Sun>Dec 25+7 anchored in year Y but resolving to year Y+1).
    check_years = {y for base_y in years for y in (base_y - 1, base_y, base_y + 1)}
    resolved = {d for y in check_years for d in expr.resolve(y)}
    matching = resolved & dates_to_check

    variable = explicit_variable or expr.variable
    return [
        Event(d, replace_age_in_description(event_description, d), variable=variable)
        for d in matching
    ]


def find_calendar(look_in: Sequence[Path]) -> Path | None:
    """Find the calendar file in standard locations."""
    calendar_dir = os.environ.get("CALENDAR_DIR")
    first = Path(calendar_dir) if calendar_dir else Path.cwd()
    dirs = list(dict.fromkeys([first, *look_in]))
    log.debug(f"Searching for calendar in: {[str(d) for d in dirs]}")
    for dir_path in dirs:
        file = dir_path / "calendar"
        if file.is_file():
            return file.resolve()
    return None


def write_starter_calendar(target: Path) -> bool:
    """Write a starter calendar to *target*. Returns False if it already exists."""
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(STARTER_CALENDAR, encoding="utf-8")
    return True


def run_init() -> None:
    """Handle the ``--init`` flag: write a starter calendar to ~/.calendar/calendar."""
    target = Path.home() / ".calendar" / "calendar"
    if write_starter_calendar(target):
        print(f"pylendar: starter calendar written to {target}")
    else:
        print(f"pylendar: not overwriting existing file at {target}")


def resolve_calendar_path(file_arg: str | None) -> Path | None:
    """Resolve the calendar file path, warning and returning None on failure."""
    if file_arg:
        path = Path(file_arg)
        if not path.is_file():
            log.warning(f"Calendar file not found: {path}")
            return None
        return path
    found = find_calendar(DEFAULT_CALENDAR_PATHS)
    if found is None:
        home_target = Path.home() / ".calendar" / "calendar"
        log.warning(
            f"No calendar file found. Run 'pylendar --init' to create one "
            f"at {home_target}, or pass -f PATH."
        )
    return found


if __name__ == "__main__":  # pragma: no cover
    main()
