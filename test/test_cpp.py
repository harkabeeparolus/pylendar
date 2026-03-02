"""Test SimpleCPP functionality."""

from pathlib import Path

import pytest

from pylendar.pylendar import SimpleCPP


def test_simplecpp_can_resolve_includes(tmp_path):
    """Test that SimpleCPP can resolve #include directives."""
    # Create a temporary directory with an include file
    temp_calendar_directory = tmp_path / ".calendar"
    temp_calendar_directory.mkdir()

    include_file = temp_calendar_directory / "holidays"
    include_file.write_text("01/01\tNew Year's Day\n")

    # Create a main calendar file that includes the holidays file
    main_calendar = tmp_path / "calendar"
    main_calendar.write_text('#include "holidays"\n07/04\tIndependence Day\n')

    processor = SimpleCPP(include_dirs=[temp_calendar_directory])
    result = processor.process_file(main_calendar)

    assert "01/01\tNew Year's Day" in result
    assert "07/04\tIndependence Day" in result


def test_include_not_found_skips(tmp_path: Path) -> None:
    """Missing include file is silently skipped (with a log warning)."""
    cal = tmp_path / "calendar"
    cal.write_text('#include "nonexistent.file"\n01/01\tNew Year\n')
    cpp = SimpleCPP(include_dirs=[tmp_path])
    result = cpp.process_file(cal)
    assert result == ["01/01\tNew Year"]


def test_malformed_include_raises(tmp_path: Path) -> None:
    """Bare #include with no filename raises SyntaxError."""
    cal = tmp_path / "calendar"
    cal.write_text("#include\n")
    cpp = SimpleCPP(include_dirs=[tmp_path])
    with pytest.raises(SyntaxError, match="Malformed include"):
        cpp.process_file(cal)
