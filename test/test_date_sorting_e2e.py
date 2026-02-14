# pylint: disable=duplicate-code
"""End-to-end tests for date sorting functionality.

These tests verify that events are properly sorted by date when displayed,
without creating test files in the current directory.
"""

import datetime

import pytest

from pylendar.pylendar import (
    DateStringParser,
    SimpleCPP,
    get_ahead_behind,
    get_dates_to_check,
    get_matching_event,
    join_continuation_lines,
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

        special_dates, recurring_events = parse_special_dates(
            calendar_lines, today.year
        )
        date_parser = DateStringParser(special_dates)
        matching_events = [
            event
            for line in calendar_lines
            if (
                event := get_matching_event(
                    line, dates_to_check, date_parser, recurring_events
                )
            )
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


def test_default_date_range_sorting(run_calendar):
    """Test sorting with default date range (uses get_ahead_behind logic)."""
    calendar_content = """# Calendar with today and tomorrow events
08/29\tToday's event
08/30\tTomorrow's event
08/31\tDay after tomorrow (should not show)
08/28\tYesterday (should not show)
"""

    # Test with default parameters - should use get_ahead_behind() logic
    # Thursday (Aug 29, 2024) should default to ahead=1, behind=0
    today = datetime.date(2024, 8, 29)  # Thursday
    result = run_calendar(calendar_content, today)  # Uses defaults

    # Should only show today (Aug 29) and tomorrow (Aug 30)
    expected = [
        "Aug 29\tToday's event",
        "Aug 30\tTomorrow's event",
    ]

    assert result == expected


def test_weekend_date_range_sorting(run_calendar):
    """Test sorting with weekend behavior (Friday default of 3 days ahead)."""
    calendar_content = """# Weekend calendar events
07/12\tFriday event
07/13\tSaturday event
07/14\tSunday event
07/15\tMonday event
07/16\tTuesday event (should not show with Friday default)
"""

    # Test on Friday - should use get_ahead_behind() default of 3 days ahead
    today = datetime.date(2024, 7, 12)  # Friday
    result = run_calendar(calendar_content, today)  # Uses Friday default

    # Should show Fri-Mon events in chronological order (Friday default: ahead=3)
    expected = [
        "Jul 12\tFriday event",
        "Jul 13\tSaturday event",
        "Jul 14\tSunday event",
        "Jul 15\tMonday event",
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

    expected = ["Mar 20\tSpring begins"]
    assert result == expected

    # Test around winter solstice 2026 (December 21)
    today = datetime.date(2026, 12, 20)
    result = run_calendar(calendar_content, today, ahead=2)

    expected = ["Dec 21\tWinter begins - shortest day of the year"]
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
        "Jan  3\tFull moon party tonight!",
        "Jan 18\tNew moon - time for reflection",
    ]
    assert result == expected
