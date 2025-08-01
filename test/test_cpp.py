"""Test SimpleCPP functionality."""

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


def test_simplecpp_custom_include_dir(tmp_path):
    """Test that SimpleCPP accepts a custom include directory."""
    dir_name = "AiSei5Ah"
    temp_dir = tmp_path / dir_name
    temp_dir.mkdir()
    processor = SimpleCPP(include_dirs=[*DEFAULT_CALENDAR_PATHS, temp_dir])
    assert temp_dir in processor.include_dirs


def test_simplecpp_can_resolve_from_home_calendar(tmp_path):
    """Test that SimpleCPP can resolve includes from ~/.calendar directory."""
    # Create a temporary ~/.calendar-like directory
    temp_calendar_directory = tmp_path / ".calendar"
    temp_calendar_directory.mkdir()

    # Create an include file in the fake ~/.calendar directory
    file_name = "xae6eeCi"
    include_file = temp_calendar_directory / file_name
    include_file.write_text("01/01\tNew Year's Day\n")

    # Create a main calendar file that includes the holidays file
    main_calendar = tmp_path / "calendar"
    main_calendar.write_text(f'#include "{file_name}"\n07/04\tIndependence Day\n')

    # Create SimpleCPP with include directories including our fake home calendar
    include_dirs = [temp_calendar_directory, "/etc/calendar"]
    processor = SimpleCPP(include_dirs=include_dirs)

    # Process the main calendar file
    result = processor.process_file(main_calendar)

    # Should contain both the included content and the main content
    assert "01/01\tNew Year's Day" in result
    assert "07/04\tIndependence Day" in result
