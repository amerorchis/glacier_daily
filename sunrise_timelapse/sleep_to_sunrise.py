"""
Calculate when the sunrise timelapse will be finished and sleep until that time.
"""

from datetime import datetime, date, timedelta
from time import sleep
from zoneinfo import ZoneInfo
from astral import LocationInfo, sun


def sunrise_timelapse_complete_time():
    """
    Calculate the sunrise time and add 50 minutes.
    """
    # Create West Glacier LI object
    wg = LocationInfo(
        name="west glacier",
        region="MT",
        timezone="US/Mountain",
        latitude=48.4950,
        longitude=-113.9811,
    )

    # Create West Glacier sun object
    s = sun.sun(wg.observer, date=date.today(), tzinfo=wg.timezone)

    now = datetime.now(tz=ZoneInfo("America/Denver"))

    # Sunrise time minus now plus 52 minutes
    timelapse_ready_in = s["sunrise"] - now + timedelta(minutes=52)

    return timelapse_ready_in.total_seconds()


def sleep_time():
    """
    Sleep the program until sunrise timelapse is complete.
    """

    timelapse_ready_in = sunrise_timelapse_complete_time()

    if timelapse_ready_in > 0:
        print(
            f"Waiting {round(timelapse_ready_in/60)} minutes for timelapse to finish."
        )
        sleep(timelapse_ready_in)


if __name__ == "__main__":  # pragma: no cover
    sleep_time()
