"""End-to-end tests for the supported date formats.

Each test runs a small calendar through the full pipeline and checks the
formatted output for one date format: fixed dates, wildcards, weekday
ordinals, and astronomical special dates.
"""

import datetime

import pytest

# --- fixed dates ---


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


# --- weekday and ordinal formats ---


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


# --- wildcards ---


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


# --- astronomical and other special dates ---


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


def test_recurring_date_offset(run_calendar):
    """Test offset from recurring date (e.g., FullMoon+1)."""
    calendar_content = """\
FullMoon+1\tDay after full moon
"""
    # Full moon Jan 3, 2026 → FullMoon+1 = Jan 4
    today = datetime.date(2026, 1, 4)
    result = run_calendar(calendar_content, today, ahead=0)
    assert result == ["Jan  4*\tDay after full moon"]
