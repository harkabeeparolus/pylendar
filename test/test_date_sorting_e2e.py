# pylint: disable=duplicate-code
"""End-to-end tests for pylendar.

These tests verify the full pipeline: preprocessing, parsing, matching, sorting,
and CLI invocation.
"""

import datetime
import io
import sys

import pytest

from pylendar.pylendar import (
    DateStringParser,
    SimpleCPP,
    get_ahead_behind,
    get_dates_to_check,
    get_matching_event,
    join_continuation_lines,
    main,
    parse_special_dates,
)


@pytest.fixture
def run_calendar(tmp_path):
    """Fixture that processes calendar content and returns sorted event strings."""

    def _run(calendar_content, today, ahead=None, behind=0):
        calendar_file = tmp_path / "calendar"
        calendar_file.write_text(calendar_content)
        calendar_lines = join_continuation_lines(
            SimpleCPP(include_dirs=[]).process_file(calendar_file)
        )

        ahead_days, behind_days = get_ahead_behind(today, ahead=ahead, behind=behind)
        dates_to_check = get_dates_to_check(today, ahead=ahead_days, behind=behind_days)

        date_exprs = parse_special_dates(calendar_lines, today.year)
        date_parser = DateStringParser(date_exprs)
        matching_events = [
            event
            for line in calendar_lines
            if (event := get_matching_event(line, dates_to_check, date_parser))
        ]
        return [str(event) for event in sorted(matching_events)]

    return _run


def test_events_sorted_by_date(run_calendar):
    """Test that events from a calendar file are sorted by date."""
    calendar_content = """# Test calendar with mixed dates
07/06\tEvent on Saturday July 6th
07/04\tIndependence Day - July 4th
* 15\tMonthly rent due (wildcard)
07/05\tFriday party - July 5th
12/25\tChristmas (later in year)
* 10\tMonthly meeting (wildcard)
07/03\tWednesday event - July 3rd
"""

    # Test on July 5th (Friday) with ahead=3, behind=2
    # This will check July 3-8, covering our events
    today = datetime.date(2024, 7, 5)
    result = run_calendar(calendar_content, today, ahead=3, behind=2)

    # Expected result should be events in chronological order
    expected = [
        "Jul  3\tWednesday event - July 3rd",
        "Jul  4\tIndependence Day - July 4th",
        "Jul  5\tFriday party - July 5th",
        "Jul  6\tEvent on Saturday July 6th",
    ]

    assert result == expected


def test_events_with_wildcards_sorted_correctly(run_calendar):
    """Test that wildcard events (* DD) are sorted correctly with regular dates."""
    calendar_content = """# Mix of wildcards and specific dates
* 20\tPay credit card
07/18\tSpecific date event
* 05\tEarly monthly task
07/22\tLate July event
* 15\tMid-month task
07/10\tAnother specific date
"""

    # Test on July 15th with ahead=7, behind=7 to catch all our events
    today = datetime.date(2024, 7, 15)
    result = run_calendar(calendar_content, today, ahead=7, behind=7)

    # Should be sorted chronologically regardless of wildcard vs specific date
    expected = [
        "Jul 10\tAnother specific date",
        "Jul 15\tMid-month task",
        "Jul 18\tSpecific date event",
        "Jul 20\tPay credit card",
        "Jul 22\tLate July event",
    ]

    assert result == expected


def test_friday_vs_weekday_default_behavior(run_calendar):
    """Test that Friday and weekday use different default ahead values."""
    calendar_content = """# Events to test default behavior differences
07/10\tWednesday event
07/11\tThursday event
07/12\tFriday event
07/13\tSaturday event
07/14\tSunday event
"""

    # Test on Wednesday (weekday) - should default to ahead=1, behind=0
    wednesday = datetime.date(2024, 7, 10)
    result_wed = run_calendar(calendar_content, wednesday)
    expected_wed = [
        "Jul 10\tWednesday event",
        "Jul 11\tThursday event",
    ]
    assert result_wed == expected_wed

    # Test on Friday - should default to ahead=3, behind=0
    friday = datetime.date(2024, 7, 12)
    result_fri = run_calendar(calendar_content, friday)
    expected_fri = [
        "Jul 12\tFriday event",
        "Jul 13\tSaturday event",
        "Jul 14\tSunday event",
    ]
    assert result_fri == expected_fri


