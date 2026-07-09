"""End-to-end tests for pylendar.

These tests verify the full pipeline: preprocessing, parsing, matching, sorting,
and CLI invocation. Per-format output tests live in test_date_formats_e2e.py.
"""

import datetime

from pylendar.pylendar import (
    DateStringParser,
    Event,
    FixedDate,
    OffsetDate,
    get_matching_events,
    get_moon_phases,
    get_seasons,
    main,
    parse_special_dates,
    replace_age_in_description,
)

# --- event sorting ---


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


# --- date window and input handling ---


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


# --- CLI smoke tests ---


def test_cli_smoke(tmp_path, capsys):
    """Smoke test: invoke the CLI entry point and verify it produces expected output."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text("01/15\tTest event\n01/16\tAnother event\n")

    main(["-f", str(calendar_file), "-t", "20260115"])

    output = capsys.readouterr().out
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


def test_offset_date_inherits_variable_true_regardless_of_base() -> None:
    """OffsetDate.variable reads True even when constructed with a fixed base.

    OffsetDate has no ``variable`` of its own; it inherits the True default
    from DateExpr. This is correct only because the parser never wraps a
    fixed base — see ``test_offset_date_only_wraps_variable_bases``.
    """
    assert OffsetDate(FixedDate(12, 25), 1).variable is True


def test_offset_date_only_wraps_variable_bases() -> None:
    """Pin the invariant that the parser wraps only variable bases in OffsetDate.

    OffsetDate inherits ``variable=True`` from DateExpr, so the inherited
    default is correct only as long as every parser path that builds an
    OffsetDate feeds it a variable base. If a future grammar extension
    introduces fixed-base offset syntax (e.g. ``12/25+1``), the result
    must NOT be an OffsetDate — it would mismark the resulting date as
    variable. That extension would need a separate fixed-aware wrapper.
    """
    parser = DateStringParser(parse_special_dates([]))

    # Positive: representative inputs from each parser path that currently
    # produces an OffsetDate. Each must wrap a variable base.
    for date_str in ("easter+2", "10/MonSecond+1", "Oct/SatFourth-2"):
        result = parser.parse(date_str)
        assert isinstance(result, OffsetDate), (
            f"{date_str!r} stopped parsing as OffsetDate"
        )
        assert result.base.variable is True, (
            f"{date_str!r} now wraps a fixed base; OffsetDate.variable would "
            f"mismark it as variable"
        )

    # Negative: fixed-base offset syntax must not produce an OffsetDate.
    # Currently returns None (no grammar matches). If a future extension
    # makes these parse, the result must still report variable=False.
    for date_str in ("12/25+1", "Jul 4+1"):
        result = parser.parse(date_str)
        assert not isinstance(result, OffsetDate), (
            f"{date_str!r} parsed as OffsetDate, which would mismark this "
            f"fixed expression as variable"
        )
        if result is not None:
            assert result.variable is False, (
                f"{date_str!r} parsed but reported variable=True"
            )


def test_get_matching_events_unparseable_date_returns_empty() -> None:
    """A line with an unparseable date yields no events."""
    parser = DateStringParser()
    dates = {datetime.date(2026, 3, 1)}
    result = get_matching_events("nonsense\tSome event", dates, parser)
    assert result == []


# --- year-boundary matching ---


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


def test_year_boundary_special_offset(run_calendar):
    """Special+N whose base date is in the previous year is found in January.

    DecSolstice+15 lands around Jan 5. Checking on that very day must find
    the event, even though the December solstice it offsets from belongs to
    the previous year, which lies outside the display window.
    """
    solstice = get_seasons(2026)["decsolstice"]
    target = solstice + datetime.timedelta(days=15)
    assert target.year == 2027  # sanity: the offset crosses the year boundary
    result = run_calendar("DecSolstice+15\tYule ends", target, ahead=1)
    assert any("Yule ends" in line for line in result)
