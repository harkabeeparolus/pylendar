"""Tests for find_calendar() and CALENDAR_DIR support."""

from pathlib import Path

import pytest

from pylendar.pylendar import find_calendar


def test_calendar_dir_env_overrides_cwd(tmp_path, monkeypatch):
    """CALENDAR_DIR replaces cwd as the first directory searched."""
    cal_dir = tmp_path / "custom"
    cal_dir.mkdir()
    (cal_dir / "calendar").write_text("03/01\tTest event\n")

    monkeypatch.setenv("CALENDAR_DIR", str(cal_dir))
    monkeypatch.chdir(tmp_path)  # cwd has no calendar file

    result = find_calendar([])
    assert result == (cal_dir / "calendar").resolve()


def test_calendar_dir_unset_uses_cwd(tmp_path, monkeypatch):
    """Without CALENDAR_DIR, cwd is searched first."""
    (tmp_path / "calendar").write_text("03/01\tTest event\n")

    monkeypatch.delenv("CALENDAR_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    result = find_calendar([])
    assert result == (tmp_path / "calendar").resolve()


def test_calendar_dir_missing_falls_through(tmp_path, monkeypatch):
    """If CALENDAR_DIR has no calendar file, fall through to look_in."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    fallback = tmp_path / "fallback"
    fallback.mkdir()
    (fallback / "calendar").write_text("03/01\tFrom fallback\n")

    monkeypatch.setenv("CALENDAR_DIR", str(empty_dir))
    monkeypatch.chdir(tmp_path)
    # Prevent real ~/.calendar from interfering
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

    result = find_calendar([fallback])
    assert result == (fallback / "calendar").resolve()


def test_returns_default_when_nothing_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falls back to Path('calendar') when no file exists."""
    monkeypatch.delenv("CALENDAR_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "fakehome"))
    result = find_calendar([])
    assert result == Path("calendar")
