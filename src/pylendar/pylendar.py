#! /usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dateutil",
#     "astronomy-engine",
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
    - MM/DD       (e.g., 07/09)
    - Month DD    (e.g., Jul 9, July 9)
    - * DD        (e.g., * 9) - for the nth day of any month
    - Easter      Catholic Easter

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
import datetime
import logging
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

try:
    import dateutil.easter
except ImportError:
    sys.exit("Error: This script requires the 'python-dateutil' package.")

try:
    import astronomy
except ImportError:
    sys.exit("Error: This script requires the 'astronomy-engine' package.")

log = logging.getLogger("pylendar")


XDG_CONFIG_HOME = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
DEFAULT_CALENDAR_PATHS: list[Path] = [
    Path.home() / ".calendar",
    XDG_CONFIG_HOME / "calendar",
    Path("/etc/calendar"),
    Path("/usr/share/calendar"),
    Path("/usr/local/share/calendar"),
]

SpecialDates = dict[str, datetime.date]


class ParsedDate(NamedTuple):
    """Result of parsing a date string."""

    month: int | None
    day: int | None


def main() -> None:
    """Run the calendar utility."""
    setup_logging()
    try:
        return cli()
    except KeyboardInterrupt:
        sys.exit("Interrupted by user.")


def cli() -> None:
    """Command-line interface for the calendar utility."""
    parser = build_parser()
    args = parser.parse_args()
    if args.verbose > 0:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    calendar_lines = []
    calendar_path = (
        Path(args.file) if args.file else find_calendar(DEFAULT_CALENDAR_PATHS)
    )
    if not calendar_path.is_file():
        log.debug(f"Calendar file '{calendar_path}' not found, exiting...")
        return
    processor = SimpleCPP(include_dirs=DEFAULT_CALENDAR_PATHS)
    try:
        calendar_lines = processor.process_file(calendar_path)
    except OSError as e:
        sys.exit(f"Error: Could not read calendar file: {e}")
    calendar_lines = join_continuation_lines(calendar_lines)

    ahead, behind = get_ahead_behind(args.today, ahead=args.A, behind=args.B)
    dates_to_check = get_dates_to_check(args.today, ahead=ahead, behind=behind)

    # Parse special dates and aliases once
    special_dates, recurring_events = parse_special_dates(
        calendar_lines, args.today.year
    )

    # Create a DateStringParser instance with special dates
    date_parser = DateStringParser(special_dates)

    log.debug(f"File path = {calendar_path}")
    log.debug(f"Today is {args.today}")
    log.debug(f"Ahead = {ahead}, Behind = {behind}")
    log.debug(f"dates_to_check = {dates_to_check}")
    log.debug(f"special_dates = {special_dates}")

    # Collect calendar events matching any of the current dates
    matching_events = [
        event
        for line in calendar_lines
        if (
            event := get_matching_event(
                line, dates_to_check, date_parser, recurring_events
            )
        )
    ]

    # Sort events by date and print them
    for event in sorted(matching_events):
        print(event)


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
        formatted_date = f"{self.date:%b} {self.date.day:2}"
        return f"{formatted_date}\t{self.description}"


class DateStringParser:
    """Parser for date strings from calendar files."""

    month_map: dict[str, int]

    def __init__(
        self,
        special_dates: SpecialDates | None = None,
    ) -> None:
        """Initialize the parser with optional special dates."""
        self.special_dates = special_dates or {}
        self.month_map = self.build_month_map()

        # Ensure we have month names in US English locale
        with calendar.different_locale("C"):  # type: ignore[arg-type]
            self.month_map.update(self.build_month_map())

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

    def parse(self, date_str: str) -> ParsedDate:
        """Parse a date string from the calendar file.

        Supports special dates and aliases.
        """
        date_str = date_str.strip().lower()

        # Handle special dates and aliases
        if special_date := self.special_dates.get(date_str):
            return ParsedDate(special_date.month, special_date.day)

        # Pattern 1: MM/DD (e.g., 07/09)
        match = re.fullmatch(r"(?P<month>\d{1,2})/(?P<day>\d{1,2})", date_str)
        if match:
            month = int(match.group("month"))
            day = int(match.group("day"))
            return ParsedDate(month, day)

        # Pattern 2: Month DD (e.g., July 9 or Jul 9)
        match = re.fullmatch(
            r"(?P<month_name>[a-z]{3,24})\s+(?P<day>\d{1,2})", date_str
        )
        if match:
            month_name = match.group("month_name")
            day = int(match.group("day"))
            if month_name in self.month_map:
                return ParsedDate(self.month_map[month_name], day)

        # Pattern 3: * DD (e.g., * 9)
        match = re.fullmatch(r"\*\s+(?P<day>\d{1,2})", date_str)
        if match:
            day = int(match.group("day"))
            return ParsedDate(None, day)  # None for month signifies a wildcard

        return ParsedDate(None, None)


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
                        log.warning(f"Warning: {msg}")
                else:
                    msg = f"Malformed include directive: {line}"
                    raise SyntaxError(msg)
            elif re.match(r"#(define|ifndef|endif)", stripped):
                # Skip basic preprocessor guards (emulated via included_files)
                continue
            elif stripped.startswith("#"):
                # Handle other preprocessor directives (e.g., #define, #ifdef)
                # For now, we just skip them as they are not implemented
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


def get_seasons(year: int) -> SpecialDates:
    """Get the dates of equinoxes and solstices for a given year.

    Returns:
        dict mapping season names to their dates

    """
    seasons = astronomy.Seasons(year)
    return {
        "marequinox": seasons.mar_equinox.Utc().date(),
        "junsolstice": seasons.jun_solstice.Utc().date(),
        "sepequinox": seasons.sep_equinox.Utc().date(),
        "decsolstice": seasons.dec_solstice.Utc().date(),
    }