def test_continuation_lines(run_calendar):
    """Test that multi-line events with continuation lines are handled correctly."""
    calendar_content = """\
02/02\tLou Harrison dies in Lafayette, Indiana, en route to a festival
\tof his music at Ohio State University, 2003
02/02\tSimple single-line event
02/03\tThe Day The Music Died; Buddy Holly, Richie Valens, and the Big
\tBopper are killed in a plane crash outside Mason City, Iowa, 1959
"""

    today = datetime.date(2024, 2, 2)
    result = run_calendar(calendar_content, today, ahead=1)

    expected = [
        "Feb  2\tLou Harrison dies in Lafayette, Indiana, en route to a festival\n"
        "\tof his music at Ohio State University, 2003",
        "Feb  2\tSimple single-line event",
        "Feb  3\tThe Day The Music Died; Buddy Holly, Richie Valens, and the Big\n"
        "\tBopper are killed in a plane crash outside Mason City, Iowa, 1959",
    ]

    assert result == expected


def test_astronomical_seasons(run_calendar):
    """Test that astronomical season dates work correctly."""
    calendar_content = """# Astronomical seasons
MarEquinox	Spring begins
JunSolstice	Summer begins - longest day of the year
SepEquinox	Fall begins
DecSolstice	Winter begins - shortest day of the year
"""

    # Test around spring equinox 2026 (March 20)
    today = datetime.date(2026, 3, 20)
    result = run_calendar(calendar_content, today, ahead=1)

    expected = ["Mar 20*\tSpring begins"]
    assert result == expected

    # Test around winter solstice 2026 (December 21)
    today = datetime.date(2026, 12, 20)
    result = run_calendar(calendar_content, today, ahead=2)

    expected = ["Dec 21*\tWinter begins - shortest day of the year"]
    assert result == expected


def test_astronomical_moon_phases(run_calendar):
    """Test that moon phase dates work correctly."""
    calendar_content = """# Moon phases
NewMoon	New moon - time for reflection
FullMoon	Full moon party tonight!
"""

    # Test around January 2026 moon phases
    # New moon on Jan 18, Full moon on Jan 3
    today = datetime.date(2026, 1, 1)
    result = run_calendar(calendar_content, today, ahead=20)

    expected = [
        "Jan  3*\tFull moon party tonight!",
        "Jan 18*\tNew moon - time for reflection",
    ]
    assert result == expected


def test_nth_weekday_of_month(run_calendar):
    """Test Nth weekday of month expressions (e.g., May Sun+2 for Mother's Day)."""
    calendar_content = """\
May Sun+2\tMother's Day
Sep Mon+1\tLabor Day
Nov Thu+4\tThanksgiving
"""
    # Mother's Day 2026: May 10 (2nd Sunday)
    today = datetime.date(2026, 5, 10)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["May 10*\tMother's Day"]

    # Labor Day 2026: Sep 7 (1st Monday)
    today = datetime.date(2026, 9, 7)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Sep  7*\tLabor Day"]

    # Thanksgiving 2026: Nov 26 (4th Thursday)
    today = datetime.date(2026, 11, 26)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Nov 26*\tThanksgiving"]


def test_last_weekday_of_month(run_calendar):
    """Test last weekday of month (e.g., May Mon-1 for Memorial Day)."""
    calendar_content = """\
May Mon-1\tMemorial Day
"""
    # Memorial Day 2026: May 25 (last Monday)
    today = datetime.date(2026, 5, 25)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["May 25*\tMemorial Day"]


def test_fifth_weekday_no_match(run_calendar):
    """Test that 5th occurrence returns no match when it doesn't exist."""
    calendar_content = """\
Feb Mon+5\tFifth Monday of February
"""
    # Feb 2026 only has 4 Mondays, so no match
    today = datetime.date(2026, 2, 1)
    result = run_calendar(calendar_content, today, ahead=27)
    assert result == []


def test_wildcard_nth_weekday(run_calendar):
    """Test wildcard Nth weekday (e.g., * Fri+3 for 3rd Friday of every month)."""
    calendar_content = """\
* Fri+3\tThird Friday
"""
    # 3rd Friday of January 2026 is Jan 16
    today = datetime.date(2026, 1, 16)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jan 16*\tThird Friday"]


def test_easter_offset(run_calendar):
    """Test Easter offset expressions (e.g., Easter-2 for Good Friday)."""
    calendar_content = """\
Easter-2\tGood Friday
Easter-46\tAsh Wednesday
"""
    # Easter 2026 is April 5
    # Good Friday: April 3
    today = datetime.date(2026, 4, 3)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Apr  3*\tGood Friday"]

    # Ash Wednesday: Feb 18
    today = datetime.date(2026, 2, 18)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Feb 18*\tAsh Wednesday"]


