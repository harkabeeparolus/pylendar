"""Tests for --init starter-calendar support."""

import datetime
import logging
import sys
from pathlib import Path

import pytest

from pylendar.pylendar import (
    STARTER_CALENDAR,
    CalendarOptions,
    main,
    process_calendar,
    write_starter_calendar,
)


def test_write_starter_calendar_creates_file(tmp_path: Path) -> None:
    """Writes the starter file and creates parent directories."""
    target = tmp_path / "fake_home" / ".calendar" / "calendar"
    assert write_starter_calendar(target) is True
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == STARTER_CALENDAR


def test_write_starter_calendar_refuses_to_overwrite(tmp_path: Path) -> None:
    """Refuses to overwrite an existing file and leaves contents untouched."""
    target = tmp_path / ".calendar" / "calendar"
    target.parent.mkdir()
    target.write_text("Jan 1\tCustom event\n", encoding="utf-8")

    assert write_starter_calendar(target) is False
    assert target.read_text(encoding="utf-8") == "Jan 1\tCustom event\n"


def test_starter_calendar_parses_cleanly(tmp_path: Path) -> None:
    """The starter calendar must parse without raising SyntaxError."""
    target = tmp_path / "calendar"
    target.write_text(STARTER_CALENDAR, encoding="utf-8")

    today = datetime.date(2026, 1, 1)
    process_calendar(target, today, CalendarOptions(ahead=1))


def test_cli_init_writes_to_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`pylendar --init` writes to ~/.calendar/calendar under the patched home."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    monkeypatch.setattr(sys, "argv", ["pylendar", "--init"])

    main()

    target = fake_home / ".calendar" / "calendar"
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == STARTER_CALENDAR

    out = capsys.readouterr().out
    assert str(target) in out


def test_cli_init_second_run_does_not_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A second `--init` run leaves the existing file intact and reports it."""
    fake_home = tmp_path / "home"
    target = fake_home / ".calendar" / "calendar"
    target.parent.mkdir(parents=True)
    target.write_text("Jan 1\tCustom event\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    monkeypatch.setattr(sys, "argv", ["pylendar", "--init"])

    main()

    assert target.read_text(encoding="utf-8") == "Jan 1\tCustom event\n"
    out = capsys.readouterr().out
    assert "not overwriting" in out
    assert str(target) in out


def test_cli_no_calendar_warning_mentions_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Missing-calendar warning suggests --init and the home target path."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    monkeypatch.setattr("pylendar.pylendar.DEFAULT_CALENDAR_PATHS", [])
    monkeypatch.delenv("CALENDAR_DIR", raising=False)
    monkeypatch.chdir(tmp_path)  # cwd has no calendar
    monkeypatch.setattr(sys, "argv", ["pylendar"])

    with caplog.at_level(logging.WARNING, logger="pylendar"):
        main()

    target = fake_home / ".calendar" / "calendar"
    messages = [r.getMessage() for r in caplog.records]
    assert any("--init" in m and str(target) in m for m in messages), messages


def test_cli_uses_found_calendar_when_no_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without -f, main() resolves and reads a calendar discovered in cwd."""
    (tmp_path / "calendar").write_text("Apr 22\tEarth Day\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CALENDAR_DIR", raising=False)
    monkeypatch.setattr(sys, "argv", ["pylendar", "-t", "20260422"])

    main()

    assert "Earth Day" in capsys.readouterr().out


def test_cli_f_missing_file_does_not_suggest_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When -f points at a missing file, the warning names that file, not --init."""
    missing = tmp_path / "no-such-file"
    monkeypatch.setattr(sys, "argv", ["pylendar", "-f", str(missing)])

    with caplog.at_level(logging.WARNING, logger="pylendar"):
        main()

    messages = [r.getMessage() for r in caplog.records]
    assert any(str(missing) in m and "--init" not in m for m in messages), messages
