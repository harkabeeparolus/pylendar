import datetime

from pylendar.pylendar import get_ahead_behind


def test_get_ahead_behind_defaults():
    """Test get_ahead_behind with default behavior."""
    # Test weekday (Tuesday) - should default to 1 ahead, 0 behind
    tuesday = datetime.date(2024, 7, 9)  # Tuesday
    ahead, behind = get_ahead_behind(tuesday)
    assert ahead == 1
    assert behind == 0

    # Test Friday - should default to 3 ahead, 0 behind
    friday = datetime.date(2024, 7, 12)  # Friday
    ahead, behind = get_ahead_behind(friday)
    assert ahead == 3
    assert behind == 0


def test_get_ahead_behind_explicit_values():
    """Test get_ahead_behind with explicitly provided values."""
    # Test with explicit ahead value on Friday (should override default)
    friday = datetime.date(2024, 7, 12)  # Friday
    ahead, behind = get_ahead_behind(friday, ahead=5, behind=2)
    assert ahead == 5
    assert behind == 2

    # Test with explicit ahead=1 on Friday (should not use Friday default of 3)
    ahead, behind = get_ahead_behind(friday, ahead=1, behind=0)
    assert ahead == 1
    assert behind == 0


def test_get_ahead_behind_all_weekdays():
    """Test get_ahead_behind default behavior across all weekdays."""
    # Test each day of the week
    # Monday (0) through Thursday (3) should default to 1 ahead
    for weekday in range(4):  # Monday=0, Tuesday=1, Wednesday=2, Thursday=3
        test_date = datetime.date(2024, 7, 8) + datetime.timedelta(
            days=weekday
        )  # July 8-11, 2024
        ahead, behind = get_ahead_behind(test_date)
        assert ahead == 1, f"Weekday {weekday} should have ahead=1, got {ahead}"
        assert behind == 0, f"Weekday {weekday} should have behind=0, got {behind}"

    # Friday (4) should default to 3 ahead
    friday = datetime.date(2024, 7, 12)  # Friday
    ahead, behind = get_ahead_behind(friday)
    assert ahead == 3, f"Friday should have ahead=3, got {ahead}"
    assert behind == 0, f"Friday should have behind=0, got {behind}"

    # Saturday (5) and Sunday (6) should default to 1 ahead
    for weekday in [5, 6]:  # Saturday=5, Sunday=6
        test_date = datetime.date(2024, 7, 13) + datetime.timedelta(
            days=weekday - 5
        )  # July 13-14, 2024
        ahead, behind = get_ahead_behind(test_date)
        assert ahead == 1, f"Weekday {weekday} should have ahead=1, got {ahead}"
        assert behind == 0, f"Weekday {weekday} should have behind=0, got {behind}"