def get_moon_phases(year: int) -> dict[str, set[datetime.date]]:
    """Get all new and full moon dates for a given year.

    Returns:
        dict mapping "newmoon" and "fullmoon" to sets of dates

    """
    moon_phases: dict[str, set[datetime.date]] = {"newmoon": set(), "fullmoon": set()}
    start_time = astronomy.Time.Make(year, 1, 1, 0, 0, 0)

    for phase_name, phase_angle in [("newmoon", 0), ("fullmoon", 180)]:
        search_time = start_time
        while True:
            moon_phase = astronomy.SearchMoonPhase(phase_angle, search_time, 40)
            if moon_phase is None:
                break
            phase_date = moon_phase.Utc().date()
            if phase_date.year != year:
                break
            moon_phases[phase_name].add(phase_date)
            search_time = astronomy.Time.AddDays(moon_phase, 1)

    return moon_phases


def parse_special_dates(
    calendar_lines: list[str], year: int
) -> tuple[SpecialDates, dict[str, set[datetime.date]]]:
    """Parse special date definitions and aliases from the calendar file.

    Returns:
        tuple of (special_dates, recurring_events)
        - special_dates: dict of single-occurrence dates (Easter, seasons)
        - recurring_events: dict of multiple-occurrence dates (moon phases)

    """
    # Start with known special dates
    special_dates = {"easter": dateutil.easter.easter(year)}

    # Add astronomical dates
    special_dates.update(get_seasons(year))
    recurring_events = get_moon_phases(year)

    # Parse aliases from calendar file
    for line in calendar_lines:
        if "=" in line and "\t" not in line:
            left, right = line.split("=", 1)
            left = left.strip().lower()
            right = right.strip().lower()
            # If either side is a known special date, add the alias
            if left in special_dates and right not in special_dates:
                special_dates[right] = special_dates[left]
            elif right in special_dates:
                special_dates[left] = special_dates[right]

    return special_dates, recurring_events


def parse_today_arg(t_str: str) -> datetime.date:
    """Parse the -t argument and return a datetime.date object.

    Acceptable formats are: dd, mmdd, yymmdd, ccyymmdd
    """
    t_str = t_str.strip()
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
) -> set[datetime.date]:
    """Determine the set of dates to check for events, given -A and -B options."""
    dates = set()
    for offset in range(-behind, ahead + 1):
        dates.add(today + datetime.timedelta(days=offset))
    return dates


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
    parser.add_argument(
        "-A",
        type=int,
        default=None,
        metavar="num",
        help="Print lines from today and next num days (forward, future). "
        "Defaults to 1, except on Fridays the default is 3.",
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
        "-t",
        metavar="[[[cc]yy]mm]dd",
        type=parse_today_arg,
        default=datetime.date.today(),
        dest="today",
        help="Act like the specified value is 'today' instead of using the current "
        "date. If yy is specified, but cc is not, a value for yy between 69 and 99 "
        "results in a cc value of 19. Otherwise, a cc value of 20 is used.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times).",
    )
    return parser


def get_ahead_behind(
    today: datetime.date, ahead: int | None = None, behind: int = 0
) -> tuple[int, int]:
    """Determine the number of days to look ahead and behind based on the arguments.

    Args:
        today: The current date
        ahead: Number of days ahead to look (None for default behavior)
        behind: Number of days behind to look (default: 0)

    Returns:
        tuple: (ahead_days, behind_days)

    """
    friday = 4  # Friday is the 4th day of the week (0=Monday, 6=Sunday)
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
        return re.sub(r"\[(\d{4})\]", str(age), description)
    return description


def get_matching_event(
    line: str,
    dates_to_check: set[datetime.date],
    parser: DateStringParser,
    recurring_events: dict[str, set[datetime.date]] | None = None,
) -> Event | None:
    """Get the event from this line if it matches any of the target dates.

    Returns an Event object if the event matches any of the
    dates to check, or None if there's no match.
    """
    # Validate line has content and tab separator
    if not line.strip() or "\t" not in line:
        return None

    date_str, event_description = line.split("\t", 1)
    date_str_lower = date_str.strip().lower()

    # Check recurring events (moon phases) first
    if recurring_events and date_str_lower in recurring_events:
        for check_date in dates_to_check:
            if check_date in recurring_events[date_str_lower]:
                desc = replace_age_in_description(event_description, check_date)
                return Event(check_date, desc)
        return None

    # Normal date parsing for special dates and regular dates
    parsed = parser.parse(date_str)
    if parsed.day is None:
        return None

    for check_date in dates_to_check:
        # Check for wildcard month match (e.g., "* 15")
        is_wildcard_match = parsed.month is None and parsed.day == check_date.day

        # Check for specific month and day match
        is_full_date_match = (
            parsed.month == check_date.month and parsed.day == check_date.day
        )
        if is_wildcard_match or is_full_date_match:
            desc = replace_age_in_description(event_description, check_date)
            return Event(check_date, desc)

    return None


def find_calendar(look_in: Sequence[Path]) -> Path:
    """Find the calendar file in standard locations.

    The BSD calendar(1) utility uses chdir to the calendar directory so that
    relative #include paths resolve correctly. We don't need that here because
    SimpleCPP.resolve_include() already passes each file's parent directory as
    look_first, resolving includes relative to the including file (correct C
    preprocessor semantics) without relying on the process working directory.
    """
    dirs = [Path.cwd(), *look_in]
    my_dir = (Path.home() / ".calendar").resolve()
    if my_dir.is_dir():
        dirs.insert(1, my_dir)
    for dir_path in dirs:
        file = dir_path / "calendar"
        if file.is_file():
            return file.resolve()
    return Path("calendar")


if __name__ == "__main__":
    main()
