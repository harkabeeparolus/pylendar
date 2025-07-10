#!/usr/bin/env python3
"""Test that ~/.calendar is included in SimpleCPP include paths."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path to import pylendar
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pylendar.pylendar import DEFAULT_CALENDAR_PATHS, SimpleCPP


class TestIncludePaths(unittest.TestCase):
    """Test that ~/.calendar is included in the default include paths."""

    def test_home_calendar_in_default_paths(self):
        """Test that ~/.calendar is included in DEFAULT_CALENDAR_PATHS."""
        home_calendar = Path.home() / ".calendar"
        self.assertIn(home_calendar, DEFAULT_CALENDAR_PATHS)

    def test_simplecpp_include_dirs_contains_home_calendar(self):
        """Test that SimpleCPP instance includes ~/.calendar in include directories."""
        processor = SimpleCPP(include_dirs=DEFAULT_CALENDAR_PATHS)
        home_calendar = Path.home() / ".calendar"
        self.assertIn(home_calendar, processor.include_dirs)

    def test_simplecpp_can_resolve_from_home_calendar(self):
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
            self.assertIn("01/01\tNew Year's Day", result)
            self.assertIn("07/04\tIndependence Day", result)


if __name__ == "__main__":
    unittest.main()