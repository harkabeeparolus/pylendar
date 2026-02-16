"""Tests for parse_today_arg (the -t flag) and _parse_dot_date."""

import datetime

import pytest

from pylendar.pylendar import main, parse_today_arg

# --- OpenBSD/Debian positional format (regression tests) ---


def test_dd_only():
    """Parse two-digit day-only format."""
    today = datetime.date.today()
    assert parse_today_arg("15") == datetime.date(today.year, today.month, 15)


def test_mmdd():
    """Parse four-digit mmdd format."""
    today = datetime.date.today()
    assert parse_today_arg("0704") == datetime.date(today.year, 7, 4)


def test_yymmdd_21st_century():
    """Parse six-digit yymmdd with 21st-century year."""
    assert parse_today_arg("260704") == datetime.date(2026, 7, 4)


def test_yymmdd_20th_century():
    """Parse six-digit yymmdd with 20th-century year (69-99)."""
    assert parse_today_arg("991231") == datetime.date(1999, 12, 31)


def test_ccyymmdd():
    """Parse eight-digit ccyymmdd format."""
    assert parse_today_arg("20260216") == datetime.date(2026, 2, 16)


# --- macOS/FreeBSD dot-separated format ---


def test_dot_dd_mm():
    """Parse dd.mm format, year defaults to current year."""
    today = datetime.date.today()
    assert parse_today_arg("16.02") == datetime.date(today.year, 2, 16)


def test_dot_dd_mm_year():
    """Parse dd.mm.year format."""
    assert parse_today_arg("4.7.2026") == datetime.date(2026, 7, 4)


def test_dot_single_digit_day_and_month():
    """Parse single-digit day and month (FreeBSD sscanf behavior)."""
    today = datetime.date.today()
    assert parse_today_arg("5.6") == datetime.date(today.year, 6, 5)


def test_dot_zero_padded():
    """Parse zero-padded dd.mm.year format."""
    assert parse_today_arg("01.01.2000") == datetime.date(2000, 1, 1)


def test_dot_year_literal_no_heuristic():
    """Year is taken literally — 99 means year 99, not 1999."""
    assert parse_today_arg("1.1.99") == datetime.date(99, 1, 1)


def test_dot_with_whitespace():
    """Leading/trailing whitespace is stripped before parsing."""
    today = datetime.date.today()
    assert parse_today_arg("  16.02  ") == datetime.date(today.year, 2, 16)


# --- Error cases ---


def test_dot_trailing_dot():
    """Trailing dot produces an empty part, which is rejected."""
    with pytest.raises(Exception, match=r"Invalid|Non-numeric|Out-of-range"):
        parse_today_arg("16.")


def test_dot_too_many_parts():
    """More than three dot-separated parts is rejected."""
    with pytest.raises(Exception, match=r"Invalid"):
        parse_today_arg("16.02.2026.99")


def test_dot_non_numeric():
    """Non-numeric values in dot-separated date are rejected."""
    with pytest.raises(Exception, match=r"Non-numeric"):
        parse_today_arg("ab.cd")


def test_dot_out_of_range_month():
    """Month > 12 is rejected."""
    with pytest.raises(Exception, match=r"Out-of-range"):
        parse_today_arg("1.13.2026")


def test_dot_out_of_range_day():
    """Day > 31 is rejected."""
    with pytest.raises(Exception, match=r"Out-of-range"):
        parse_today_arg("32.1.2026")


def test_positional_invalid():
    """Non-numeric positional input is rejected."""
    with pytest.raises(Exception, match=r"Invalid"):
        parse_today_arg("abc")


# --- CLI integration ---


def test_cli_dot_format(tmp_path, capsys):
    """End-to-end: -t with dot-separated date selects the right events."""
    cal = tmp_path / "calendar"
    cal.write_text("07/04\tIndependence Day\n")
    main(["-t", "4.7.2026", "-f", str(cal)])
    assert "Jul  4\tIndependence Day" in capsys.readouterr().out
