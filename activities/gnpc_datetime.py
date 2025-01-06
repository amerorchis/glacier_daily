"""
This module provides functions to convert and format datetime strings specific to Glacier National Park events.
"""

import re
from datetime import datetime
import pytz

def convert_gnpc_datetimes(date_string: str):
    """
    Convert a date string from Glacier National Park Conservancy format to a localized datetime object.

    Args:
        date_string (str): The date string in the format 'Month Day, Year Hour:Minute'.

    Returns:
        datetime: A localized datetime object if the conversion is successful, otherwise the original date string.
    """
    # Regular expression pattern to extract date and time components
    pattern = r'(?P<month>[A-Za-z]+) (?P<day>\d{1,2}), (?P<year>\d{4})\D*(?P<hour>\d{1,2}):(?P<minute>\d{2})'

    match = re.search(pattern, date_string)
    if match:
        # Extract components from the regex match
        month = match.group('month')
        day = int(match.group('day'))
        year = int(match.group('year'))
        hour = int(match.group('hour')) + 12  # events always in evening
        minute = int(match.group('minute'))

        # Create a datetime object
        return pytz.timezone('America/Denver').localize(datetime(year, datetime.strptime(month, '%B').month, day, hour, minute))

    return date_string

def datetime_to_string(dt_obj: datetime):
    """
    Convert a datetime object to a formatted string.

    Args:
        dt_obj (datetime): The datetime object to be formatted.

    Returns:
        str: The formatted date string.
    """
    return dt_obj.strftime("%A, %B %d, %Y, %-I:%M%p %Z")