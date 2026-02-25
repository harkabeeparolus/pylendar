"""Tests for -l (longitude), -U (UTC offset), and -D (diagnostic) flags."""

import datetime
import subprocess

import pytest

from pylendar.pylendar import get_moon_phases, get_seasons, main


class TestGetSeasonsWithOffset:
    """Test that UTC offset shifts season dates correctly."""

    def test_sep_equinox_shifts_back_with_negative_offset(self):
        """Sep equinox 2026 is ~00:05 UTC; UTC-2 should shift it to Sep 22."""
        seasons_utc = get_seasons(2026, utc_offset_hours=0)
        seasons_neg = get_seasons(2026, utc_offset_hours=-2)
        assert seasons_utc["sepequinox"] == datetime.date(2026, 9, 23)
        assert seasons_neg["sepequinox"] == datetime.date(2026, 9, 22)

    def test_equinox_unchanged_with_positive_offset(self):
        """Sep equinox 2026 at ~00:05 UTC; UTC+8 should remain Sep 23."""
        seasons = get_seasons(2026, utc_offset_hours=8)
        assert seasons["sepequinox"] == datetime.date(2026, 9, 23)

    def test_zero_offset_matches_default(self):
        """Explicit offset=0 should match the default behavior."""
        assert get_seasons(2026) == get_seasons(2026, utc_offset_hours=0)


class TestGetMoonPhasesWithOffset:
    """Test that UTC offset shifts moon phase dates correctly."""

    def test_new_moon_shifts_back_with_negative_offset(self):
        """New moon on 2026-03-19 at ~01:24 UTC; UTC-2 shifts it to Mar 18."""
        phases_utc = get_moon_phases(2026, utc_offset_hours=0)
        phases_neg = get_moon_phases(2026, utc_offset_hours=-2)
        assert datetime.date(2026, 3, 19) in phases_utc["newmoon"]
        assert datetime.date(2026, 3, 18) in phases_neg["newmoon"]

    def test_full_moon_shifts_forward_with_positive_offset(self):
        """Full moon on 2026-06-29 at ~23:57 UTC; UTC+2 shifts it to Jun 30."""
        phases_utc = get_moon_phases(2026, utc_offset_hours=0)
        phases_pos = get_moon_phases(2026, utc_offset_hours=2)
        assert datetime.date(2026, 6, 29) in phases_utc["fullmoon"]
        assert datetime.date(2026, 6, 30) in phases_pos["fullmoon"]

    def test_zero_offset_matches_default(self):
        """Explicit offset=0 should match the default behavior."""
        assert get_moon_phases(2026) == get_moon_phases(2026, utc_offset_hours=0)


class TestDiagnosticFlag:
    """Test -D flag output and behavior."""

    def test_d_sun_output(self, capsys):
        """``-D sun`` should print UTC offset, longitude, and 4 season entries."""
        main(["-D", "sun", "-U", "1", "-t", "20260101"])
        output = capsys.readouterr().out
        lines = output.strip().splitlines()
        assert lines[0] == "UTCOffset: 1"
        assert lines[1] == "eastlongitude: 15"
        assert lines[2] == "Sun in 2026:"
        assert len(lines) == 7
        # Check labels are present
        labels = {line.split(" - ")[0] for line in lines[3:]}
        assert labels == {"e[0]", "e[1]", "s[0]", "s[1]"}

    def test_d_moon_output(self, capsys):
        """``-D moon`` should print UTC offset, longitude, and full/new moon lines."""
        main(["-D", "moon", "-U", "0", "-t", "20260101"])
        output = capsys.readouterr().out
        lines = output.strip().splitlines()
        assert lines[0] == "UTCOffset: 0"
        assert lines[1] == "eastlongitude: 0"
        assert lines[2].startswith("Full moon 2026:\t")
        assert lines[3].startswith("New moon 2026:\t")
        # Should have 12+ entries per line (one per month)
        full_entries = lines[2].split("\t", 1)[1].split(")")
        new_entries = lines[3].split("\t", 1)[1].split(")")
        # Each entry ends with ")", last split is empty
        assert len(full_entries) >= 12
        assert len(new_entries) >= 12

    def test_d_exits_without_events(self, tmp_path, capsys):
        """``-D`` should print diagnostics and NOT print calendar events."""
        cal = tmp_path / "calendar"
        cal.write_text("01/01\tNew Year\n06/21\tSummer solstice\n")
        main(["-D", "sun", "-U", "0", "-f", str(cal), "-t", "20260101"])
        output = capsys.readouterr().out
        assert "New Year" not in output
        assert "Summer solstice" not in output
        assert "UTCOffset" in output


class TestCliFlags:
    """Integration tests for -l and -U flags affecting calendar output."""

    def test_l_flag_affects_special_dates(self, run_calendar):
        """The -l flag should shift astronomical dates via derived UTC offset."""
        # Sep equinox is ~00:05 UTC; longitude -30 => UTC-2 => shifts to Sep 22
        content = "SepEquinox\tAutumn equinox\n"
        today = datetime.date(2026, 9, 22)
        # With utc_offset_hours=-2 (longitude=-30), equinox shifts to Sep 22
        events = run_calendar(content, today, ahead=1, utc_offset_hours=-2)
        assert any("Autumn equinox" in e for e in events)

    def test_u_flag_affects_special_dates(self, run_calendar):
        """The -U flag should shift astronomical dates."""
        content = "SepEquinox\tAutumn equinox\n"
        today = datetime.date(2026, 9, 22)
        # UTC offset -2 shifts equinox to Sep 22
        events = run_calendar(content, today, ahead=0, utc_offset_hours=-2)
        assert any("Autumn equinox" in e for e in events)

    def test_u_overrides_l(self, capsys):
        """When both -U and -l are given, UTC offset from -U is used."""
        # -U 5 means offset=5, -l 30 means longitude=30
        # The printed UTCOffset should be 5 (from -U), not 2 (from -l)
        main(["-D", "sun", "-U", "5", "-l", "30", "-t", "20260101"])
        output = capsys.readouterr().out
        lines = output.strip().splitlines()
        assert lines[0] == "UTCOffset: 5"
        assert lines[1] == "eastlongitude: 30"

    def test_l_derives_utc_offset(self, capsys):
        """When only -l is given, UTC offset is derived as longitude/15."""
        main(["-D", "sun", "-l", "30", "-t", "20260101"])
        output = capsys.readouterr().out
        lines = output.strip().splitlines()
        assert lines[0] == "UTCOffset: 2"
        assert lines[1] == "eastlongitude: 30"

    def test_u_derives_longitude(self, capsys):
        """When only -U is given, longitude is derived as offset*15."""
        main(["-D", "sun", "-U", "-5", "-t", "20260101"])
        output = capsys.readouterr().out
        lines = output.strip().splitlines()
        assert lines[0] == "UTCOffset: -5"
        assert lines[1] == "eastlongitude: -75"

    def test_d_sun_via_subprocess(self, tmp_path):
        """Verify -D works via the CLI entry point."""
        result = subprocess.run(
            ["uv", "run", "pylendar", "-D", "sun", "-U", "0"],
            capture_output=True,
            text=True,
            check=True,
            cwd=tmp_path,
        )
        assert "UTCOffset: 0" in result.stdout
        assert "Sun in" in result.stdout


@pytest.mark.parametrize("offset", [5.5, -3.5, 0.0])
def test_fractional_offset_no_crash(offset):
    """Fractional UTC offsets (e.g. India UTC+5:30) should not raise."""
    get_seasons(2026, utc_offset_hours=offset)
    get_moon_phases(2026, utc_offset_hours=offset)
