"""Test that ~/.calendar is included in SimpleCPP include paths."""

import tempfile
from pathlib import Path

from pylendar.pylendar import DEFAULT_CALENDAR_PATHS, SimpleCPP


def test_home_calendar_in_default_paths():
    """Test that ~/.calendar is included in DEFAULT_CALENDAR_PATHS."""
    home_calendar = Path.home() / ".calendar"
    assert home_calendar in DEFAULT_CALENDAR_PATHS


def test_home_calendar_is_first_in_default_paths():
    """Test that ~/.calendar is the first directory in DEFAULT_CALENDAR_PATHS."""
    home_calendar = Path.home() / ".calendar"
    assert DEFAULT_CALENDAR_PATHS[0] == home_calendar


def test_simplecpp_include_dirs_contains_home_calendar():
    """Test that SimpleCPP instance includes ~/.calendar in include directories."""
    processor = SimpleCPP(include_dirs=DEFAULT_CALENDAR_PATHS)
    home_calendar = Path.home() / ".calendar"
    assert home_calendar in processor.include_dirs


def test_simplecpp_can_resolve_from_home_calendar():
    """Test that SimpleCPP can resolve includes from ~/.calendar directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a temporary ~/.calendar-like directory
        fake_home_calendar = Path(temp_dir) / ".calendar"
        fake_home_calendar.mkdir()

        # Create an include file in the fake ~/.calendar directory
        include_file = fake_home_calendar / "holidays"
        include_file.write_text("01/01\tNew Year's Day\n")

        # Create a main calendar file that includes the holidays file
        main_calendar = Path(temp_dir) / "calendar"
        main_calendar.write_text('#include "holidays"\n07/04\tIndependence Day\n')

        # Create SimpleCPP with include directories including our fake home calendar
        include_dirs = [fake_home_calendar, "/etc/calendar"]
        processor = SimpleCPP(include_dirs=include_dirs)

        # Process the main calendar file
        result = processor.process_file(main_calendar)

        # Should contain both the included content and the main content
        assert "01/01\tNew Year's Day" in result
        assert "07/04\tIndependence Day" in result
