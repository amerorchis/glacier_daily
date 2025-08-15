"""
Unit tests for shared.datetime_utils module.

Tests cross-platform datetime formatting functions to ensure they work
correctly on both Unix and Windows platforms.
"""

import platform
from datetime import datetime
from unittest.mock import patch

import pytest
import pytz

from shared.datetime_utils import (
    cross_platform_strftime,
    format_date_readable,
    format_short_date,
    format_time_12hr,
    format_time_with_timezone,
)


class TestCrossPlatformStrftime:
    """Test the cross_platform_strftime function."""

    def test_unix_platform_uses_native_strftime(self):
        """Test that Unix platforms use native strftime with %-modifiers."""
        dt = datetime(2025, 1, 5, 13, 30, 0)

        with patch("shared.datetime_utils.platform.system", return_value="Linux"):
            result = cross_platform_strftime(dt, "%B %-d, %Y")
            # On Unix, should use native strftime
            assert result == "January 5, 2025"

    def test_windows_platform_removes_leading_zeros(self):
        """Test that Windows platform properly removes leading zeros."""
        dt = datetime(2025, 1, 5, 13, 30, 0)

        with patch("shared.datetime_utils.platform.system", return_value="Windows"):
            # Test day without leading zero
            result = cross_platform_strftime(dt, "%B %-d, %Y")
            assert result == "January 5, 2025"

            # Test hour without leading zero
            result = cross_platform_strftime(dt, "%-I:%M %p")
            assert result == "1:30 PM"

            # Test month without leading zero
            result = cross_platform_strftime(dt, "%-m/%-d/%-y")
            assert result == "1/5/25"

    def test_windows_edge_cases(self):
        """Test Windows platform with edge cases like day 10 (double digit)."""
        dt = datetime(2025, 12, 15, 2, 5, 0)

        with patch("shared.datetime_utils.platform.system", return_value="Windows"):
            # Test with double-digit day (should not remove zeros)
            result = cross_platform_strftime(dt, "%B %-d, %Y")
            assert result == "December 15, 2025"

            # Test with single-digit hour
            result = cross_platform_strftime(dt, "%-I:%M %p")
            assert result == "2:05 AM"

            # Test with double-digit month
            result = cross_platform_strftime(dt, "%-m/%-d/%-y")
            assert result == "12/15/25"

    def test_no_minus_modifiers(self):
        """Test format strings without %-modifiers work on both platforms."""
        dt = datetime(2025, 1, 5, 13, 30, 0)

        # Test with Unix
        with patch("shared.datetime_utils.platform.system", return_value="Linux"):
            result = cross_platform_strftime(dt, "%Y-%m-%d")
            assert result == "2025-01-05"

        # Test with Windows
        with patch("shared.datetime_utils.platform.system", return_value="Windows"):
            result = cross_platform_strftime(dt, "%Y-%m-%d")
            assert result == "2025-01-05"

    def test_complex_format_string(self):
        """Test complex format strings with multiple %-modifiers."""
        dt = datetime(2025, 1, 5, 9, 5, 0)

        with patch("shared.datetime_utils.platform.system", return_value="Windows"):
            result = cross_platform_strftime(dt, "%A, %B %-d, %Y at %-I:%M %p")
            assert result == "Sunday, January 5, 2025 at 9:05 AM"


class TestFormatTime12hr:
    """Test the format_time_12hr function."""

    def test_morning_time(self):
        """Test morning time formatting."""
        dt = datetime(2025, 1, 5, 9, 30, 0)
        result = format_time_12hr(dt)
        assert result == "9:30 am"

    def test_afternoon_time(self):
        """Test afternoon time formatting."""
        dt = datetime(2025, 1, 5, 15, 45, 0)
        result = format_time_12hr(dt)
        assert result == "3:45 pm"

    def test_midnight(self):
        """Test midnight formatting."""
        dt = datetime(2025, 1, 5, 0, 0, 0)
        result = format_time_12hr(dt)
        assert result == "12:00 am"

    def test_noon(self):
        """Test noon formatting."""
        dt = datetime(2025, 1, 5, 12, 0, 0)
        result = format_time_12hr(dt)
        assert result == "12:00 pm"

    def test_single_digit_hour(self):
        """Test single digit hour (no leading zero)."""
        dt = datetime(2025, 1, 5, 1, 5, 0)
        result = format_time_12hr(dt)
        assert result == "1:05 am"


class TestFormatDateReadable:
    """Test the format_date_readable function."""

    def test_single_digit_day(self):
        """Test single digit day formatting."""
        dt = datetime(2025, 1, 5, 12, 0, 0)
        result = format_date_readable(dt)
        assert result == "January 5, 2025"

    def test_double_digit_day(self):
        """Test double digit day formatting."""
        dt = datetime(2025, 12, 25, 12, 0, 0)
        result = format_date_readable(dt)
        assert result == "December 25, 2025"


