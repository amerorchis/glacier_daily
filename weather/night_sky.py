import requests_cache
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
from datetime import datetime, timedelta
from typing import List, Dict

def judge_cover(cloud: int) -> str:
    """
    Determines the cloud cover description based on the cloud cover percentage.

    Args:
        cloud (int): The cloud cover percentage.

    Returns:
        str: A description of the cloud cover.
    """
    if cloud == 0:
        return "no"
    elif cloud <= 25:
        return "low"
    elif cloud <= 75:
        return "medium"
    else:
        return "high"

def clear_night(aur_start: datetime, aur_end: datetime) -> str:
    """
    Determines the clear night sky forecast for aurora viewing.

    Args:
        aur_start (datetime): The start time for aurora viewing.
        aur_end (datetime): The end time for aurora viewing.

    Returns:
        str: A formatted HTML string describing the clear night sky forecast, or an empty string if the forecast is not favorable.
    """
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_strategy = Retry(total=5, backoff_factor=0.2)

    # Create an HTTPAdapter with the retry strategy
    retry_adapter = HTTPAdapter(max_retries=retry_strategy)

    # Mount the retry adapter to the cache session
    cache_session.mount("http://", retry_adapter)
    cache_session.mount("https://", retry_adapter)
    url = "https://api.open-meteo.com/v1/forecast?latitude=48.50228&longitude=-113.98202&hourly=cloud_cover&daily=sunrise,sunset&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=America%2FDenver&forecast_days=2&elevation=980.8464"

    response = cache_session.get(url)
    forecast = json.loads(response.text)

    sunset = datetime.fromisoformat(forecast['daily']['sunset'][0])
    sunrise = datetime.fromisoformat(forecast['daily']['sunrise'][1])
    start = max(aur_start, sunset)
    end = min(aur_end, sunrise)

    hourly = forecast['hourly']
    hours = hourly['time']
    clouds = hourly['cloud_cover']

    dark: List[Dict[str, any]] = []
    for hour, cloud in zip(hours, clouds):
        time = datetime.fromisoformat(hour)

        if start < time < end:
            cover = judge_cover(cloud)
            dark.append({
                'time': time,
                'num': cloud,
                'desc': cover
            })

    clear = [i for i in dark if i['num'] == 0]
    str = ''

    if dark:
        if clear:
            start = clear[0]['time']
            end = clear[0]['time']
            for item in clear:
                curr = item['time']
                diff = curr - end

                if diff > timedelta(hours=1):
                    break
                else:
                    end = item['time']

            start = start.strftime("%-I%p").lower()
            end = end.strftime("%-I%p").lower()
            str = f"and the skies will be clear from {start} to {end}! <strong>It's a great night to see the northern lights!</strong>"

        else:
            clearest = min(dark, key=lambda x: x['num'])
            conj = 'and' if clearest['desc'] == 'low' else 'but'
            str = f'{conj} there will be {clearest["desc"]} cloud cover.'

    return str

def aurora_forecast() -> str:
    """
    Fetches the aurora forecast and determines the best time for viewing based on cloud cover.

    Returns:
        str: A formatted HTML string describing the aurora forecast, or an empty string if the forecast is not favorable.
    """
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_strategy = Retry(total=5, backoff_factor=0.2)

    # Create an HTTPAdapter with the retry strategy
    retry_adapter = HTTPAdapter(max_retries=retry_strategy)

    # Mount the retry adapter to the cache session
    cache_session.mount("http://", retry_adapter)
    cache_session.mount("https://", retry_adapter)
    url = "https://services.swpc.noaa.gov/text/3-day-forecast.txt"
    response = cache_session.get(url)
    forecast = response.text

    forecast = forecast.split('NOAA Kp index breakdown')[1]
    forecast = forecast.split('Rationale')[0].strip()
    forecast = forecast.split('\n')[3:]

    forecast = [i.split() for i in forecast]

    current_date = datetime.now().date()
    two_pm = datetime(current_date.year, current_date.month, current_date.day, 14, 0, 0)  # 2:00 PM
    five_pm = datetime(current_date.year, current_date.month, current_date.day, 17, 0, 0)  # 5:00 PM
    eight_pm = datetime(current_date.year, current_date.month, current_date.day, 20, 0, 0)  # 8:00 PM
    eleven_pm = datetime(current_date.year, current_date.month, current_date.day, 23, 0, 0)  # 11:00 PM
    two_am = datetime(current_date.year, current_date.month, current_date.day, 2, 0, 0) + timedelta(days=1)  # 2:00 AM
    five_am = datetime(current_date.year, current_date.month, current_date.day, 5, 0, 0) + timedelta(days=1)  # 5:00 AM

    times = [five_pm, eight_pm, eleven_pm, two_am, five_am]
    kp = []
    kp.append([two_pm, float(forecast[-1][1])])
    for i in range(5):
        kp.append([times[i], float(forecast[i][1])])

    # Test parameters:
    # kp[1][1] = 5.2
    # kp[4][1] = 4.1

    kp = [i for i in kp if i[1] >= 4]

    if kp:
        start = min(kp, key=lambda x: x[0])[0]
        end = max(kp, key=lambda x: x[0])[0]
        max_kp = max(kp, key=lambda x: x[1])[1]
        max_kp = f'<strong>{max_kp}</strong>' if max_kp > 5.5 else max_kp

        skies = clear_night(start, end)

        if skies:
            return f'<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">The aurora is forecasted for tonight with a max KP of {max_kp} {skies}</p>'

    return ''

if __name__ == "__main__":
    print(aurora_forecast())
