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
    Event,
    FixedDate,
    get_matching_events,
    get_moon_phases,
    main,
    replace_age_in_description,
)


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


def test_four_digit_special_date_offset_is_ignored(run_calendar):
    """Absurd special-date offsets are rejected instead of crashing at runtime."""
    content = "Easter+1000\tWay too far\n"
    today = datetime.date(2026, 4, 5)
    result = run_calendar(content, today, ahead=0)
    assert result == []


def test_paskha(run_calendar):
    """Test Paskha (Orthodox Easter) and offset expressions."""
    calendar_content = """\
Paskha\tOrthodox Easter
Paskha-2\tOrthodox Good Friday
"""
    # Paskha 2026 is April 12
    today = datetime.date(2026, 4, 12)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Apr 12*\tOrthodox Easter"]

    # Orthodox Good Friday: April 10
    today = datetime.date(2026, 4, 10)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Apr 10*\tOrthodox Good Friday"]


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


@pytest.mark.parametrize(
    ("content", "today", "expected"),
    [
        (
            "07/04*\tIndependence Day\n07/04\tAlso Independence Day\n",
            datetime.date(2024, 7, 4),
            ["Jul  4*\tIndependence Day", "Jul  4\tAlso Independence Day"],
        ),
        (
            "Jul 4*\tIndependence Day\n",
            datetime.date(2024, 7, 4),
            ["Jul  4*\tIndependence Day"],
        ),
    ],
    ids=["mm-dd-star", "month-dd-star"],
)
def test_trailing_asterisk(run_calendar, content, today, expected):
    """Test trailing * marks a fixed date as variable in output."""
    result = run_calendar(content, today, ahead=0)
    assert result == expected


@pytest.mark.parametrize(
    ("content", "today", "ahead", "expected"),
    [
        (
            "2026/2/17\tRosh Chodesh Adar\n2026/2/18\tRosh Chodesh Adar II\n",
            datetime.date(2026, 2, 17),
            1,
            ["Feb 17\tRosh Chodesh Adar", "Feb 18\tRosh Chodesh Adar II"],
        ),
        (
            "2026/2/17*\tRosh Chodesh Adar\n",
            datetime.date(2026, 2, 17),
            0,
            ["Feb 17*\tRosh Chodesh Adar"],
        ),
        (
            "2026-02-17\tISO format event\n",
            datetime.date(2026, 2, 17),
            0,
            ["Feb 17\tISO format event"],
        ),
    ],
    ids=["yyyy-slash", "yyyy-slash-star", "iso-format"],
)
def test_full_date_formats(run_calendar, content, today, ahead, expected):
    """Test YYYY/M/D, YYYY/M/D*, and YYYY-MM-DD formats."""
    result = run_calendar(content, today, ahead=ahead)
    assert result == expected


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


def test_dd_month_formats(run_calendar):
    """Test DD Month format and coexistence with Month DD format."""
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


def test_month_slash_dd_formats(run_calendar):
    """Test Month/DD format and coexistence with Month/WkdayOrdinal."""
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


def test_chinese_new_year(run_calendar):
    """Test ChineseNewYear and offset expressions."""
    calendar_content = """\
ChineseNewYear\tChinese New Year
ChineseNewYear-1\tChinese New Year's Eve
"""
    # Chinese New Year 2026 is February 17
    today = datetime.date(2026, 2, 17)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Feb 17*\tChinese New Year"]

    # Chinese New Year's Eve: February 16
    today = datetime.date(2026, 2, 16)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Feb 16*\tChinese New Year's Eve"]


def test_bare_month_name(run_calendar):
    """Test bare month name matches the 1st of that month."""
    calendar_content = """\
June\tEvery June 1st
Jun\tAlso June 1st (abbreviation)
"""
    # June 1st should match both entries
    today = datetime.date(2026, 6, 1)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == [
        "Jun  1\tEvery June 1st",
        "Jun  1\tAlso June 1st (abbreviation)",
    ]

    # June 2nd — no match
    today = datetime.date(2026, 6, 2)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == []


@pytest.mark.parametrize(
    ("content", "today", "ahead", "expected"),
    [
        (
            "**\tDaily standup\n",
            datetime.date(2026, 3, 10),
            2,
            [
                "Mar 10\tDaily standup",
                "Mar 11\tDaily standup",
                "Mar 12\tDaily standup",
            ],
        ),
        (
            "* *\tDaily reminder\n",
            datetime.date(2026, 6, 15),
            1,
            [
                "Jun 15\tDaily reminder",
                "Jun 16\tDaily reminder",
            ],
        ),
    ],
    ids=["double-star", "spaced-star"],
)
def test_every_day_wildcards(run_calendar, content, today, ahead, expected):
    """Test ** and * * both match every day."""
    result = run_calendar(content, today, ahead=ahead)
    assert result == expected


@pytest.mark.parametrize(
    ("content", "today", "ahead", "expected"),
    [
        (
            "June*\tSummer fun\n",
            datetime.date(2026, 6, 14),
            1,
            ["Jun 14\tSummer fun", "Jun 15\tSummer fun"],
        ),
        (
            "Jun*\tJune event\n",
            datetime.date(2026, 6, 30),
            0,
            ["Jun 30\tJune event"],
        ),
        (
            "June *\tJune spaced\n",
            datetime.date(2026, 6, 1),
            0,
            ["Jun  1\tJune spaced"],
        ),
    ],
    ids=["compact", "abbreviated", "spaced"],
)
def test_month_wildcards(run_calendar, content, today, ahead, expected):
    """Test Month* and Month * match days in the given month."""
    result = run_calendar(content, today, ahead=ahead)
    assert result == expected