class TestFormatShortDate:
    """Test the format_short_date function."""

    def test_single_digit_month_day(self):
        """Test single digit month and day."""
        dt = datetime(2025, 1, 5, 12, 0, 0)
        result = format_short_date(dt)
        assert result == "1/5/25"

    def test_double_digit_month_day(self):
        """Test double digit month and day."""
        dt = datetime(2025, 12, 25, 12, 0, 0)
        result = format_short_date(dt)
        assert result == "12/25/25"


class TestFormatTimeWithTimezone:
    """Test the format_time_with_timezone function."""

    def test_timezone_formatting(self):
        """Test time with timezone formatting."""
        dt = pytz.timezone("America/Denver").localize(datetime(2025, 1, 5, 13, 30, 0))
        result = format_time_with_timezone(dt)
        assert result == "1:30 pm mst"

    def test_timezone_formatting_summer(self):
        """Test time with timezone formatting in summer (MDT)."""
        dt = pytz.timezone("America/Denver").localize(datetime(2025, 7, 15, 13, 30, 0))
        result = format_time_with_timezone(dt)
        assert result == "1:30 pm mdt"

    def test_utc_timezone(self):
        """Test UTC timezone formatting."""
        dt = pytz.UTC.localize(datetime(2025, 1, 5, 20, 30, 0))
        result = format_time_with_timezone(dt)
        assert result == "8:30 pm utc"


class TestWindowsSpecificBehavior:
    """Test Windows-specific datetime formatting behavior."""

    @patch("shared.datetime_utils.platform.system", return_value="Windows")
    def test_windows_leading_zero_removal(self, mock_system):
        """Test that leading zeros are properly removed on Windows."""
        dt = datetime(2025, 1, 5, 1, 5, 0)

        # Test various %-modifiers
        test_cases = [
            ("%-d", "5"),  # day
            ("%-I", "1"),  # hour (12-hour)
            ("%-m", "1"),  # month
            ("%-y", "25"),  # year without century
        ]

        for format_str, expected in test_cases:
            result = cross_platform_strftime(dt, format_str)
            assert result == expected, f"Failed for format {format_str}"

    @patch("shared.datetime_utils.platform.system", return_value="Windows")
    def test_windows_no_leading_zero_needed(self, mock_system):
        """Test Windows behavior when no leading zero removal is needed."""
        dt = datetime(2025, 12, 15, 11, 45, 0)

        # Test cases where values are already double-digit
        test_cases = [
            ("%-d", "15"),  # day
            ("%-I", "11"),  # hour (12-hour)
            ("%-m", "12"),  # month
        ]

        for format_str, expected in test_cases:
            result = cross_platform_strftime(dt, format_str)
            assert result == expected, f"Failed for format {format_str}"

    @patch("shared.datetime_utils.platform.system", return_value="Windows")
    def test_windows_zero_values(self, mock_system):
        """Test Windows behavior with values that would become empty after lstrip('0')."""
        # This is an edge case where stripping all zeros would leave empty string
        # Our function should handle this by returning '0'
        dt = datetime(2025, 1, 1, 0, 0, 0)  # midnight on January 1st

        # Test midnight hour (should be 12 in 12-hour format, so not an issue)
        result = cross_platform_strftime(dt, "%-I:%M %p")
        assert result == "12:00 AM"


class TestRealWorldUseCases:
    """Test real-world use cases from the codebase."""

    def test_gnpc_datetime_format(self):
        """Test the format used in gnpc_datetime module."""
        dt = pytz.timezone("America/Denver").localize(datetime(2025, 1, 5, 13, 30, 0))
        result = (
            cross_platform_strftime(dt, "%A, %B %-d, %Y, %-I:%M%p %Z")
            .lower()
            .replace("mst", "MST")
        )
        assert "sunday, january 5, 2025, 1:30pm MST" == result

    def test_weather_time_format(self):
        """Test the format used in weather modules."""
        dt = datetime(2025, 1, 5, 6, 15, 0)
        result = cross_platform_strftime(dt, "%-I:%M %p").lower()
        assert result == "6:15 am"

    def test_web_version_timestring(self):
        """Test the format used in web_version module."""
        dt = datetime(2025, 1, 5, 14, 30, 0)
        date_part = format_short_date(dt)
        time_part = format_time_12hr(dt)
        result = f"{date_part} at {time_part} MT"
        assert result == "1/5/25 at 2:30 pm MT"


if __name__ == "__main__":
    pytest.main([__file__])
