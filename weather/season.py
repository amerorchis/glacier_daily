"""
This module determines the season based on a given or current date.
Seasons are defined as:
    - Winter: December 1 - March 31
    - Spring: April 1 - June 30
    - Summer: July 1 - September 30
    - Fall: October 1 - November 30
Note: this is to figure out which template theme to use and so it goes
by the vibe in GNP, not the actual season dates.
"""

from datetime import datetime

from shared.datetime_utils import now_mountain


def get_season(date: datetime | None = None) -> str:
    """
    Determine the season based on the given date or current date.

    Args:
        date (datetime, optional): The date to check. Defaults to current date.

    Returns:
        str: The season ('winter', 'spring', 'summer', or 'fall')

    """
    if not date:
        date = now_mountain()

    month = date.month

    if month in [12, 1, 2, 3]:
        return "winter"
    elif month in [4, 5, 6]:
        return "spring"
    elif month in [7, 8, 9]:
        return "summer"
    else:  # months 10, 11
        return "fall"


if __name__ == "__main__":  # pragma: no cover
    print(get_season())
