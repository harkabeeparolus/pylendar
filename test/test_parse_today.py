"""Tests for parse_today_arg (the -t flag) and _parse_dot_date."""

import calendar
import datetime

import pytest

from pylendar.pylendar import main, parse_today_arg

_TODAY = datetime.date.today()

# --- OpenBSD/Debian positional format (regression tests) ---


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("15", datetime.date(_TODAY.year, _TODAY.month, 15)),
        ("0704", datetime.date(_TODAY.year, 7, 4)),
        ("260704", datetime.date(2026, 7, 4)),
        ("680101", datetime.date(2068, 1, 1)),
        ("690101", datetime.date(1969, 1, 1)),
        ("991231", datetime.date(1999, 12, 31)),
        ("20260216", datetime.date(2026, 2, 16)),
    ],
    ids=[
        "dd",
        "mmdd",
        "yymmdd-21c",
        "yymmdd-pivot-to-21c",
        "yymmdd-pivot-to-20c",
        "yymmdd-20c",
        "ccyymmdd",
    ],
)
def test_positional_formats(arg: str, expected: datetime.date) -> None:
    """Parse positional date formats (DD, MMDD, YYMMDD, CCYYMMDD)."""
    assert parse_today_arg(arg) == expected


# --- ISO 8601 format ---


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("2026-03-02", datetime.date(2026, 3, 2)),
        ("1999-12-31", datetime.date(1999, 12, 31)),
        ("May 15", datetime.date(_TODAY.year, 5, 15)),
        ("15 May", datetime.date(_TODAY.year, 5, 15)),
    ],
    ids=["typical", "end-of-century", "month-day", "day-month"],
)
def test_iso_formats(arg: str, expected: datetime.date) -> None:
    """Parse ISO and single-date parser expressions in -t."""
    assert parse_today_arg(arg) == expected


def test_weekday_relative_expression() -> None:
    """Parse weekday-relative expressions via DateStringParser fallback."""
    anchor = datetime.date(_TODAY.year, 6, 19)
    candidate = anchor + datetime.timedelta(days=1)
    while candidate.weekday() != calendar.SATURDAY:
        candidate += datetime.timedelta(days=1)
    assert parse_today_arg("Sat>Jun 19") == candidate


# --- macOS/FreeBSD dot-separated format ---


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("16.02", datetime.date(_TODAY.year, 2, 16)),
        ("4.7.2026", datetime.date(2026, 7, 4)),
        ("5.6", datetime.date(_TODAY.year, 6, 5)),
        ("01.01.2000", datetime.date(2000, 1, 1)),
        ("1.1.99", datetime.date(99, 1, 1)),
        ("  16.02  ", datetime.date(_TODAY.year, 2, 16)),
    ],
    ids=[
        "dd-mm",
        "dd-mm-year",
        "single-digit",
        "zero-padded",
        "year-literal",
        "whitespace",
    ],
)
def test_dot_formats(arg: str, expected: datetime.date) -> None:
    """Parse dot-separated date formats (dd.mm, dd.mm.year)."""
    assert parse_today_arg(arg) == expected


# --- Error cases ---


@pytest.mark.parametrize(
    ("arg", "match"),
    [
        ("16.", r"Invalid|Non-numeric|Out-of-range"),
        ("16.02.2026.99", r"Invalid"),
        ("ab.cd", r"Non-numeric"),
        ("1.13.2026", r"Out-of-range"),
        ("32.1.2026", r"Out-of-range"),
        ("abc", r"Invalid"),
        ("2026-13-01", r"Invalid|does not resolve"),
        ("2026-02-30", r"Invalid|does not resolve"),
        ("Friday", r"Ambiguous"),
        ("* 15", r"Ambiguous"),
    ],
    ids=[
        "trailing-dot",
        "too-many-parts",
        "non-numeric",
        "bad-month",
        "bad-day",
        "positional-invalid",
        "iso-bad-month",
        "iso-bad-day",
        "weekday-ambiguous",
        "wildcard-ambiguous",
    ],
)
def test_invalid_inputs(arg: str, match: str) -> None:
    """Reject malformed date strings with appropriate error messages."""
    with pytest.raises(Exception, match=match):
        parse_today_arg(arg)


# --- CLI integration ---


def test_cli_dot_format(tmp_path, capsys):
    """End-to-end: -t with dot-separated date selects the right events."""
    cal = tmp_path / "calendar"
    cal.write_text("07/04\tIndependence Day\n")
    main(["-t", "4.7.2026", "-f", str(cal)])
    assert "Jul  4\tIndependence Day" in capsys.readouterr().out
