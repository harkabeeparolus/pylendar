"""End-to-end tests for date sorting functionality.

These tests verify that events are properly sorted by date when displayed,
without creating test files in the current directory.
"""

import datetime

from pylendar.pylendar import (
    DateStringParser,
    SimpleCPP,
    get_ahead_behind,
    get_dates_to_check,
    get_matching_event,
    parse_special_dates,
)


def _test_calendar_sorting(tmp_path, calendar_content, today, ahead=None, behind=None):
    """Provide helper functionality for testing calendar event sorting.

    Args:
        tmp_path: pytest temporary path fixture
        calendar_content: string content for the calendar file
        today: datetime.date for the test date
        ahead: number of days ahead to check (None for default behavior)
        behind: number of days behind to check (None for default behavior)

    Returns:
        list[str]: sorted events output, one event per list item
    """
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text(calendar_content)

    # Process the calendar file
    processor = SimpleCPP(include_dirs=[])
    calendar_lines = processor.process_file(calendar_file)

    # Get ahead/behind values using the same logic as the main application
    # Use 0 as default for behind if not specified, None for ahead to get default behavior
    behind_value = behind if behind is not None else 0
    ahead_days, behind_days = get_ahead_behind(today, ahead=ahead, behind=behind_value)

    # Get dates to check
    dates_to_check = get_dates_to_check(today, ahead=ahead_days, behind=behind_days)

    # Parse special dates and create parser
    special_dates = parse_special_dates(calendar_lines, today.year)
    date_parser = DateStringParser(special_dates)

    # Collect matching events
    matching_events = [
        event
        for line in calendar_lines
        if (event := get_matching_event(line, dates_to_check, date_parser))
    ]

    # Sort events and return result list
    return [str(event) for event in sorted(matching_events)]


def test_events_sorted_by_date(tmp_path):
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
    result = _test_calendar_sorting(
        tmp_path, calendar_content, today, ahead=3, behind=2
    )

    # Expected result should be events in chronological order
    expected = [
        "Jul  3\tWednesday event - July 3rd",
        "Jul  4\tIndependence Day - July 4th",
        "Jul  5\tFriday party - July 5th",
        "Jul  6\tEvent on Saturday July 6th",
    ]

    assert result == expected


def test_events_with_wildcards_sorted_correctly(tmp_path):
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
    result = _test_calendar_sorting(
        tmp_path, calendar_content, today, ahead=7, behind=7
    )

    # Should be sorted chronologically regardless of wildcard vs specific date
    expected = [
        "Jul 10\tAnother specific date",
        "Jul 15\tMid-month task",
        "Jul 18\tSpecific date event",
        "Jul 20\tPay credit card",
        "Jul 22\tLate July event",
    ]

    assert result == expected


def test_default_date_range_sorting(tmp_path):
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
    result = _test_calendar_sorting(tmp_path, calendar_content, today)  # Uses defaults

    # Should only show today (Aug 29) and tomorrow (Aug 30)
    expected = [
        "Aug 29\tToday's event",
        "Aug 30\tTomorrow's event",
    ]

    assert result == expected


def test_weekend_date_range_sorting(tmp_path):
    """Test sorting with weekend behavior (Friday uses get_ahead_behind default of 3)."""
    calendar_content = """# Weekend calendar events
07/12\tFriday event
07/13\tSaturday event
07/14\tSunday event
07/15\tMonday event
07/16\tTuesday event (should not show with Friday default)
"""

    # Test on Friday - should use get_ahead_behind() default of 3 days ahead
    today = datetime.date(2024, 7, 12)  # Friday
    result = _test_calendar_sorting(
        tmp_path, calendar_content, today
    )  # Uses Friday default

    # Should show Fri-Mon events in chronological order (Friday default: ahead=3)
    expected = [
        "Jul 12\tFriday event",
        "Jul 13\tSaturday event",
        "Jul 14\tSunday event",
        "Jul 15\tMonday event",
    ]

    assert result == expected


def test_friday_vs_weekday_default_behavior(tmp_path):
    """Test that Friday and weekday use different default ahead values via get_ahead_behind."""
    calendar_content = """# Events to test default behavior differences
07/10\tWednesday event
07/11\tThursday event  
07/12\tFriday event
07/13\tSaturday event
07/14\tSunday event
"""

    # Test on Wednesday (weekday) - should default to ahead=1, behind=0
    wednesday = datetime.date(2024, 7, 10)
    result_wed = _test_calendar_sorting(tmp_path, calendar_content, wednesday)
    expected_wed = [
        "Jul 10\tWednesday event",
        "Jul 11\tThursday event",
    ]
    assert result_wed == expected_wed

    # Test on Friday - should default to ahead=3, behind=0
    friday = datetime.date(2024, 7, 12)
    result_fri = _test_calendar_sorting(tmp_path, calendar_content, friday)
    expected_fri = [
        "Jul 12\tFriday event",
        "Jul 13\tSaturday event",
        "Jul 14\tSunday event",
    ]
    assert result_fri == expected_fri
