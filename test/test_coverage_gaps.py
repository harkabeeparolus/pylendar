"""Tests targeting specific uncovered lines and branches."""

import datetime
from pathlib import Path

import pytest

from pylendar.pylendar import (
    DateStringParser,
    Event,
    FixedDate,
    SimpleCPP,
    find_calendar,
    get_matching_events,
    parse_special_dates,
    replace_age_in_description,
)


class TestReplaceAgeInDescription:
    """Tests for [YYYY] age replacement in event descriptions."""

    def test_replaces_year_with_age(self) -> None:
        """[1985] is replaced with 41 when checked against 2026-03-01."""
        result = replace_age_in_description("Born [1985]", datetime.date(2026, 3, 1))
        assert result == "Born 41"

    def test_no_placeholder_unchanged(self) -> None:
        """Description without [YYYY] is returned unchanged."""
        result = replace_age_in_description("No year here", datetime.date(2026, 3, 1))
        assert result == "No year here"


class TestParseSpecialDatesAliases:
    """Tests for alias directives (left=right) in parse_special_dates."""

    def test_right_side_known_alias(self) -> None:
        """myfeast=Easter — right side known, left gets the value."""
        date_exprs = parse_special_dates(["myfeast=Easter"], 2026)
        assert "myfeast" in date_exprs
        easter_dates = date_exprs["easter"].resolve(2026)
        assert date_exprs["myfeast"].resolve(2026) == easter_dates

    def test_left_side_known_alias(self) -> None:
        """Easter=spring — left side known, right gets the value."""
        date_exprs = parse_special_dates(["Easter=spring"], 2026)
        assert "spring" in date_exprs
        easter_dates = date_exprs["easter"].resolve(2026)
        assert date_exprs["spring"].resolve(2026) == easter_dates


class TestEventLt:
    """Tests for Event comparison edge cases."""

    def test_non_event_returns_not_implemented(self) -> None:
        """Comparing Event with a non-Event returns NotImplemented."""
        event = Event(datetime.date(2026, 1, 1), "x")
        assert event.__lt__("not an event") is NotImplemented  # pylint: disable=unnecessary-dunder-call


class TestParseUnknownSpecialDateOffset:
    """Tests for unknown base in special-date-with-offset pattern."""

    def test_bogus_date_with_offset_returns_none(self) -> None:
        """bogusdate+3 is not in date_exprs, so parse returns None."""
        parser = DateStringParser()
        assert parser.parse("bogusdate+3") is None


class TestSimpleCPPIncludeEdgeCases:
    """Tests for SimpleCPP include resolution edge cases."""

    def test_include_not_found_skips(self, tmp_path: Path) -> None:
        """Missing include file is silently skipped (with a log warning)."""
        cal = tmp_path / "calendar"
        cal.write_text('#include "nonexistent.file"\n01/01\tNew Year\n')
        cpp = SimpleCPP(include_dirs=[tmp_path])
        result = cpp.process_file(cal)
        assert result == ["01/01\tNew Year"]

    def test_malformed_include_raises(self, tmp_path: Path) -> None:
        """Bare #include with no filename raises SyntaxError."""
        cal = tmp_path / "calendar"
        cal.write_text("#include\n")
        cpp = SimpleCPP(include_dirs=[tmp_path])
        with pytest.raises(SyntaxError, match="Malformed include"):
            cpp.process_file(cal)


class TestFixedDateImpossible:
    """Tests for FixedDate with impossible month/day combinations."""

    def test_feb_30_returns_empty(self) -> None:
        """Feb 30 doesn't exist, so resolve returns an empty set."""
        assert FixedDate(month=2, day=30).resolve(2026) == set()


class TestFindCalendarFallback:
    """Tests for find_calendar when no calendar file is found anywhere."""

    def test_returns_default_when_nothing_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to Path('calendar') when no file exists."""
        monkeypatch.delenv("CALENDAR_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "fakehome"))
        result = find_calendar([])
        assert result == Path("calendar")


class TestGetMatchingEventsUnparseable:
    """Tests for get_matching_events with an unparseable date string."""

    def test_unparseable_date_returns_empty(self) -> None:
        """A line with an unparseable date yields no events."""
        parser = DateStringParser()
        dates = {datetime.date(2026, 3, 1)}
        result = get_matching_events("nonsense\tSome event", dates, parser)
        assert result == []
