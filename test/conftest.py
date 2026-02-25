"""Shared test fixtures for pylendar tests."""

import pytest

from pylendar.pylendar import CalendarOptions, process_calendar


@pytest.fixture
def run_calendar(tmp_path):
    """Fixture that processes calendar content and returns sorted event strings."""

    def _run(calendar_content, today, **options):
        calendar_file = tmp_path / "calendar"
        calendar_file.write_text(calendar_content)
        return process_calendar(calendar_file, today, CalendarOptions(**options))

    return _run
