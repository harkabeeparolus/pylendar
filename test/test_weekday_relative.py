"""Tests for Wkday<Date / Wkday>Date weekday-relative-to-date syntax."""

import datetime

import pytest

from pylendar.pylendar import (
    DateStringParser,
    WeekdayRelativeToDate,
    parse_special_dates,
)


@pytest.fixture
def parser() -> DateStringParser:
    """Return a default DateStringParser."""
    special = parse_special_dates([], [2026])
    return DateStringParser(special)


# --- WeekdayRelativeToDate.resolve() ---


def test_resolve_sat_after_jun_19_2026() -> None:
    """2026-06-19 is a Friday, so Sat>Jun 19 should be Jun 20."""
    expr = WeekdayRelativeToDate(month=6, day=19, weekday=5, direction=1)
    assert expr.resolve(2026) == {datetime.date(2026, 6, 20)}


def test_resolve_sat_after_jun_19_2027() -> None:
    """2027-06-19 is a Saturday, so Sat>Jun 19 skips it and returns Jun 26."""
    expr = WeekdayRelativeToDate(month=6, day=19, weekday=5, direction=1)
    assert expr.resolve(2027) == {datetime.date(2027, 6, 26)}


def test_resolve_sun_before_dec_25_2026() -> None:
    """2026-12-25 is a Friday, so Sun<Dec 25 should be Dec 20."""
    expr = WeekdayRelativeToDate(month=12, day=25, weekday=6, direction=-1)
    assert expr.resolve(2026) == {datetime.date(2026, 12, 20)}


def test_resolve_sun_before_dec_25_2025() -> None:
    """2025-12-25 is a Thursday, so Sun<Dec 25 should be Dec 21."""
    expr = WeekdayRelativeToDate(month=12, day=25, weekday=6, direction=-1)
    assert expr.resolve(2025) == {datetime.date(2025, 12, 21)}


def test_resolve_strict_skips_anchor_weekday() -> None:
    """When anchor IS the target weekday, it must be skipped (strict)."""
    # 2028-06-19 is a Monday; let's find Mon>Jun 19 — should be Jun 26
    expr = WeekdayRelativeToDate(month=6, day=19, weekday=0, direction=1)
    assert expr.resolve(2028) == {datetime.date(2028, 6, 26)}


def test_resolve_with_anchor_offset() -> None:
    """Sun<Dec 25-7 should find Sunday before Dec 18 (Third Advent)."""
    expr = WeekdayRelativeToDate(
        month=12, day=25, weekday=6, direction=-1, anchor_offset=-7
    )
    # 2026: Dec 18 is Friday, Sunday before is Dec 13
    assert expr.resolve(2026) == {datetime.date(2026, 12, 13)}


def test_resolve_invalid_anchor_date() -> None:
    """Invalid date (e.g., Feb 30) should return empty set."""
    expr = WeekdayRelativeToDate(month=2, day=30, weekday=0, direction=1)
    assert expr.resolve(2026) == set()


def test_reject_invalid_direction() -> None:
    """Direction must be strict: before (-1) or after (+1)."""
    with pytest.raises(ValueError, match="direction must be -1 or 1"):
        WeekdayRelativeToDate(month=6, day=19, weekday=5, direction=0)


def test_reject_invalid_weekday() -> None:
    """Weekday must use Python weekday numbering (0..6)."""
    with pytest.raises(ValueError, match=r"weekday must be in range 0\.\.6"):
        WeekdayRelativeToDate(month=6, day=19, weekday=7, direction=1)


def test_resolve_is_variable() -> None:
    """WeekdayRelativeToDate should be marked as variable (changes yearly)."""
    expr = WeekdayRelativeToDate(month=6, day=19, weekday=5, direction=1)
    assert expr.variable is True


# --- Advent Sundays via offset chaining ---


