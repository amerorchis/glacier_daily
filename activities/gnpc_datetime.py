"""
Convert date strings from Glacier National Park Conservancy format to a localized datetime object.
"""

import calendar
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from shared.datetime_utils import cross_platform_strftime


def convert_gnpc_datetimes(date_string: str):
    """
    Convert a date string from Glacier National Park Conservancy format to a localized datetime object.

    Args:
        date_string (str): The date string in the format 'Month Day, Year Hour:Minute'.

    Returns:
        datetime: A localized datetime object if the conversion is successful, otherwise the original date string.
    """
    if not isinstance(date_string, str):
        return date_string

    # Regular expression pattern to extract date and time components
    pattern = r"(?P<month>[A-Za-z]+) (?P<day>\d{1,2}), (?P<year>\d{4})\D*(?P<hour>\d{1,2}):(?P<minute>\d{2})"

    match = re.search(pattern, date_string)
    if match:
        try:
            # Extract components from the regex match
            month = match.group("month")
            day = int(match.group("day"))
            year = int(match.group("year"))
            hour = int(match.group("hour"))
            minute = int(match.group("minute"))

            # Handle 12-hour to 24-hour time conversion
            is_pm = "pm" in date_string.lower() or "p.m." in date_string.lower()
            is_am = "am" in date_string.lower() or "a.m." in date_string.lower()

            if is_am:
                if hour == 12:
                    hour = 0  # 12:00 AM is 00:00
            elif (is_pm or not is_am) and hour != 12:
                # Default to PM if neither specified (GNPC events are typically afternoon)
                hour += 12

            # Validate month
            month_num = datetime.strptime(month, "%B").month

            # Validate day for the specific month and year
            max_days = calendar.monthrange(year, month_num)[1]
            if day < 1 or day > max_days:
                return date_string

            # Create datetime object (this will raise ValueError if date/time is invalid)
            dt = datetime(year, month_num, day, hour, minute)

            # Return localized datetime
            return dt.replace(tzinfo=ZoneInfo("America/Denver"))

        except (ValueError, TypeError):
            # Return original string if any conversion fails
            return date_string

    return date_string


def datetime_to_string(dt_obj: datetime):
    """
    Convert a datetime object to a formatted string.

    Args:
        dt_obj (datetime): The datetime object to be formatted.

    Returns:
        str: The formatted date string.
    """
    if not isinstance(dt_obj, datetime):
        raise TypeError("Input must be a datetime object")

    try:
        formatted = cross_platform_strftime(
            dt_obj, "%A, %B %-d, %Y, %-I:%M %p %Z"
        ).lower()
        # Keep proper case for day/month names and uppercase timezone
        parts = formatted.split()
        if len(parts) >= 6:  # "monday, july 5, 2025, 1:30 pm mst"
            # Capitalize day and month
            parts[0] = parts[0].capitalize().rstrip(",") + ","  # "Monday,"
            parts[1] = parts[1].capitalize()  # "July"
            # Keep timezone uppercase
            if parts[-1].lower() in [
                "mst",
                "mdt",
                "pst",
                "pdt",
                "est",
                "edt",
                "cst",
                "cdt",
            ]:
                parts[-1] = parts[-1].upper()
        return " ".join(parts)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid datetime format: {e!s}") from e
