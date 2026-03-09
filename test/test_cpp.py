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


def test_circular_include_skipped(tmp_path: Path) -> None:
    """Circular includes are silently skipped (once-only inclusion)."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_text('#include "b"\n01/01\tA event\n')
    b.write_text('#include "a"\n02/02\tB event\n')
    cpp = SimpleCPP(include_dirs=[tmp_path])
    result = cpp.process_file(a)
    assert "01/01\tA event" in result
    assert "02/02\tB event" in result


# --- locale fallback ---


def test_resolve_include_locale_fallback(tmp_path: Path) -> None:
    """uk_UA/calendar.all resolves to uk_UA.KOI8-U/calendar.all."""
    locale_dir = tmp_path / "uk_UA.KOI8-U"
    locale_dir.mkdir()
    target = locale_dir / "calendar.all"
    target.write_text("01/01\tNew Year\n")

    cpp = SimpleCPP(include_dirs=[tmp_path])
    result = cpp.resolve_include(Path("uk_UA/calendar.all"))
    assert result == target.resolve()


def test_resolve_include_locale_direct_preferred(tmp_path: Path) -> None:
    """Exact uk_UA/ directory takes priority over locale fallback."""
    # Create both exact and encoding-suffixed directories
    exact_dir = tmp_path / "uk_UA"
    exact_dir.mkdir()
    exact_file = exact_dir / "calendar.all"
    exact_file.write_text("exact\n")

    fallback_dir = tmp_path / "uk_UA.KOI8-U"
    fallback_dir.mkdir()
    fallback_file = fallback_dir / "calendar.all"
    fallback_file.write_text("fallback\n")

    cpp = SimpleCPP(include_dirs=[tmp_path])
    result = cpp.resolve_include(Path("uk_UA/calendar.all"))
    assert result == exact_file.resolve()


def test_resolve_include_locale_utf8_preferred(tmp_path: Path) -> None:
    """UTF-8 encoding directory is preferred over other encodings."""
    koi8_dir = tmp_path / "ru_RU.KOI8-R"
    koi8_dir.mkdir()
    (koi8_dir / "calendar.all").write_text("koi8\n")

    utf8_dir = tmp_path / "ru_RU.UTF-8"
    utf8_dir.mkdir()
    (utf8_dir / "calendar.all").write_text("utf8\n")

    cpp = SimpleCPP(include_dirs=[tmp_path])
    result = cpp.resolve_include(Path("ru_RU/calendar.all"))
    assert result == (utf8_dir / "calendar.all").resolve()


def test_include_locale_fallback_e2e(tmp_path: Path) -> None:
    """End-to-end: #include <uk_UA/calendar.all> resolves via fallback."""
    locale_dir = tmp_path / "uk_UA.KOI8-U"
    locale_dir.mkdir()
    (locale_dir / "calendar.all").write_text("01/01\tUkrainian New Year\n")

    main = tmp_path / "calendar"
    main.write_text("#include <uk_UA/calendar.all>\n07/04\tMain event\n")

    cpp = SimpleCPP(include_dirs=[tmp_path])
    result = cpp.process_file(main)
    assert "01/01\tUkrainian New Year" in result
    assert "07/04\tMain event" in result


# --- non-UTF-8 file handling ---


def test_process_file_skips_non_utf8(tmp_path: Path) -> None:
    """File with non-UTF-8 bytes is skipped with a warning."""
    bad_file = tmp_path / "calendar.koi8"
    bad_file.write_bytes(b"\xc1\xc2\xc3\n")  # invalid UTF-8

    cpp = SimpleCPP(include_dirs=[tmp_path])
    result = cpp.process_file(bad_file)
    assert not result


def test_malformed_include_raises(tmp_path: Path) -> None:
    """Bare #include with no filename raises SyntaxError."""
    cal = tmp_path / "calendar"
    cal.write_text("#include\n")
    cpp = SimpleCPP(include_dirs=[tmp_path])
    with pytest.raises(SyntaxError, match="Malformed include"):
        cpp.process_file(cal)
