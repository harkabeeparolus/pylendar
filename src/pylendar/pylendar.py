#! /usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dateutil",
#     "astronomy-engine",
#     "lunardate",
# ]
# ///

"""A simple Python implementation of the BSD calendar(1) utility.

This script reads a text file with dated events and prints the events
scheduled for today and tomorrow. If today is a Friday, it also includes
events for Saturday, Sunday, and Monday.

Usage:
    python calendar.py [-f /path/to/calendar_file]

The calendar file should have one event per line, formatted as:
    <Date><TAB><Event Description>

Supported Date Formats:
    - YYYY/M/D        (e.g., 2026/2/17) - specific date with year
    - YYYY-MM-DD      (e.g., 2026-02-17) - ISO date format
    - MM/DD           (e.g., 07/09)
    - Month DD        (e.g., Jul 9, July 9)
    - * DD / *DD      (e.g., * 9, *15) - DDth of every month
    - DD *            (e.g., 15 *) - DDth of every month (reversed)
    - **  / * *       Every day of the year
    - Month* / Month *(e.g., June*, Jun *) - every day of that month
    - Month Wkday+N   (e.g., May Sun+2) - Nth weekday of a month
    - Month Wkday-N   (e.g., May Mon-1) - last Nth weekday of a month
    - MM/Wkday+N      (e.g., 03/Sun-1) - Nth weekday of numbered month
    - MM/WkdayOrd     (e.g., 10/MonSecond) - Nth weekday using ordinal
    - Month/WkdayOrd  (e.g., Oct/SatFourth-2) - with optional day offset
    - Month/DD        (e.g., apr/01) - month name with slash
    - * Wkday+N       (e.g., * Fri+3) - Nth weekday of every month
    - WkdayOrd Month  (e.g., SunFirst Aug) - ordinal weekday then month
    - DD Month        (e.g., 01 Jan) - day then month name
    - Easter          Catholic Easter
    - ChineseNewYear  First day of the Chinese year
    - Special+/-N     (e.g., Easter-2, FullMoon+1) - offset from special date
    - Weekday         (e.g., Friday) - every occurrence in the year
    - Month           (e.g., June) - the 1st of that month

Example calendar file (save as 'calendar'):
#------------------------------------------
# My Personal Calendar
#------------------------------------------
01/01	New Year's Day
Easter  Happy Easter!
Jul 4	US Independence Day
12/25	Christmas Day

* 15	Pay the rent

07/09	Finish the Python calendar script
07/10	Deploy the new script
07/11	TGIF
07/14	Monday morning meeting
#------------------------------------------
"""

import argparse
import calendar
import contextlib
import datetime
import locale
import logging
import os
import re
import sys
from abc import ABC, abstractmethod
from collections.abc import Sequence
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

log = logging.getLogger("pylendar")


__version__ = "0.5.0"

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
ORDINALS_RE = "|".join(ORDINAL_MAP)

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
        dates: DateSet = set()
        for month in range(1, 13):
            result = _find_nth_weekday(year, month, self.weekday, self.n)
            if result:
                dates.add(result)
        return dates


@dataclass(frozen=True)
class OffsetDateExpr(DateExpr):
    """A date expression offset by a number of days (e.g., Easter-2 for Good Friday)."""

    base: DateExpr
    offset: int

    @property
    def variable(self) -> bool:  # type: ignore[override]
        """Delegate to the base expression."""
        return self.base.variable

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
        days_ahead = (self.weekday - jan1.weekday()) % 7
        first = jan1 + datetime.timedelta(days=days_ahead)
        dates: DateSet = set()
        current = first
        while current.year == year:
            dates.add(current)
            current += datetime.timedelta(weeks=1)
        return dates


def main(argv: list[str] | None = None) -> None:
    """Run the calendar utility."""
    setup_logging()
    try:
        return cli(argv)
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit("Interrupted by user.")


