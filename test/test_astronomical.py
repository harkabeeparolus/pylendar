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


def test_moon_phases_extreme_negative_offset():
    """Test that an extreme negative UTC offset does not skip the entire year.

    In 2048, the first full moon is exactly on Jan 1st 06:57 UTC.
    With a -8.0 offset, this shifts to Dec 31st 2047 locally. The bug previously
    caused the loop to break on the first iteration, returning an empty set for 2048.
    """
    moon_phases = get_moon_phases(2048, utc_offset_hours=-8.0)

    # We should still find all the other full moons for the rest of 2048
    assert len(moon_phases["fullmoon"]) >= 12
    assert len(moon_phases["newmoon"]) >= 12


def test_moon_phases_extreme_positive_offset():
    """Test that an extreme positive UTC offset does not skip late December phases.

    In 2009, there is a full moon on Dec 31st 19:13 UTC.
    With a +12.0 offset, this shifts to Jan 1st 2010 locally. The bug previously
    caused the search to either break early or skip phases around boundaries.
    """
    moon_phases = get_moon_phases(2010, utc_offset_hours=12.0)

    # We should catch the Jan 1st 2010 local full moon (which was Dec 31st 2009 UTC)
    assert datetime.date(2010, 1, 1) in moon_phases["fullmoon"]
    assert len(moon_phases["fullmoon"]) >= 12
    assert len(moon_phases["newmoon"]) >= 12
