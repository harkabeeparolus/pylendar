"""Tests for LANG= and SEQUENCE= calendar directives."""

import datetime
import locale
import logging

import pytest

from pylendar.pylendar import (
    CalendarDirectives,
    DateStringParser,
    extract_directives,
)

# ---------------------------------------------------------------------------
# extract_directives() unit tests
# ---------------------------------------------------------------------------


class TestExtractDirectives:
    """Tests for parsing LANG= and SEQUENCE= from calendar lines."""

    def test_lang_directive(self) -> None:
        """LANG= value is extracted from a directive line."""
        lines = ["LANG=de_DE.UTF-8", "01/01\tNew Year"]
        result = extract_directives(lines)
        assert result.lang == "de_DE.UTF-8"

    def test_sequence_directive(self) -> None:
        """SEQUENCE= value is extracted as a 6-word tuple."""
        lines = ["SEQUENCE=premier deuxieme troisieme quatrieme cinquieme dernier"]
        result = extract_directives(lines)
        assert result.sequence == (
            "premier",
            "deuxieme",
            "troisieme",
            "quatrieme",
            "cinquieme",
            "dernier",
        )

    def test_last_occurrence_wins(self) -> None:
        """When a directive appears twice, the last value is used."""
        lines = ["LANG=fr_FR.UTF-8", "LANG=de_DE.UTF-8"]
        result = extract_directives(lines)
        assert result.lang == "de_DE.UTF-8"

    def test_lines_with_tabs_are_skipped(self) -> None:
        """Lines containing tabs are events, not directives."""
        lines = ["LANG=de_DE.UTF-8\tsome event"]
        result = extract_directives(lines)
        assert result.lang is None

    def test_case_sensitive_key(self) -> None:
        """Directive keys are case-sensitive (LANG, not lang or Lang)."""
        lines = ["lang=de_DE.UTF-8", "Lang=de_DE.UTF-8"]
        result = extract_directives(lines)
        assert result.lang is None

    def test_empty_lang_is_none(self) -> None:
        """LANG= with empty value results in None."""
        lines = ["LANG="]
        result = extract_directives(lines)
        assert result.lang is None

    def test_sequence_wrong_word_count_warns(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """SEQUENCE= with wrong number of words warns and is ignored."""
        lines = ["SEQUENCE=one two three"]
        with caplog.at_level(logging.WARNING, logger="pylendar"):
            result = extract_directives(lines)
        assert result.sequence is None
        assert "exactly 6 words" in caplog.text

    def test_no_directives(self) -> None:
        """Files without directives return default CalendarDirectives."""
        lines = ["01/01\tNew Year", "# comment"]
        result = extract_directives(lines)
        assert result == CalendarDirectives()

    def test_both_directives(self) -> None:
        """Both LANG= and SEQUENCE= are extracted from the same file."""
        lines = [
            "LANG=fr_FR.UTF-8",
            "SEQUENCE=premier deuxieme troisieme quatrieme cinquieme dernier",
        ]
        result = extract_directives(lines)
        assert result.lang == "fr_FR.UTF-8"
        assert result.sequence is not None


# ---------------------------------------------------------------------------
# LANG= effect on DateStringParser
# ---------------------------------------------------------------------------


class TestLangDirective:
    """Tests for LANG= directive integration with DateStringParser."""

    @pytest.mark.parametrize("lang", ["C", "POSIX", "UTF-8"])
    def test_noop_lang_values(self, lang: str) -> None:
        """LANG=C/POSIX/UTF-8 does not change the parser's month map."""
        parser = DateStringParser(
            directives=CalendarDirectives(lang=lang),
        )
        assert "jan" in parser.month_map

    @staticmethod
    def _locale_available(loc: str) -> bool:
        """Check whether a locale is installed on this system."""
        try:
            locale.setlocale(locale.LC_ALL, loc)
        except locale.Error:
            return False
        else:
            return True
        finally:
            locale.setlocale(locale.LC_ALL, "")

    @pytest.fixture
    def german_locale(self) -> str:
        """Return an available German locale name, or skip the test."""
        for loc in ("de_DE.UTF-8", "de_DE.utf8", "de_DE"):
            if self._locale_available(loc):
                return loc
        pytest.skip("German locale not available on this system")
        return ""  # unreachable, keeps type checker happy

    def test_locale_adds_month_names(self, german_locale: str) -> None:
        """LANG= with a valid locale adds localized month names."""
        parser = DateStringParser(directives=CalendarDirectives(lang=german_locale))
        german_months = {
            "januar",
            "februar",
            "märz",
            "april",
            "mai",
            "juni",
            "juli",
            "august",
            "september",
            "oktober",
            "november",
            "dezember",
        }
        found = german_months & set(parser.month_map)
        assert found, f"Expected German months in map, got: {sorted(parser.month_map)}"

    def test_english_still_works_with_locale(self, german_locale: str) -> None:
        """English month names remain available alongside locale names."""
        parser = DateStringParser(directives=CalendarDirectives(lang=german_locale))
        assert "january" in parser.month_map
        assert "jan" in parser.month_map

    def test_invalid_locale_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        """Invalid locale warns and falls back to English."""
        with caplog.at_level(logging.WARNING, logger="pylendar"):
            parser = DateStringParser(
                directives=CalendarDirectives(lang="xx_INVALID.UTF-8")
            )
        assert "locale not available" in caplog.text
        assert "january" in parser.month_map


# ---------------------------------------------------------------------------
# SEQUENCE= effect on DateStringParser
# ---------------------------------------------------------------------------


class TestSequenceDirective:
    """Tests for SEQUENCE= directive integration with DateStringParser."""

    @pytest.fixture
    def custom_parser(self) -> DateStringParser:
        """Parser with French-ish ordinals."""
        return DateStringParser(
            directives=CalendarDirectives(
                sequence=(
                    "premier",
                    "deuxieme",
                    "troisieme",
                    "quatrieme",
                    "cinquieme",
                    "dernier",
                )
            )
        )

    def test_custom_ordinals_in_mm_wkday_ord(
        self,
        custom_parser: DateStringParser,
    ) -> None:
        """Custom ordinal works in MM/WkdayOrdinal format."""
        expr = custom_parser.parse("10/MonPremier")
        assert expr is not None
        dates = expr.resolve(2026)
        assert datetime.date(2026, 10, 5) in dates

    def test_custom_ordinals_in_wkday_ord_month(
        self,
        custom_parser: DateStringParser,
    ) -> None:
        """Custom ordinal works in WkdayOrd Month format."""
        expr = custom_parser.parse("SunDernier Jun")
        assert expr is not None
        dates = expr.resolve(2026)
        assert datetime.date(2026, 6, 28) in dates

    def test_english_ordinals_still_work(self, custom_parser: DateStringParser) -> None:
        """English ordinals remain available alongside custom ones."""
        expr = custom_parser.parse("10/MonSecond")
        assert expr is not None

    def test_custom_ordinal_named_month(self, custom_parser: DateStringParser) -> None:
        """Custom ordinal works in Month/WkdayOrdinal format."""
        expr = custom_parser.parse("Oct/SatDeuxieme")
        assert expr is not None
        dates = expr.resolve(2026)
        assert datetime.date(2026, 10, 10) in dates


# ---------------------------------------------------------------------------
# Integration: both directives together (end-to-end via process_calendar)
# ---------------------------------------------------------------------------


class TestDirectivesE2E:
    """End-to-end tests with LANG= and SEQUENCE= in calendar files."""

    def test_sequence_e2e(self, run_calendar):
        """SEQUENCE= ordinal works end-to-end in MM/WkdayOrd format."""
        content = """\
SEQUENCE=premier deuxieme troisieme quatrieme cinquieme dernier
10/MonPremier\tFirst Monday of October
"""
        today = datetime.date(2026, 10, 5)
        result = run_calendar(content, today, ahead=0)
        assert result == ["Oct  5*\tFirst Monday of October"]

    def test_sequence_wkday_ord_month_e2e(self, run_calendar):
        """SEQUENCE= ordinal works end-to-end in WkdayOrd Month format."""
        content = """\
SEQUENCE=premier deuxieme troisieme quatrieme cinquieme dernier
SunDernier Jun\tLast Sunday of June
"""
        today = datetime.date(2026, 6, 28)
        result = run_calendar(content, today, ahead=0)
        assert result == ["Jun 28*\tLast Sunday of June"]

    def test_english_ordinals_with_sequence_e2e(self, run_calendar):
        """English ordinals still work when SEQUENCE= is active."""
        content = """\
SEQUENCE=premier deuxieme troisieme quatrieme cinquieme dernier
10/MonSecond\tSecond Monday of October
"""
        today = datetime.date(2026, 10, 12)
        result = run_calendar(content, today, ahead=0)
        assert result == ["Oct 12*\tSecond Monday of October"]

    def test_both_directives_e2e(self, run_calendar):
        """Both LANG= and SEQUENCE= work together in a calendar file."""
        content = """\
LANG=C
SEQUENCE=premier deuxieme troisieme quatrieme cinquieme dernier
10/MonPremier\tFirst Monday of October
Oct 12\tFixed date
"""
        today = datetime.date(2026, 10, 5)
        result = run_calendar(content, today, ahead=7)
        assert "Oct  5*\tFirst Monday of October" in result
        assert "Oct 12\tFixed date" in result
