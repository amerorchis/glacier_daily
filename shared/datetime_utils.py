"""Cross-platform datetime formatting utilities.

Windows strftime doesn't support the %-modifier for removing leading zeros.
This module provides cross-platform compatible datetime formatting.
"""

import platform
from datetime import datetime
from typing import Union


def cross_platform_strftime(dt: datetime, format_string: str) -> str:
    """Format datetime with cross-platform compatibility.

    Handles the %-modifier which isn't supported on Windows.

    Args:
        dt: datetime object to format
        format_string: strftime format string (may contain %-modifiers)

    Returns:
        Formatted datetime string
    """
    if platform.system() == "Windows":
        # Replace %-modifiers with placeholders, format, then replace placeholders
        result = format_string

        # Map of %-modifiers to their zero-padded equivalents and placeholders
        replacements = {
            "%-d": "%d",  # day
            "%-I": "%I",  # hour (12-hour)
            "%-H": "%H",  # hour (24-hour)
            "%-m": "%m",  # month
            "%-y": "%y",  # year without century
            "%-j": "%j",  # day of year
            "%-U": "%U",  # week number (Sunday start)
            "%-W": "%W",  # week number (Monday start)
        }

        # Create unique placeholders and store what they should be replaced with
        placeholder_map = {}
        for unix_format, windows_format in replacements.items():
            if unix_format in format_string:
                placeholder = f"__PLACEHOLDER_{len(placeholder_map)}__"
                result = result.replace(unix_format, placeholder)
                # Get the actual value and strip leading zeros
                formatted_value = dt.strftime(windows_format).lstrip("0") or "0"
                placeholder_map[placeholder] = formatted_value

        # Format the string with remaining strftime codes
        formatted = dt.strftime(result)

        # Replace placeholders with the zero-stripped values
        for placeholder, value in placeholder_map.items():
            formatted = formatted.replace(placeholder, value)

        return formatted
    else:
        # Unix systems support %-modifier natively
        return dt.strftime(format_string)


def format_time_12hr(dt: datetime) -> str:
    """Format time in 12-hour format without leading zeros (cross-platform).

    Returns: "1:30 pm" instead of "01:30 PM"
    """
    return cross_platform_strftime(dt, "%-I:%M %p").lower()


def format_date_readable(dt: datetime) -> str:
    """Format date in readable format without leading zeros (cross-platform).

    Returns: "January 5, 2025" instead of "January 05, 2025"
    """
    return cross_platform_strftime(dt, "%B %-d, %Y")


def format_short_date(dt: datetime) -> str:
    """Format date in short format without leading zeros (cross-platform).

    Returns: "1/5/25" instead of "01/05/25"
    """
    return cross_platform_strftime(dt, "%-m/%-d/%-y")


def format_time_with_timezone(dt: datetime) -> str:
    """Format time with timezone in standardized format (cross-platform).

    Returns: "1:30 pm MST" (lowercase am/pm, uppercase timezone)
    """
    formatted = cross_platform_strftime(dt, "%-I:%M %p %Z")
    # Split to lowercase only the AM/PM part, keep timezone uppercase
    parts = formatted.rsplit(" ", 1)  # Split from right: ['1:30 PM', 'MST']
    if len(parts) == 2:
        time_part, tz_part = parts
        time_part = time_part.lower()  # "1:30 pm"
        return f"{time_part} {tz_part}"  # "1:30 pm MST"
    return formatted.lower()  # Fallback if no timezone
