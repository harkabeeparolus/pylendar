"""Tests for parse_today_arg (the -t flag) and _parse_dot_date."""

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
        ("991231", datetime.date(1999, 12, 31)),
        ("20260216", datetime.date(2026, 2, 16)),
    ],
    ids=["dd", "mmdd", "yymmdd-21c", "yymmdd-20c", "ccyymmdd"],
)
def test_positional_formats(arg: str, expected: datetime.date) -> None:
    """Parse positional date formats (DD, MMDD, YYMMDD, CCYYMMDD)."""
    assert parse_today_arg(arg) == expected


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
    ],
    ids=[
        "trailing-dot",
        "too-many-parts",
        "non-numeric",
        "bad-month",
        "bad-day",
        "positional-invalid",
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
