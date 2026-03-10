"""Tests for the -F (friday), -A (business-day), and -W (calendar-day) flags."""

import datetime
import io
import sys
from pathlib import Path

import pytest

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
    """Test that -W counts plain calendar days on non-Friday days."""
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


# --- -A flag tests (business-day counting with weekend expansion) ---


_A_CALENDAR = (
    "\n".join(
        f"{d.strftime('%m/%d')}\t{d.strftime('%A')}"
        for d in (
            datetime.date(2026, 3, 2) + datetime.timedelta(days=i) for i in range(14)
        )
    )
    + "\n"
)


@pytest.mark.parametrize(
    ("today", "ahead", "expected_days"),
    [
        # Mon -A 5 → 8 days (Mon-Mon, crosses one Fri→Sat+Sun)
        (datetime.date(2026, 3, 2), 5, 8),
        # Thu -A 2 → 5 days (Thu-Mon, crosses one Fri→Sat+Sun)
        (datetime.date(2026, 3, 5), 2, 5),
        # Fri -A 2 → 5 days (Fri-Tue, Sat+Sun are free)
        (datetime.date(2026, 3, 6), 2, 5),
        # Fri -A 0 → 1 day (just today, no expansion)
        (datetime.date(2026, 3, 6), 0, 1),
        # Sat -A 1 → 2 days (no Friday crossed, just Sat+Sun)
        (datetime.date(2026, 3, 7), 1, 2),
    ],
    ids=["mon_A5", "thu_A2", "fri_A2", "fri_A0", "sat_A1"],
)
def test_a_flag_business_day_expansion(run_calendar, today, ahead, expected_days):
    """Test that -A counts business days, expanding weekends for free."""
    result = run_calendar(
        _A_CALENDAR,
        today,
        ahead=ahead,
        expand_weekends=True,
    )
    assert len(result) == expected_days
    # First event should be today.
    assert result[0].startswith(today.strftime("%b"))


def test_a_flag_mon_a5_exact_range(run_calendar):
    """Verify Mon -A 5 includes exactly Mar 2-9 (8 days)."""
    monday = datetime.date(2026, 3, 2)
    result = run_calendar(_A_CALENDAR, monday, ahead=5, expand_weekends=True)
    assert result == [
        "Mar  2\tMonday",
        "Mar  3\tTuesday",
        "Mar  4\tWednesday",
        "Mar  5\tThursday",
        "Mar  6\tFriday",
        "Mar  7\tSaturday",
        "Mar  8\tSunday",
        "Mar  9\tMonday",
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


def test_cli_a_flag_on_friday(tmp_path, monkeypatch):
    """Smoke test: -A 2 on a Friday gives 5 days (Fri-Tue, weekend is free)."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text(
        "03/06\tFriday\n03/07\tSaturday\n03/08\tSunday\n"
        "03/09\tMonday\n03/10\tTuesday\n03/11\tWednesday\n"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["pylendar", "-A", "2", "-f", str(calendar_file), "-t", "20260306"],
    )
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    main()

    lines = stdout.getvalue().strip().splitlines()
    assert len(lines) == 5
    assert "Mar  6\tFriday" in lines[0]
    assert "Mar 10\tTuesday" in lines[-1]
    # Wednesday should NOT appear — only 2 business days ahead.
    assert "Wednesday" not in stdout.getvalue()


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


@pytest.mark.parametrize("f_value", ["0", "6"])
def test_cli_f_flag_accepts_bsd_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    f_value: str,
) -> None:
    """BSD weekday range endpoints are accepted for -F."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text("07/10\tFriday\n")

    monkeypatch.setattr(
        sys,
        "argv",
        ["pylendar", "-F", f_value, "-f", str(calendar_file), "-t", "20260710"],
    )
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    main()

    assert "Jul 10\tFriday" in stdout.getvalue()


def test_cli_f_flag_rejects_out_of_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Out-of-range BSD weekday values are rejected by argparse."""
    calendar_file = tmp_path / "calendar"
    calendar_file.write_text("07/10\tFriday\n")

    monkeypatch.setattr(
        sys,
        "argv",
        ["pylendar", "-F", "7", "-f", str(calendar_file), "-t", "20260710"],
    )

    with pytest.raises(SystemExit):
        main()

    assert "BSD weekday out of range [0-6]" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["-A", "-W", "-B"])
def test_cli_day_window_flags_reject_negative_values(
    flag: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Day window flags must not accept negative values."""
    monkeypatch.setattr(sys, "argv", ["pylendar", flag, "-1"])

    with pytest.raises(SystemExit):
        main()

    err = capsys.readouterr().err
    assert f"argument {flag}: invalid positive_int value" in err
