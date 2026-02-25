"""Shared test fixtures for pylendar tests."""

import pytest

from pylendar.pylendar import process_calendar


@pytest.fixture
def run_calendar(tmp_path):
    """Fixture that processes calendar content and returns sorted event strings."""

    def _run(  # pylint: disable=too-many-arguments
        calendar_content,
        today,
        ahead=None,
        behind=0,
        *,
        friday=4,
        weekday=False,
        utc_offset_hours=0,
    ):
        calendar_file = tmp_path / "calendar"
        calendar_file.write_text(calendar_content)
        return process_calendar(
            calendar_file,
            today,
            ahead=ahead,
            behind=behind,
            friday=friday,
            weekday=weekday,
            utc_offset_hours=utc_offset_hours,
        )

    return _run
