from datetime import datetime, date, timedelta, time
from astral import LocationInfo, sun
from zoneinfo import ZoneInfo
from time import sleep

def sleep_time():

    # Create West Glacier LI object
    wg=LocationInfo(name='west glacier', region='MT', timezone='US/Mountain', latitude=48.4950, longitude=-113.9811)

    # Create West Glacier sun object
    s = sun.sun(wg.observer, date=date.today(), tzinfo=wg.timezone)

    # Sunrise time minus now plus 50 minutes
    sleep_time = s[f"sunrise"] - datetime.now(tz=ZoneInfo('America/Denver')) + timedelta(minutes=50)

    if sleep_time.total_seconds() > 0:
        print(f'Waiting {round(sleep_time.total_seconds()/60)} minutes for timelapse to finish.')
        sleep(sleep_time.total_seconds())

if __name__ == "__main__":
    sleep_time()
