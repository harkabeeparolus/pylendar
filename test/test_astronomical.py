"""Tests for astronomical special dates (moon phases and seasons)."""

import datetime
from itertools import pairwise

from pylendar.pylendar import get_moon_phases, get_seasons


def test_seasons_2026():
    """Test that seasons have correct keys, order, and specific dates for 2026."""
    seasons = get_seasons(2026)

    assert seasons == {
        "marequinox": datetime.date(2026, 3, 20),
        "junsolstice": datetime.date(2026, 6, 21),
        "sepequinox": datetime.date(2026, 9, 23),
        "decsolstice": datetime.date(2026, 12, 21),
    }


def test_moon_phases_2026():
    """Test moon phase counts, years, and known January 2026 dates."""
    moon_phases = get_moon_phases(2026)

    # Both phase types present with ~12-13 each
    assert 12 <= len(moon_phases["newmoon"]) <= 14
    assert 12 <= len(moon_phases["fullmoon"]) <= 14

    # All dates in 2026
    for phase_date in [*moon_phases["newmoon"], *moon_phases["fullmoon"]]:
        assert phase_date.year == 2026

    # Known January 2026 dates
    assert datetime.date(2026, 1, 18) in moon_phases["newmoon"]
    assert datetime.date(2026, 1, 3) in moon_phases["fullmoon"]


def test_moon_phases_roughly_monthly():
    """Test that moon phases occur roughly once per month."""
    moon_phases = get_moon_phases(2026)

    # New moons should be roughly 29-30 days apart
    new_moons = sorted(moon_phases["newmoon"])
    for m1, m2 in pairwise(new_moons):
        days_between = (m2 - m1).days
        assert 27 <= days_between <= 31, (
            f"New moons should be ~29.5 days apart, "
            f"got {days_between} days between {m1} and {m2}"
        )

    # Full moons should also be roughly 29-30 days apart
    full_moons = sorted(moon_phases["fullmoon"])
    for m1, m2 in pairwise(full_moons):
        days_between = (m2 - m1).days
        assert 27 <= days_between <= 31, (
            f"Full moons should be ~29.5 days apart, "
            f"got {days_between} days between {m1} and {m2}"
        )