def cli(argv: list[str] | None = None) -> None:
    """Command-line interface for the calendar utility."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.verbose > 0:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    utc_offset, longitude = resolve_coordinates(args.U, args.l)

    if args.D is not None:
        print_diagnostic(args.D, args.today.year, utc_offset, longitude)
        return

    calendar_path = (
        Path(args.file) if args.file else find_calendar(DEFAULT_CALENDAR_PATHS)
    )
    if not calendar_path.is_file():
        log.debug(f"Calendar file '{calendar_path}' not found, exiting...")
        return

    friday = bsd_to_python_weekday(args.F)
    ahead_value = args.W if args.W is not None else args.A
    opts = CalendarOptions(
        ahead=ahead_value,
        behind=args.B,
        friday=friday,
        weekday=args.w,
        utc_offset_hours=utc_offset,
        include_dirs=DEFAULT_CALENDAR_PATHS,
    )
    try:
        lines = process_calendar(calendar_path, args.today, opts)
    except (OSError, SyntaxError) as e:
        sys.exit(f"Error: Could not read calendar file: {e}")

    for line in lines:
        print(line)


@dataclass(frozen=True)
class CalendarDirectives:
    """Global directives parsed from a calendar file (LANG=, SEQUENCE=)."""

    lang: str | None = None
    sequence: tuple[str, ...] | None = None


@dataclass
class CalendarOptions:
    """Options for calendar processing."""

    ahead: int | None = None
    behind: int = 0
    friday: int = 4
    weekday: bool = False
    utc_offset_hours: float = 0
    include_dirs: Sequence[Path] = ()


def process_calendar(
    calendar_path: Path,
    today: datetime.date,
    options: CalendarOptions | None = None,
) -> list[str]:
    """Process a calendar file and return formatted event strings.

    This is the core pipeline shared by ``cli()`` and test fixtures.
    """
    opts = options or CalendarOptions()
    processor = SimpleCPP(include_dirs=opts.include_dirs)
    calendar_lines = join_continuation_lines(processor.process_file(calendar_path))

    ahead_days, behind_days = get_ahead_behind(
        today, ahead=opts.ahead, behind=opts.behind, friday=opts.friday
    )
    dates_to_check = get_dates_to_check(today, ahead=ahead_days, behind=behind_days)
    date_exprs = parse_special_dates(calendar_lines, today.year, opts.utc_offset_hours)
    directives = extract_directives(calendar_lines)
    date_parser = DateStringParser(date_exprs, directives=directives)

    log.debug(f"File path = {calendar_path}")
    log.debug(f"Today is {today}")
    log.debug(f"Ahead = {ahead_days}, Behind = {behind_days}")
    log.debug(f"dates_to_check = {dates_to_check}")
    log.debug(f"date_exprs = {date_exprs}")

    matching_events = [
        event
        for line in calendar_lines
        for event in get_matching_events(line, dates_to_check, date_parser)
    ]
    return [
        format_event(event, weekday=opts.weekday) for event in sorted(matching_events)
    ]


def join_continuation_lines(lines: list[str]) -> list[str]:
    """Join continuation lines with their parent line.

    BSD calendar files allow multi-line events where continuation lines
    start with a tab character (no date before the tab).
    """
    result: list[str] = []
    for line in lines:
        if line.startswith("\t") and result:
            # Continuation line - append to previous
            result[-1] += "\n" + line
        else:
            result.append(line)
    return result


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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


class DateStringParser:
    """Parser for date strings from calendar files."""

    month_map: dict[str, int]
    weekday_map: dict[str, int]
    ordinal_map: dict[str, int]
    ordinals_re: str

    def __init__(
        self,
        date_exprs: dict[str, DateExpr] | None = None,
        *,
        directives: CalendarDirectives | None = None,
    ) -> None:
        """Initialize the parser with optional date expressions and directives."""
        self.date_exprs = date_exprs or {}
        dirs = directives or CalendarDirectives()

        # Start with system locale names
        self.month_map = self.build_month_map()
        self.weekday_map = self.build_weekday_map()

        # Layer C/English names on top
        with calendar.different_locale("C"):  # type: ignore[arg-type]
            self.month_map.update(self.build_month_map())
            self.weekday_map.update(self.build_weekday_map())

        # Layer LANG= locale names on top, if set
        if dirs.lang and dirs.lang.lower().split(".")[0] not in _LANG_NOOP:
            try:
                with calendar.different_locale(dirs.lang):  # type: ignore[arg-type]
                    self.month_map.update(self.build_month_map())
                    self.weekday_map.update(self.build_weekday_map())
            except locale.Error:
                log.warning(f"LANG={dirs.lang}: locale not available; ignoring")

        # Build per-instance ordinal map
        self.ordinal_map = dict(ORDINAL_MAP)
        if dirs.sequence:
            for word, n in zip(dirs.sequence, (1, 2, 3, 4, 5, -1), strict=True):
                self.ordinal_map[word.lower()] = n
        self.ordinals_re = "|".join(self.ordinal_map)

    @staticmethod
    def build_month_map() -> dict[str, int]:
        """Build a map of month names and abbreviations to their respective numbers.

        This uses the current locale at the time of execution.
        """
        return {
            m.lower(): n
            for s in (calendar.month_name, calendar.month_abbr)
            for n, m in enumerate(s)
            if m
        }

    @staticmethod
    def build_weekday_map() -> dict[str, int]:
        """Build a map of weekday names and abbreviations to their numbers (Monday=0).

        This uses the current locale at the time of execution.
        """
        return {
            d.lower(): n
            for s in (calendar.day_name, calendar.day_abbr)
            for n, d in enumerate(s)
        }

    def parse(self, date_str: str) -> DateExpr | None:
        """Parse a date string from the calendar file.

        Supports special dates, aliases, and standard date formats.
        Pattern order matters — more specific patterns are tried first.
        """
        date_str = date_str.strip().lower()

        # Special date with offset (e.g., Easter-2, FullMoon+1)
        # Must precede plain special-date lookup
        match = re.fullmatch(r"([a-z]+)([+-])(\d+)", date_str)
        if match:
            offset = _parse_signed_int(match, 2, 3)
            if base := self.date_exprs.get(match.group(1)):
                return OffsetDateExpr(base, offset)

        # Plain special dates and aliases
        if date_expr := self.date_exprs.get(date_str):
            return date_expr

        # Standalone weekday (e.g., Friday) — checked before regex
        if date_str in self.weekday_map:
            return EveryWeekday(self.weekday_map[date_str])

        # Standalone month name (e.g., June) — matches the 1st of that month
        if date_str in self.month_map:
            return FixedDate(self.month_map[date_str], 1)

        return self._parse_format_patterns(date_str)

    def _parse_ordinal_weekday(self, date_str: str) -> DateExpr | None:
        """Parse BSD ordinal weekday formats (e.g., 10/MonSecond, Oct/SatFourth-2)."""
        ordinals = self.ordinals_re

        # MM/WkdayOrdinal with optional offset (e.g., 10/monsecond, 01/monthird)
        match = re.fullmatch(rf"(\d{{1,2}})/([a-z]+)({ordinals})([+-]\d+)?", date_str)
        if match:
            month = int(match.group(1))
            wkday_name = match.group(2)
        else:
            # Month/WkdayOrdinal with optional offset (e.g., oct/satfourth-2)
            match = re.fullmatch(rf"([a-z]+)/([a-z]+)({ordinals})([+-]\d+)?", date_str)
            if not match:
                return None
            month_name = match.group(1)
            if month_name not in self.month_map:
                return None
            month = self.month_map[month_name]
            wkday_name = match.group(2)

        if wkday_name not in self.weekday_map:
            return None
        n = self.ordinal_map[match.group(3)]
        base: DateExpr = NthWeekdayOfMonth(month, self.weekday_map[wkday_name], n)
        if match.group(4):
            base = OffsetDateExpr(base, int(match.group(4)))
        return base

    @staticmethod
    def _parse_mm_dd(date_str: str) -> DateExpr | None:
        """Parse MM/DD format (e.g., 07/09)."""
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})", date_str)
        if match:
            return FixedDate(int(match.group(1)), int(match.group(2)))
        return None

    @staticmethod
    def _parse_full_date(date_str: str) -> DateExpr | None:
        """Parse YYYY/M/D or YYYY-MM-DD format (e.g., 2026/2/17, 2026-02-17)."""
        match = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", date_str)
        if match:
            return FixedDate(
                month=int(match.group(2)),
                day=int(match.group(3)),
                year=int(match.group(1)),
            )
        return None

    def _parse_month_slash_dd(self, date_str: str) -> DateExpr | None:
        """Parse Month/DD format (e.g., apr/01, dec/07, jan/06)."""
        match = re.fullmatch(r"([a-z]+)/(\d{1,2})", date_str)
        if match:
            month_name = match.group(1)
            if month_name in self.month_map:
                return FixedDate(self.month_map[month_name], int(match.group(2)))
        return None

    def _parse_mm_wkday_offset(self, date_str: str) -> DateExpr | None:
        """Parse MM/Weekday+/-N format (e.g., 03/Sun-1, 11/Wed+3, 12/Sun+1)."""
        match = re.fullmatch(r"(\d{1,2})/([a-z]+)([+-])(\d+)", date_str)
        if match:
            month = int(match.group(1))
            wkday_name = match.group(2)
            if wkday_name in self.weekday_map:
                n = _parse_signed_int(match, 3, 4)
                return NthWeekdayOfMonth(month, self.weekday_map[wkday_name], n)
        return None

    def _parse_month_wkday_offset(self, date_str: str) -> DateExpr | None:
        """Parse Month Weekday+/-N format (e.g., May Sun+2, Nov Thu+4, May Mon-1)."""
        match = re.fullmatch(r"([a-z]+)\s+([a-z]+)([+-])(\d+)", date_str)
        if match:
            month_name, wkday_name = match.group(1), match.group(2)
            n = _parse_signed_int(match, 3, 4)
            if month_name in self.month_map and wkday_name in self.weekday_map:
                return NthWeekdayOfMonth(
                    self.month_map[month_name],
                    self.weekday_map[wkday_name],
                    n,
                )
        return None

    def _parse_month_dd(self, date_str: str) -> DateExpr | None:
        """Parse Month DD format (e.g., July 9, Jul 9)."""
        match = re.fullmatch(r"([a-z]{3,24})\s+(\d{1,2})", date_str)
        if match:
            month_name = match.group(1)
            if month_name in self.month_map:
                return FixedDate(self.month_map[month_name], int(match.group(2)))
        return None

    def _parse_wildcard_wkday(self, date_str: str) -> DateExpr | None:
        """Parse * Weekday+/-N format (e.g., * Fri+3)."""
        match = re.fullmatch(r"\*\s+([a-z]+)([+-])(\d+)", date_str)
        if match:
            wkday_name = match.group(1)
            n = _parse_signed_int(match, 2, 3)
            if wkday_name in self.weekday_map:
                return NthWeekdayEveryMonth(self.weekday_map[wkday_name], n)
        return None

    @staticmethod
    def _parse_wildcard_day(date_str: str) -> DateExpr | None:
        """Parse * DD or *DD format (e.g., * 9, *15)."""
        match = re.fullmatch(r"\*\s*(\d{1,2})", date_str)
        if match:
            return WildcardDay(int(match.group(1)))
        return None

    @staticmethod
    def _parse_every_day(date_str: str) -> DateExpr | None:
        """Parse ** or * * format (every day of the year)."""
        if re.fullmatch(r"\*\s*\*", date_str):
            return EveryDay()
        return None

    def _parse_month_wildcard(self, date_str: str) -> DateExpr | None:
        """Parse Month* or Month * format (every day of that month, e.g., June*)."""
        match = re.fullmatch(r"([a-z]+)\s*\*", date_str)
        if match:
            month_name = match.group(1)
            if month_name in self.month_map:
                return EveryDayOfMonth(self.month_map[month_name])
        return None

    def _parse_wildcard_day_reversed(self, date_str: str) -> DateExpr | None:
        """Parse DD * format (e.g., 15 * for 15th of every month)."""
        match = re.fullmatch(r"(\d{1,2})\s+\*", date_str)
        if match:
            return WildcardDay(int(match.group(1)))
        return None

    def _parse_wkday_ord_month(self, date_str: str) -> DateExpr | None:
        """Parse WkdayOrd Month format (e.g., SunFirst Aug, SunThird Jul)."""
        ordinals = self.ordinals_re
        match = re.fullmatch(rf"([a-z]+)({ordinals})\s+([a-z]+)", date_str)
        if match:
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

    def _parse_dd_month(self, date_str: str) -> DateExpr | None:
        """Parse DD Month format (e.g., 01 Jan, 21 Apr)."""
        match = re.fullmatch(r"(\d{1,2})\s+([a-z]+)", date_str)
        if match:
            month_name = match.group(2)
            if month_name in self.month_map:
                return FixedDate(self.month_map[month_name], int(match.group(1)))
        return None

    def _parse_format_patterns(self, date_str: str) -> DateExpr | None:
        """Parse regex-based date format patterns."""
        # YYYY/M/D, YYYY-MM-DD, MM/Wkday+N, MM/WkdayOrd, Month/WkdayOrd,
        # Month/DD, or MM/DD
        if "/" in date_str or ("-" in date_str and date_str[0].isdigit()):
            return (
                self._parse_full_date(date_str)
                or self._parse_mm_wkday_offset(date_str)
                or self._parse_ordinal_weekday(date_str)
                or self._parse_month_slash_dd(date_str)
                or self._parse_mm_dd(date_str)
            )

        # Non-slash patterns, tried most-specific first
        return (
            self._parse_month_wkday_offset(date_str)
            or self._parse_month_dd(date_str)
            or self._parse_month_wildcard(date_str)
            or self._parse_every_day(date_str)
            or self._parse_wildcard_wkday(date_str)
            or self._parse_wildcard_day(date_str)
            or self._parse_wkday_ord_month(date_str)
            or self._parse_wildcard_day_reversed(date_str)
            or self._parse_dd_month(date_str)
        )


def remove_comments(code: str) -> str:
    """Remove comments from C/C++ code.

    This function removes both block comments (/* ... */) and line comments (// ...).

    However, it does not handle nested comments or comments within strings.
    """
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)  # Remove block comments
    return re.sub(r"(?:^|\s)//.*", "", code)  # Remove line comments


class SimpleCPP:
    """A simple C/C++ preprocessor emulator."""

    def __init__(self, include_dirs: Sequence[Path | str]) -> None:
        """Initialize the preprocessor with include directories."""
        self.include_dirs = [Path(d) for d in include_dirs]
        self.included_files: set[Path] = set()
        stringified_dirs = [str(d) for d in include_dirs]
        log.debug(f"Including calendar files from directories: {stringified_dirs}")

    def process_file(self, path: Path) -> list[str]:
        """Process a C/C++ source file, resolving includes and removing comments."""
        abs_path = path.resolve()
        if abs_path in self.included_files:
            log.debug(f"Skipping {abs_path.name}: already included")
            return []
        log.debug(f"Processing {abs_path.name}")
        self.included_files.add(abs_path)

        lines = []
        for line in remove_comments(path.read_text(encoding="utf-8")).splitlines():
            stripped = line.strip()

            if stripped.startswith("#include"):
                match = re.match(r'#include\s+[<"]([^">]+)[">]', stripped)
                if match:
                    include_target = Path(match.group(1))
                    include_file = self.resolve_include(include_target, abs_path.parent)
                    if include_file:
                        lines.extend(self.process_file(include_file))
                    else:
                        msg = f"Included file not found: {include_target}"
                        log.warning(msg)
                else:
                    msg = f"Malformed include directive: {line}"
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
    """Derive UTC offset and east longitude from -U and -l flags.

    Returns:
        (utc_offset_hours, east_longitude)

    """
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
    """Get the dates of equinoxes and solstices for a given year.

    Returns:
        dict mapping season names to their dates

    """
    return {
        name: dt.date() for name, dt in _get_season_datetimes(year, utc_offset_hours)
    }


def _search_moon_phases(
    year: int, phase_angle: int, utc_offset_hours: float
) -> list[datetime.datetime]:
    """Return all moon phase datetimes for a year with UTC offset applied."""
    start_time = astronomy.Time.Make(year, 1, 1, 0, 0, 0)
    offset = datetime.timedelta(hours=utc_offset_hours)
    results: list[datetime.datetime] = []
    search_time = start_time
    while True:
        moon_phase = astronomy.SearchMoonPhase(phase_angle, search_time, 40)
        if moon_phase is None:
            break
        dt = moon_phase.Utc() + offset
        if dt.date().year != year:
            break
        results.append(dt)
        search_time = astronomy.Time.AddDays(moon_phase, 1)
    return results


def get_moon_phases(year: int, utc_offset_hours: float = 0) -> dict[str, DateSet]:
    """Get all new and full moon dates for a given year.

    Returns:
        dict mapping "newmoon" and "fullmoon" to sets of dates

    """
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
    """Return equinox/solstice datetimes with UTC offset applied.

    Returns (keyword, datetime) pairs using calendar keyword names.
    """
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


def parse_special_dates(
    calendar_lines: list[str], year: int, utc_offset_hours: float = 0
) -> dict[str, DateExpr]:
    """Parse special date definitions and aliases from the calendar file.

    Returns:
        dict mapping date keywords to DateExpr objects

    """
    date_exprs: dict[str, DateExpr] = {}

    # Start with known special dates
    date_exprs["easter"] = ResolvedDate.of(dateutil.easter.easter(year))
    date_exprs["paskha"] = ResolvedDate.of(
        dateutil.easter.easter(year, method=dateutil.easter.EASTER_ORTHODOX)
    )
    date_exprs["chinesenewyear"] = ResolvedDate.of(LunarDate(year, 1, 1).toSolarDate())

    # Add astronomical season dates
    for name, date in get_seasons(year, utc_offset_hours).items():
        date_exprs[name] = ResolvedDate.of(date)

    # Add moon phases as recurring dates
    for name, dates in get_moon_phases(year, utc_offset_hours).items():
        date_exprs[name] = ResolvedDate(frozenset(dates))

    # Parse aliases from calendar file
    for line in calendar_lines:
        if "=" in line and "\t" not in line:
            left, right = line.split("=", 1)
            left = left.strip().lower()
            right = right.strip().lower()
            # If either side is a known date expr, add the alias
            if left in date_exprs and right not in date_exprs:
                date_exprs[right] = date_exprs[left]
            elif right in date_exprs:
                date_exprs[left] = date_exprs[right]

    return date_exprs


_LANG_NOOP = frozenset({"c", "posix", "utf-8", "utf8"})


def extract_directives(calendar_lines: list[str]) -> CalendarDirectives:
    """Extract LANG= and SEQUENCE= directives from preprocessed calendar lines.

    Directives are lines without tabs whose left-hand side is ``LANG`` or
    ``SEQUENCE`` (case-sensitive).  Last occurrence wins.
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


def parse_today_arg(t_str: str) -> datetime.date:
    """Parse the -t argument and return a datetime.date object.

    Acceptable formats:
      - OpenBSD/Debian positional: dd, mmdd, yymmdd, ccyymmdd
      - macOS/FreeBSD dot-separated: dd.mm, dd.mm.year
    """
    t_str = t_str.strip()
    if "." in t_str:
        return _parse_dot_date(t_str)
    # cSpell:ignore mmdd, ccyymmdd
    if re.fullmatch(r"\d{2}", t_str):
        # dd
        today = datetime.date.today()
        return datetime.date(today.year, today.month, int(t_str))
    if re.fullmatch(r"\d{4}", t_str):
        # mmdd
        today = datetime.date.today()
        return datetime.date(today.year, int(t_str[:2]), int(t_str[2:]))
    if re.fullmatch(r"\d{6}", t_str):
        # yymmdd
        yy = int(t_str[:2])
        mm = int(t_str[2:4])
        dd = int(t_str[4:])
        # Determine the century based on the year
        # If yy is between 69 and 99, assume 1900s; otherwise assume 2000s
        cc = 19 if 69 <= yy <= 99 else 20  # noqa: PLR2004
        year = cc * 100 + yy
        return datetime.date(year, mm, dd)
    if re.fullmatch(r"\d{8}", t_str):
        # ccyymmdd
        year = int(t_str[:4])
        mm = int(t_str[4:6])
        dd = int(t_str[6:])
        return datetime.date(year, mm, dd)
    msg = f"Invalid -t date format: {t_str}"
    raise argparse.ArgumentTypeError(msg)


def get_dates_to_check(
    today: datetime.date, ahead: int = 1, behind: int = 0
) -> DateSet:
    """Determine the set of dates to check for events, given -A and -B options."""
    return {
        today + datetime.timedelta(days=offset) for offset in range(-behind, ahead + 1)
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the calendar utility."""
    parser = argparse.ArgumentParser(
        description="A Python replacement for the BSD calendar utility.",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Path to the calendar file (default: 'calendar' in the current directory)",
    )
    ahead_group = parser.add_mutually_exclusive_group()
    ahead_group.add_argument(
        "-A",
        type=int,
        default=None,
        metavar="num",
        help="Print lines from today and next num days (forward, future). "
        "Defaults to 1, except on Fridays the default is 3.",
    )
    ahead_group.add_argument(
        "-W",
        type=int,
        default=None,
        metavar="num",
        # FreeBSD/macOS equivalent of -A that disables Friday look-ahead.
        help="Print lines from today and next num days (forward, future). "
        "Disables the Friday look-ahead expansion.",
    )
    parser.add_argument(
        "-B",
        type=int,
        default=0,
        metavar="num",
        help="Print lines from today and previous num days (backward, past). "
        "Default 0.",
    )
    parser.add_argument(
        "-F",
        type=int,
        default=5,
        metavar="friday",
        # Day numbering follows BSD tm_wday convention.
        help='Set which day is "Friday" (the day before the weekend). '
        "Day numbering: 0=Sun, 1=Mon, ..., 5=Fri, 6=Sat. Default 5.",
    )
    parser.add_argument(
        "-l",
        type=float,
        default=None,
        metavar="longitude",
        help="East longitude of your stranding. Default derived from UTC offset.",
    )
    parser.add_argument(
        "-U",
        type=float,
        default=None,
        metavar="utc-offset",
        help="UTC offset in hours (e.g. -8 for PST, 1 for CET). "
        "Default derived from system timezone.",
    )
    parser.add_argument(
        "-D",
        choices=["sun", "moon"],
        default=None,
        metavar="sun|moon",
        help="Print diagnostic sun or moon information and exit.",
    )
    parser.add_argument(
        "-t",
        metavar="date",
        type=parse_today_arg,
        default=datetime.date.today(),
        dest="today",
        # Positional format from OpenBSD/Debian; dot-separated from macOS/FreeBSD.
        help="Act like the specified value is 'today' instead of using the current "
        "date. Accepts [[[cc]yy]mm]dd (if yy is between 69 and 99, cc defaults "
        "to 19; otherwise 20) or dd.mm[.year].",
    )
    # NOTE: NetBSD uses -w for "extra Friday days" (different meaning).
    # We follow the OpenBSD/Debian convention.
    parser.add_argument(
        "-w",
        action="store_true",
        default=False,
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


def get_ahead_behind(
    today: datetime.date,
    ahead: int | None = None,
    behind: int = 0,
    *,
    friday: int = 4,
) -> tuple[int, int]:
    """Determine the number of days to look ahead and behind based on the arguments.

    Args:
        today: The current date
        ahead: Number of days ahead to look (None for default behavior)
        behind: Number of days behind to look (default: 0)
        friday: Which Python weekday (0=Mon..6=Sun) triggers the 3-day look-ahead.
            Default 4 (Friday).

    Returns:
        tuple: (ahead_days, behind_days)

    """
    weekday = today.weekday()
    ahead_days = ahead if ahead is not None else 3 if weekday == friday else 1
    behind_days = behind
    return ahead_days, behind_days


def replace_age_in_description(description: str, check_date: datetime.date) -> str:
    """Replace [YYYY] with calculated age in event description.

    Args:
        description: Event description that may contain [YYYY] placeholder
        check_date: Date to calculate age from

    Returns:
        Description with [YYYY] replaced by age, or original if no placeholder

    """
    if match := re.search(r"\[(\d{4})\]", description):
        year_val = int(match.group(1))
        age = check_date.year - year_val
        return description.replace(f"[{match.group(1)}]", str(age))
    return description


def get_matching_events(
    line: str,
    dates_to_check: DateSet,
    parser: DateStringParser,
) -> list[Event]:
    """Get events from this line that match any of the target dates.

    Returns one Event per matching date, or an empty list if nothing matches.
    """
    if not line.strip() or "\t" not in line:
        return []

    date_str, event_description = line.split("\t", 1)

    expr = parser.parse(date_str)
    explicit_variable = False

    if expr is None and date_str.rstrip().endswith("*"):
        explicit_variable = True
        date_str = date_str.rstrip()[:-1]
        expr = parser.parse(date_str)

    if expr is None:
        return []

    years = {d.year for d in dates_to_check}
    resolved: DateSet = set()
    for year in years:
        resolved |= expr.resolve(year)
    matching = resolved & dates_to_check

    variable = explicit_variable or expr.variable
    return [
        Event(d, replace_age_in_description(event_description, d), variable=variable)
        for d in matching
    ]


def find_calendar(look_in: Sequence[Path]) -> Path:
    """Find the calendar file in standard locations.

    The BSD calendar(1) utility uses chdir to the calendar directory so that
    relative #include paths resolve correctly. We don't need that here because
    SimpleCPP.resolve_include() already passes each file's parent directory as
    look_first, resolving includes relative to the including file (correct C
    preprocessor semantics) without relying on the process working directory.
    """
    calendar_dir = os.environ.get("CALENDAR_DIR")
    first = Path(calendar_dir) if calendar_dir else Path.cwd()
    dirs = [first, *look_in]
    my_dir = (Path.home() / ".calendar").resolve()
    if my_dir.is_dir():
        dirs.insert(1, my_dir)
    for dir_path in dirs:
        file = dir_path / "calendar"
        if file.is_file():
            return file.resolve()
    return Path("calendar")


if __name__ == "__main__":  # pragma: no cover
    main()