def test_month_wildcard_vs_bare_month(run_calendar):
    """Test June* vs bare June: June 1st gets both; other days get only June*."""
    calendar_content = """\
June\tFirst of June
June*\tEvery day in June
"""
    # June 1st matches both
    today = datetime.date(2026, 6, 1)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == [
        "Jun  1\tFirst of June",
        "Jun  1\tEvery day in June",
    ]

    # June 15th matches only June*
    today = datetime.date(2026, 6, 15)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jun 15\tEvery day in June"]


@pytest.mark.parametrize(
    ("content", "today", "expected"),
    [
        (
            "*15\tPay rent\n",
            datetime.date(2026, 3, 15),
            ["Mar 15\tPay rent"],
        ),
        (
            "15 *\tPay rent\n",
            datetime.date(2026, 5, 15),
            ["May 15\tPay rent"],
        ),
        (
            "*15\tNo space\n* 15\tWith space\n",
            datetime.date(2026, 4, 15),
            ["Apr 15\tNo space", "Apr 15\tWith space"],
        ),
    ],
    ids=["no-space", "reversed", "space-equivalence"],
)
def test_wildcard_day_formats(run_calendar, content, today, expected):
    """Test *DD, DD *, and * DD all match the given day of every month."""
    result = run_calendar(content, today, ahead=0)
    assert result == expected


def test_feb_wildcard_leap_year(run_calendar):
    """Test Feb* in leap year matches Feb 29."""
    calendar_content = """\
Feb*\tFebruary event
"""
    # 2024 is a leap year
    today = datetime.date(2024, 2, 29)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Feb 29\tFebruary event"]


def test_mixed_wildcards_sort(run_calendar):
    """Test mixed wildcards (**, June*, *15, fixed dates) sort correctly."""
    calendar_content = """\
**\tDaily standup
June*\tSummer fun
*15\tPay rent
06/14\tFlag Day
"""
    today = datetime.date(2026, 6, 14)
    result = run_calendar(calendar_content, today, ahead=1)
    assert result == [
        "Jun 14\tDaily standup",
        "Jun 14\tSummer fun",
        "Jun 14\tFlag Day",
        "Jun 15\tDaily standup",
        "Jun 15\tSummer fun",
        "Jun 15\tPay rent",
    ]


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


# ---------------------------------------------------------------------------
# Unit-level edge cases for the matching/sorting/output pipeline
# ---------------------------------------------------------------------------


def test_replace_age_replaces_year_with_age() -> None:
    """[1985] is replaced with 41 when checked against 2026-03-01."""
    result = replace_age_in_description("Born [1985]", datetime.date(2026, 3, 1))
    assert result == "Born 41"


def test_replace_age_no_placeholder_unchanged() -> None:
    """Description without [YYYY] is returned unchanged."""
    result = replace_age_in_description("No year here", datetime.date(2026, 3, 1))
    assert result == "No year here"


def test_replace_age_multiple_different_tags() -> None:
    """Age replacement skipped if there are multiple tags with different years."""
    desc = "Alice [1990] and Bob [1992]"
    result = replace_age_in_description(desc, datetime.date(2026, 3, 1))
    assert result == desc


def test_replace_age_multiple_identical_tags() -> None:
    """Age replacement skipped if there are multiple tags with the same year."""
    desc = "Alice [1990] (born [1990])"
    result = replace_age_in_description(desc, datetime.date(2026, 3, 1))
    assert result == desc


def test_event_lt_non_event_returns_not_implemented() -> None:
    """Comparing Event with a non-Event returns NotImplemented."""
    event = Event(datetime.date(2026, 1, 1), "x")
    assert event.__lt__("not an event") is NotImplemented  # pylint: disable=unnecessary-dunder-call


def test_fixed_date_feb_30_returns_empty() -> None:
    """Feb 30 doesn't exist, so resolve returns an empty set."""
    assert FixedDate(month=2, day=30).resolve(2026) == set()


def test_get_matching_events_unparseable_date_returns_empty() -> None:
    """A line with an unparseable date yields no events."""
    parser = DateStringParser()
    dates = {datetime.date(2026, 3, 1)}
    result = get_matching_events("nonsense\tSome event", dates, parser)
    assert result == []


def test_year_boundary_relative_weekday(run_calendar):
    """Expression anchored in Dec but resolving to Jan is found across year boundary.

    Sat>Dec 25+7: Dec 25 + 7 = Jan 1, 2027 (Friday), Saturday after = Jan 2.
    Checking from Jan 1, 2027 with ahead=3 should find Jan 2.
    """
    result = run_calendar(
        "Sat>Dec 25+7\tRelative event across year boundary",
        datetime.date(2027, 1, 1),
        ahead=3,
    )
    assert result == ["Jan  2*\tRelative event across year boundary"]


def test_year_boundary_new_moon(run_calendar):
    """Built-in NewMoon in next-year January is found when today is Dec 31.

    Regresses a bug where parse_special_dates only materialized built-in
    special dates for today.year, so a Dec/Jan window missed any
    moon-phase / equinox / Easter / etc. that fell in the adjacent year.
    """
    next_year = 2033
    earliest_jan_new_moon = min(get_moon_phases(next_year)["newmoon"])
    today = datetime.date(next_year - 1, 12, 31)
    ahead = (earliest_jan_new_moon - today).days + 1
    result = run_calendar("NewMoon\tNM event", today, ahead=ahead)
    assert any("NM event" in line for line in result)
