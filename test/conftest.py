"""Shared test fixtures for pylendar tests."""

import pytest

from pylendar.pylendar import (
    DateStringParser,
    SimpleCPP,
    format_event,
    get_ahead_behind,
    get_dates_to_check,
    get_matching_event,
    join_continuation_lines,
    parse_special_dates,
)


@pytest.fixture
def run_calendar(tmp_path):
    """Fixture that processes calendar content and returns sorted event strings."""

    def _run(  # pylint: disable=too-many-arguments
        calendar_content, today, ahead=None, behind=0, *, friday=4, weekday=False
    ):
        calendar_file = tmp_path / "calendar"
        calendar_file.write_text(calendar_content)
        calendar_lines = join_continuation_lines(
            SimpleCPP(include_dirs=[]).process_file(calendar_file)
        )

        ahead_days, behind_days = get_ahead_behind(
            today, ahead=ahead, behind=behind, friday=friday
        )
        dates_to_check = get_dates_to_check(today, ahead=ahead_days, behind=behind_days)

        date_exprs = parse_special_dates(calendar_lines, today.year)
        date_parser = DateStringParser(date_exprs)
        matching_events = [
            event
            for line in calendar_lines
            if (event := get_matching_event(line, dates_to_check, date_parser))
        ]
        return [
            format_event(event, weekday=weekday) for event in sorted(matching_events)
        ]

    return _run