def test_recurring_date_offset(run_calendar):
    """Test offset from recurring date (e.g., FullMoon+1)."""
    calendar_content = """\
FullMoon+1\tDay after full moon
"""
    # Full moon Jan 3, 2026 → FullMoon+1 = Jan 4
    today = datetime.date(2026, 1, 4)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jan  4*\tDay after full moon"]


def test_standalone_weekday(run_calendar):
    """Test standalone weekday matches (e.g., Friday matches every Friday)."""
    calendar_content = """\
Friday\tTGIF!
"""
    # Jan 2, 2026 is a Friday
    today = datetime.date(2026, 1, 2)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jan  2*\tTGIF!"]

    # Jan 1, 2026 is a Thursday — no match
    today = datetime.date(2026, 1, 1)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == []


def test_mixed_formats_sorting(run_calendar):
    """Test sorting with mixed fixed, weekday, and standalone expressions."""
    calendar_content = """\
01/02\tNew Year recovery
Friday\tTGIF!
Jan Mon+1\tFirst Monday
"""
    # Check Jan 1-5, 2026:
    #   Jan 1 = Thu, Jan 2 = Fri, Jan 3 = Sat, Jan 4 = Sun, Jan 5 = Mon
    today = datetime.date(2026, 1, 1)
    result = run_calendar(calendar_content, today, ahead=4)
    assert result == [
        "Jan  2\tNew Year recovery",
        "Jan  2*\tTGIF!",
        "Jan  5*\tFirst Monday",
    ]


def test_ordinal_weekday_numeric_month(run_calendar):
    """Test MM/WkdayOrdinal format (e.g., 10/MonSecond for Thanksgiving Canada)."""
    calendar_content = """\
10/MonSecond\tThanksgiving Day in Canada
12/SunFirst\tFirst Sunday of Advent
01/MonThird\tMartin Luther King Day
05/MonLast\tMemorial Day
"""
    # 2nd Monday of October 2026: Oct 12
    today = datetime.date(2026, 10, 12)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Oct 12*\tThanksgiving Day in Canada"]

    # 1st Sunday of December 2026: Dec 6
    today = datetime.date(2026, 12, 6)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Dec  6*\tFirst Sunday of Advent"]

    # 3rd Monday of January 2026: Jan 19
    today = datetime.date(2026, 1, 19)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jan 19*\tMartin Luther King Day"]

    # Last Monday of May 2026: May 25
    today = datetime.date(2026, 5, 25)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["May 25*\tMemorial Day"]


def test_ordinal_weekday_named_month_with_offset(run_calendar):
    """Test Month/WkdayOrdinal with day offset (e.g., Oct/SatFourth-2)."""
    calendar_content = """\
Oct/SatFourth-2\tHobart Show Day (TAS)
"""
    # 4th Saturday of October 2026: Oct 24, minus 2 = Oct 22
    today = datetime.date(2026, 10, 22)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Oct 22*\tHobart Show Day (TAS)"]


def test_trailing_asterisk_mm_dd(run_calendar):
    """Test that trailing * on MM/DD marks a fixed date as variable in output."""
    calendar_content = """\
07/04*\tIndependence Day
07/04\tAlso Independence Day
"""
    today = datetime.date(2024, 7, 4)
    result = run_calendar(calendar_content, today, ahead=0)
    assert "Jul  4*\tIndependence Day" in result
    assert "Jul  4\tAlso Independence Day" in result


def test_trailing_asterisk_month_dd(run_calendar):
    """Test that trailing * on Month DD marks a fixed date as variable in output."""
    calendar_content = """\
Jul 4*\tIndependence Day
"""
    today = datetime.date(2024, 7, 4)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jul  4*\tIndependence Day"]


def test_full_date_yyyy_slash(run_calendar):
    """Test YYYY/M/D format from judaic calendar files."""
    calendar_content = """\
2026/2/17\tRosh Chodesh Adar
2026/2/18\tRosh Chodesh Adar II
"""
    today = datetime.date(2026, 2, 17)
    result = run_calendar(calendar_content, today, ahead=1)
    assert result == [
        "Feb 17\tRosh Chodesh Adar",
        "Feb 18\tRosh Chodesh Adar II",
    ]


def test_full_date_yyyy_slash_with_asterisk(run_calendar):
    """Test YYYY/M/D* format marks date as variable in output."""
    calendar_content = """\
2026/2/17*\tRosh Chodesh Adar
"""
    today = datetime.date(2026, 2, 17)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Feb 17*\tRosh Chodesh Adar"]


