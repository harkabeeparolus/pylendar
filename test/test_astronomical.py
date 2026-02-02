"""Tests for astronomical special dates (moon phases and seasons)."""

import datetime

from pylendar.pylendar import get_moon_phases, get_seasons


def test_get_seasons_2026():
    """Test that seasons are calculated correctly for 2026."""
    seasons = get_seasons(2026)

    # Verify we have all four seasons
    assert "marequinox" in seasons
    assert "junsolstice" in seasons
    assert "sepequinox" in seasons
    assert "decsolstice" in seasons

    # Verify the dates are in the correct months
    assert seasons["marequinox"].month == 3
    assert seasons["junsolstice"].month == 6
    assert seasons["sepequinox"].month == 9
    assert seasons["decsolstice"].month == 12

    # Verify they're all in 2026
    assert seasons["marequinox"].year == 2026
    assert seasons["junsolstice"].year == 2026
    assert seasons["sepequinox"].year == 2026
    assert seasons["decsolstice"].year == 2026


def test_get_moon_phases_2026():
    """Test that moon phases are calculated correctly for 2026."""
    moon_phases = get_moon_phases(2026)

    # Verify we have both types of moon phases
    assert "newmoon" in moon_phases
    assert "fullmoon" in moon_phases

    # Verify we have approximately 12-13 of each (lunar cycle is ~29.5 days)
    assert 12 <= len(moon_phases["newmoon"]) <= 14
    assert 12 <= len(moon_phases["fullmoon"]) <= 14

    # Verify all dates are in 2026
    for phase_date in moon_phases["newmoon"]:
        assert phase_date.year == 2026
    for phase_date in moon_phases["fullmoon"]:
        assert phase_date.year == 2026

    # Verify first new moon of 2026 is in January
    new_moons_sorted = sorted(moon_phases["newmoon"])
    assert new_moons_sorted[0].month == 1

    # Verify first full moon of 2026 is in January
    full_moons_sorted = sorted(moon_phases["fullmoon"])
    assert full_moons_sorted[0].month == 1


def test_moon_phases_roughly_monthly():
    """Test that moon phases occur roughly once per month."""
    moon_phases = get_moon_phases(2026)

    # New moons should be roughly 29-30 days apart
    new_moons = sorted(moon_phases["newmoon"])
    for i in range(len(new_moons) - 1):
        days_between = (new_moons[i + 1] - new_moons[i]).days
        assert 27 <= days_between <= 31, (
            f"New moons should be ~29.5 days apart, "
            f"got {days_between} days between {new_moons[i]} and {new_moons[i + 1]}"
        )

    # Full moons should also be roughly 29-30 days apart
    full_moons = sorted(moon_phases["fullmoon"])
    for i in range(len(full_moons) - 1):
        days_between = (full_moons[i + 1] - full_moons[i]).days
        assert 27 <= days_between <= 31, (
            f"Full moons should be ~29.5 days apart, "
            f"got {days_between} days between {full_moons[i]} and {full_moons[i + 1]}"
        )


def test_seasons_are_in_correct_order():
    """Test that seasons occur in the expected chronological order."""
    seasons = get_seasons(2026)

    # Create list of (name, date) tuples
    season_list = [
        ("marequinox", seasons["marequinox"]),
        ("junsolstice", seasons["junsolstice"]),
        ("sepequinox", seasons["sepequinox"]),
        ("decsolstice", seasons["decsolstice"]),
    ]

    # Verify they're in chronological order
    for i in range(len(season_list) - 1):
        assert season_list[i][1] < season_list[i + 1][1], (
            f"{season_list[i][0]} should come before {season_list[i + 1][0]}"
        )


def test_seasons_specific_dates_2026():
    """Test specific known season dates for 2026."""
    seasons = get_seasons(2026)

    # March equinox 2026 is on March 20
    assert seasons["marequinox"] == datetime.date(2026, 3, 20)

    # June solstice 2026 is on June 21
    assert seasons["junsolstice"] == datetime.date(2026, 6, 21)

    # September equinox 2026 is on September 23
    assert seasons["sepequinox"] == datetime.date(2026, 9, 23)

    # December solstice 2026 is on December 21
    assert seasons["decsolstice"] == datetime.date(2026, 12, 21)


def test_moon_phases_specific_dates_2026():
    """Test specific known moon phase dates for January 2026."""
    moon_phases = get_moon_phases(2026)

    # January 2026 new moon is on the 18th
    assert datetime.date(2026, 1, 18) in moon_phases["newmoon"]

    # January 2026 full moon is on the 3rd
    assert datetime.date(2026, 1, 3) in moon_phases["fullmoon"]