def test_advent_sundays_2026() -> None:
    """All four Advent Sundays for 2026 via Sun<Dec 25 with offsets."""
    base_args = {"month": 12, "day": 25, "weekday": 6, "direction": -1}
    fourth = WeekdayRelativeToDate(**base_args).resolve(2026)
    third = WeekdayRelativeToDate(**base_args, anchor_offset=-7).resolve(2026)
    second = WeekdayRelativeToDate(**base_args, anchor_offset=-14).resolve(2026)
    first = WeekdayRelativeToDate(**base_args, anchor_offset=-21).resolve(2026)
    assert fourth == {datetime.date(2026, 12, 20)}
    assert third == {datetime.date(2026, 12, 13)}
    assert second == {datetime.date(2026, 12, 6)}
    assert first == {datetime.date(2026, 11, 29)}


# --- Parser: _parse_weekday_relative() via parse() ---


def test_parse_sat_after_month_dd(parser: DateStringParser) -> None:
    """Parse 'Sat>Jun 19' and resolve for 2026."""
    expr = parser.parse("Sat>Jun 19")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 6, 20)}


def test_parse_sun_before_month_dd(parser: DateStringParser) -> None:
    """Parse 'Sun<Dec 25' and resolve for 2026."""
    expr = parser.parse("Sun<Dec 25")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 12, 20)}


def test_parse_with_negative_offset(parser: DateStringParser) -> None:
    """Parse 'Sun<Dec 25-7' (Third Advent)."""
    expr = parser.parse("Sun<Dec 25-7")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 12, 13)}


def test_parse_with_positive_offset(parser: DateStringParser) -> None:
    """Parse 'Sun<Dec 25+7' shifts anchor forward to Jan 1."""
    expr = parser.parse("Sun<Dec 25+7")
    assert expr is not None
    # Anchor becomes Jan 1, 2027; Sunday before that is Dec 27, 2026
    result = expr.resolve(2026)
    assert result == {datetime.date(2026, 12, 27)}


def test_parse_with_four_digit_anchor_offset_returns_none(
    parser: DateStringParser,
) -> None:
    """Anchor offsets with more than 3 digits are rejected."""
    assert parser.parse("Sun<Dec 25+1000") is None


def test_parse_mm_dd_anchor(parser: DateStringParser) -> None:
    """Parse 'Sat>06/19' with MM/DD anchor format."""
    expr = parser.parse("Sat>06/19")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 6, 20)}


def test_parse_mm_dd_anchor_with_offset(parser: DateStringParser) -> None:
    """Parse 'Sat>10/30' (All Saints' Eve)."""
    expr = parser.parse("Sat>10/30")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 10, 31)}


def test_parse_dd_month_anchor(parser: DateStringParser) -> None:
    """Parse 'Sat>19 Jun' with DD Month anchor format."""
    expr = parser.parse("Sat>19 Jun")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 6, 20)}


def test_parse_dd_month_anchor_with_offset(parser: DateStringParser) -> None:
    """Parse 'Sun<25 Dec-7' (Third Advent) with DD Month anchor."""
    expr = parser.parse("Sun<25 Dec-7")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 12, 13)}


def test_parse_case_insensitive(parser: DateStringParser) -> None:
    """Parse lowercase 'sat>jun 19'."""
    expr = parser.parse("sat>jun 19")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 6, 20)}


def test_parse_unknown_weekday_returns_none(parser: DateStringParser) -> None:
    """Unknown weekday name returns None."""
    assert parser.parse("Xyz>Jun 19") is None


def test_parse_unknown_month_returns_none(parser: DateStringParser) -> None:
    """Unknown month name returns None."""
    assert parser.parse("Sat>Foo 19") is None


def test_parse_spaces_around_operator(parser: DateStringParser) -> None:
    """Spaces around < or > are allowed."""
    expr = parser.parse("Sat > Jun 19")
    assert expr is not None
    assert expr.resolve(2026) == {datetime.date(2026, 6, 20)}
