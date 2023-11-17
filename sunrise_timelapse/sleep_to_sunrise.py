from datetime import datetime, date, timedelta, time
from astral import LocationInfo, sun
from zoneinfo import ZoneInfo
from time import sleep


def sunrise_timelapse_complete_time():
    # Create West Glacier LI object
    wg=LocationInfo(name='west glacier', region='MT', timezone='US/Mountain', latitude=48.4950, longitude=-113.9811)

    # Create West Glacier sun object
    s = sun.sun(wg.observer, date=date.today(), tzinfo=wg.timezone)

    now = datetime.now(tz=ZoneInfo('America/Denver'))

    now -= timedelta(hours=7)

    # Sunrise time minus now plus 50 minutes
    timelapse_ready_in = s[f"sunrise"] - now + timedelta(minutes=50)

    return timelapse_ready_in.total_seconds()


def sleep_time():

    timelapse_ready_in = sunrise_timelapse_complete_time()

    if timelapse_ready_in > 0:
        print(f'Waiting {round(timelapse_ready_in/60)} minutes for timelapse to finish.')
        sleep(timelapse_ready_in)

if __name__ == "__main__":
    sleep_time()
