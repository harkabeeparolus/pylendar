"""Tests for the -w (weekday) flag."""

import datetime
import io
import sys

from pylendar.pylendar import Event, format_event, main


def test_weekday_flag_prepends_day_name(run_calendar):
    """Test that -w prepends abbreviated weekday names to output."""
    calendar_content = """\
07/04\tIndependence Day
07/05\tDay after
"""
    # July 4, 2026 is a Saturday
    today = datetime.date(2026, 7, 4)
    result = run_calendar(calendar_content, today, ahead=1, weekday=True)

    assert result == [
        "Sat Jul  4\tIndependence Day",
        "Sun Jul  5\tDay after",
    ]


def test_without_weekday_flag_unchanged(run_calendar):
    """Test that output without -w is unchanged."""
    calendar_content = """\
07/04\tIndependence Day
"""
    today = datetime.date(2026, 7, 4)
    result_without = run_calendar(calendar_content, today, ahead=0, weekday=False)
    result_default = run_calendar(calendar_content, today, ahead=0)

    assert result_without == ["Jul  4\tIndependence Day"]
    assert result_default == result_without


def test_weekday_flag_with_variable_dates(run_calendar):
    """Test that -w works correctly with variable (*) dates."""
    calendar_content = """\
* 15\tMid-month task
"""
    # Jul 15, 2026 is a Wednesday
    today = datetime.date(2026, 7, 15)
    result = run_calendar(calendar_content, today, ahead=0, weekday=True)

    assert result == ["Wed Jul 15\tMid-month task"]


def test_weekday_flag_with_nth_weekday(run_calendar):
    """Test that -w works with Nth weekday expressions."""
    calendar_content = """\
Nov Thu+4\tThanksgiving
"""
    # Thanksgiving 2026: Nov 26 (Thursday)
    today = datetime.date(2026, 11, 26)
    result = run_calendar(calendar_content, today, ahead=0, weekday=True)

    assert result == ["Thu Nov 26*\tThanksgiving"]


def test_format_event_unit():
    """Unit test for format_event function."""
    event = Event(datetime.date(2026, 2, 16), "President's Day", variable=False)

    assert format_event(event) == "Feb 16\tPresident's Day"
    assert format_event(event, weekday=True) == "Mon Feb 16\tPresident's Day"


def test_cli_weekday_flag(tmp_path, monkeypatch):
    """Smoke test: invoke the CLI with -w and verify weekday names appear."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text("01/15\tTest event\n01/16\tAnother event\n")

    monkeypatch.setattr(
        sys,
        "argv",
        ["pylendar", "-w", "-f", str(calendar_file), "-t", "20260115"],
    )
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    main()

    output = stdout.getvalue()
    # Jan 15, 2026 is a Thursday; Jan 16 is a Friday
    assert "Thu Jan 15\tTest event" in output
    assert "Fri Jan 16\tAnother event" in output
