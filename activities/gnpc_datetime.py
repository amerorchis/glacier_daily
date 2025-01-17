import re
from datetime import datetime
import pytz
import calendar

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
    pattern = r'(?P<month>[A-Za-z]+) (?P<day>\d{1,2}), (?P<year>\d{4})\D*(?P<hour>\d{1,2}):(?P<minute>\d{2})'

    match = re.search(pattern, date_string)
    if match:
        try:
            # Extract components from the regex match
            month = match.group('month')
            day = int(match.group('day'))
            year = int(match.group('year'))
            hour = int(match.group('hour'))
            minute = int(match.group('minute'))

            # Handle 12-hour time conversion
            if hour == 12:
                hour = 12  # 12:00 stays as 12:00
            else:
                hour = hour + 12  # Other hours add 12 for PM

            # Validate month
            month_num = datetime.strptime(month, '%B').month

            # Validate day for the specific month and year
            max_days = calendar.monthrange(year, month_num)[1]
            if day < 1 or day > max_days:
                return date_string

            # Create datetime object (this will raise ValueError if date/time is invalid)
            dt = datetime(year, month_num, day, hour, minute)
            
            # Return localized datetime
            return pytz.timezone('America/Denver').localize(dt)

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
        return dt_obj.strftime("%A, %B %-d, %Y, %-I:%M%p %Z")
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid datetime format: {str(e)}")
