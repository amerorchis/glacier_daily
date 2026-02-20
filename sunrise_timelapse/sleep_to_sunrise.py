"""
Calculate when the sunrise timelapse will be finished and sleep until that time.
"""

from datetime import date, datetime, timedelta
from time import sleep
from zoneinfo import ZoneInfo

from astral import LocationInfo, sun

MAX_WAIT_SECONDS = 3 * 60 * 60  # 3 hours
SUNRISE_BUFFER_MINUTES = 52


def sunrise_timelapse_complete_time():
    """
    Calculate the sunrise time and add SUNRISE_BUFFER_MINUTES minutes.
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

    # Sunrise time minus now plus buffer for timelapse completion
    timelapse_ready_in = s["sunrise"] - now + timedelta(minutes=SUNRISE_BUFFER_MINUTES)

    return timelapse_ready_in.total_seconds()


def sleep_time():
    """
    Sleep the program until sunrise timelapse is complete.
    """

    timelapse_ready_in = sunrise_timelapse_complete_time()

    if timelapse_ready_in > MAX_WAIT_SECONDS:
        print(
            f"WARNING: Computed sleep time ({round(timelapse_ready_in / 60)} minutes) exceeds maximum wait of "
            f"{MAX_WAIT_SECONDS // 3600} hours. Skipping sleep."
        )
    elif timelapse_ready_in > 0:
        print(
            f"Waiting {round(timelapse_ready_in / 60)} minutes for timelapse to finish."
        )
        sleep(timelapse_ready_in)


if __name__ == "__main__":  # pragma: no cover
    sleep_time()
