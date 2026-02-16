"""Tests for the -F (friday) and -W (weekend-ignore) flags."""

import datetime
import io
import sys

from pylendar.pylendar import main

# --- -F flag tests ---


def test_f_flag_changes_friday_day(run_calendar):
    """Test that -F changes which day triggers the 3-day look-ahead."""
    calendar_content = """\
07/09\tThursday event
07/10\tFriday event
07/11\tSaturday event
07/12\tSunday event
"""
    # July 9, 2026 is a Thursday
    thursday = datetime.date(2026, 7, 9)

    # Default friday=4 (Friday): Thursday gets ahead=1
    result = run_calendar(calendar_content, thursday)
    assert result == [
        "Jul  9\tThursday event",
        "Jul 10\tFriday event",
    ]

    # With friday=3 (Thursday via Python weekday): Thursday gets ahead=3
    result = run_calendar(calendar_content, thursday, friday=3)
    assert result == [
        "Jul  9\tThursday event",
        "Jul 10\tFriday event",
        "Jul 11\tSaturday event",
        "Jul 12\tSunday event",
    ]


def test_f_flag_friday_no_longer_special(run_calendar):
    """Test that -F to a non-Friday day means Friday gets default ahead=1."""
    calendar_content = """\
07/10\tFriday event
07/11\tSaturday event
07/12\tSunday event
07/13\tMonday event
"""
    # July 10, 2026 is a Friday
    friday = datetime.date(2026, 7, 10)

    # With friday=3 (Thursday): Friday is no longer special, gets ahead=1
    result = run_calendar(calendar_content, friday, friday=3)
    assert result == [
        "Jul 10\tFriday event",
        "Jul 11\tSaturday event",
    ]


# --- -W flag tests ---


def test_w_flag_disables_friday_expansion(run_calendar):
    """Test that -W provides explicit ahead, bypassing Friday logic."""
    calendar_content = """\
07/10\tFriday event
07/11\tSaturday event
07/12\tSunday event
07/13\tMonday event
07/14\tTuesday event
07/15\tWednesday event
"""
    # July 10, 2026 is a Friday — normally gets ahead=3
    friday = datetime.date(2026, 7, 10)

    # With -W 5, get exactly 5 days forward (no Friday expansion)
    result = run_calendar(calendar_content, friday, ahead=5)
    assert result == [
        "Jul 10\tFriday event",
        "Jul 11\tSaturday event",
        "Jul 12\tSunday event",
        "Jul 13\tMonday event",
        "Jul 14\tTuesday event",
        "Jul 15\tWednesday event",
    ]


def test_w_flag_on_non_friday(run_calendar):
    """Test that -W works the same as -A on non-Friday days."""
    calendar_content = """\
07/08\tWednesday event
07/09\tThursday event
"""
    wednesday = datetime.date(2026, 7, 8)
    result = run_calendar(calendar_content, wednesday, ahead=1)
    assert result == [
        "Jul  8\tWednesday event",
        "Jul  9\tThursday event",
    ]


# --- CLI integration tests ---


def test_cli_f_flag(tmp_path, monkeypatch):
    """Smoke test: -F 4 (BSD Thursday) makes Thursday trigger 3-day look-ahead."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text(
        "07/09\tThursday event\n07/10\tFriday event\n"
        "07/11\tSaturday event\n07/12\tSunday event\n"
    )

    # July 9, 2026 is a Thursday; -F 4 = BSD Thursday = Python Wednesday (no!)
    # BSD 4 = Thursday -> Python weekday 3 (Thursday)
    monkeypatch.setattr(
        sys,
        "argv",
        ["pylendar", "-F", "4", "-f", str(calendar_file), "-t", "20260709"],
    )
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    main()

    output = stdout.getvalue()
    # Thursday with -F 4 (BSD Thursday = Python 3) triggers 3-day look-ahead
    assert "Jul  9\tThursday event" in output
    assert "Jul 10\tFriday event" in output
    assert "Jul 11\tSaturday event" in output
    assert "Jul 12\tSunday event" in output


def test_cli_w_flag(tmp_path, monkeypatch):
    """Smoke test: -W 5 on a Friday gives exactly 5 days forward."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text(
        "07/10\tFriday\n07/11\tSaturday\n07/12\tSunday\n"
        "07/13\tMonday\n07/14\tTuesday\n07/15\tWednesday\n"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["pylendar", "-W", "5", "-f", str(calendar_file), "-t", "20260710"],
    )
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    main()

    output = stdout.getvalue()
    assert "Jul 10\tFriday" in output
    assert "Jul 15\tWednesday" in output