def test_full_date_iso_format(run_calendar):
    """Test YYYY-MM-DD ISO date format."""
    calendar_content = """\
2026-02-17\tISO format event
"""
    today = datetime.date(2026, 2, 17)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Feb 17\tISO format event"]


def test_full_date_wrong_year_no_match(run_calendar):
    """Test that YYYY/M/D only matches in its specific year."""
    calendar_content = """\
2025/2/17\tLast year's event
"""
    today = datetime.date(2026, 2, 17)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == []


def test_full_date_mixed_with_mm_dd(run_calendar):
    """Test that YYYY/M/D and MM/DD dates coexist and sort correctly."""
    calendar_content = """\
2026/2/18\tJudaic event
02/17\tFixed MM/DD event
Feb 19\tMonth DD event
"""
    today = datetime.date(2026, 2, 17)
    result = run_calendar(calendar_content, today, ahead=2)
    assert result == [
        "Feb 17\tFixed MM/DD event",
        "Feb 18\tJudaic event",
        "Feb 19\tMonth DD event",
    ]


def test_dd_month_format(run_calendar):
    """Test DD Month format (e.g., 01 Jan, 21 Apr)."""
    calendar_content = """\
01 Jan\tNew Year's Day
"""
    today = datetime.date(2026, 1, 1)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jan  1\tNew Year's Day"]


def test_dd_month_mixed_with_month_dd(run_calendar):
    """Test DD Month and Month DD formats coexist and sort correctly."""
    calendar_content = """\
01 Jan\tDD Month format
Jan 02\tMonth DD format
"""
    today = datetime.date(2026, 1, 1)
    result = run_calendar(calendar_content, today, ahead=1)
    assert result == [
        "Jan  1\tDD Month format",
        "Jan  2\tMonth DD format",
    ]


def test_month_slash_dd_format(run_calendar):
    """Test Month/DD format (e.g., apr/01, dec/07)."""
    calendar_content = """\
apr/01\tApril Fools
dec/07\tPearl Harbor Day
jan/06\tEpiphany
"""
    today = datetime.date(2026, 4, 1)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Apr  1\tApril Fools"]


def test_month_slash_dd_with_ordinal(run_calendar):
    """Test Month/DD and Month/WkdayOrdinal formats don't conflict."""
    calendar_content = """\
apr/01\tApril Fools
Apr/SunFirst\tFirst Sunday of April
"""
    # First Sunday of April 2026 is Apr 5
    today = datetime.date(2026, 4, 1)
    result = run_calendar(calendar_content, today, ahead=5)
    assert result == [
        "Apr  1\tApril Fools",
        "Apr  5*\tFirst Sunday of April",
    ]


def test_mm_wkday_offset_format(run_calendar):
    """Test MM/Weekday+/-N format (e.g., 03/Sun-1, 11/Wed+3, 12/Sun+1)."""
    calendar_content = """\
03/Sun-1\tLast Sunday of March
11/Wed+3\tThird Wednesday of November
12/Sun+1\tFirst Sunday of December
"""
    # Last Sunday of March 2026: Mar 29
    today = datetime.date(2026, 3, 29)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Mar 29*\tLast Sunday of March"]

    # 3rd Wednesday of November 2026: Nov 18
    today = datetime.date(2026, 11, 18)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Nov 18*\tThird Wednesday of November"]

    # 1st Sunday of December 2026: Dec 6
    today = datetime.date(2026, 12, 6)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Dec  6*\tFirst Sunday of December"]


def test_wkday_ord_month_format(run_calendar):
    """Test WkdayOrd Month format (e.g., SunFirst Aug, SunThird Jul)."""
    calendar_content = """\
SunFirst Aug\tFirst Sunday of August
SunThird Jul\tThird Sunday of July
SunLast Jun\tLast Sunday of June
"""
    # First Sunday of August 2026: Aug 2
    today = datetime.date(2026, 8, 2)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Aug  2*\tFirst Sunday of August"]

    # Third Sunday of July 2026: Jul 19
    today = datetime.date(2026, 7, 19)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jul 19*\tThird Sunday of July"]

    # Last Sunday of June 2026: Jun 28
    today = datetime.date(2026, 6, 28)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jun 28*\tLast Sunday of June"]


def test_cli_smoke(tmp_path, monkeypatch):
    """Smoke test: invoke the CLI entry point and verify it produces expected output."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text("01/15\tTest event\n01/16\tAnother event\n")

    monkeypatch.setattr(
        sys, "argv", ["pylendar", "-f", str(calendar_file), "-t", "20260115"]
    )
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    main()

    output = stdout.getvalue()
    assert "Jan 15\tTest event" in output
    assert "Jan 16\tAnother event" in output
