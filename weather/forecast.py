"""
This module fetches weather forecasts for various locations in Glacier National Park using the Open-Meteo API.
"""

import requests_cache
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
from datetime import datetime
from math import floor
from typing import List, Tuple


def get_forecast() -> Tuple[List[Tuple[str, int, int, str]], str]:
    """
    Fetch weather forecasts for various locations in Glacier National Park.
    
    Returns:
        Tuple[List[Tuple[str, int, int, str]], str]: A tuple containing a list of forecast results and a string describing the daylight duration.
    """
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_strategy = Retry(total=5, backoff_factor=0.2)

    # Create an HTTPAdapter with the retry strategy
    retry_adapter = HTTPAdapter(max_retries=retry_strategy)

    # Mount the retry adapter to the cache session
    cache_session.mount("http://", retry_adapter)
    cache_session.mount("https://", retry_adapter)

    places = {
        'West Glacier': {'latitude':48.50228, 'longitude':-113.98202, 'altitude':3218},
        'Logan Pass': {'latitude':48.69567, 'longitude':-113.71656, 'altitude':6626},
        'St. Mary': {'latitude':48.74746, 'longitude':-113.43877, 'altitude':4500},
        'Two Medicine': {'latitude':48.48480, 'longitude':-113.36981, 'altitude':5174},
        'Many Glacier': {'latitude':48.79664, 'longitude':-113.65773, 'altitude':4895},
        'Polebridge': {'latitude':48.78348, 'longitude':-114.28056, 'altitude':3560}
    }

    latitude, longitude, elevation = [], [], []

    for i in places:
        latitude.append(places[i]['latitude'])
        longitude.append(places[i]['longitude'])
        elevation.append(places[i]['altitude'] / 3.281)


    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset", "daylight_duration"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": ["America/Denver"] * len(places),
        "forecast_days": 1,
        "elevation": elevation
    }

    responses = cache_session.get(url, params=params)
    forecasts = json.loads(responses.text)

    with open('weather/descriptions.json') as desc:
        code_convert = json.load(desc)

    results = []
    for place, forecast in zip(places, forecasts):
        forecast = forecast['daily']
        low = round(forecast['temperature_2m_min'][0])
        high = round(forecast['temperature_2m_max'][0])
        code = forecast['weather_code'][0]
        cond = code_convert[str(code)]['day']['description'].lower()
        results.append((place, high, low, cond))

    time_format = "%-I:%M%p"
    wg = forecasts[0]['daily']
    sunrise = datetime.fromisoformat(wg['sunrise'][0])
    sunrise = sunrise.strftime(time_format).lower()

    sunset = datetime.fromisoformat(wg['sunset'][0])
    sunset = sunset.strftime(time_format).lower()

    duration_hours = floor(wg['daylight_duration'][0] / (60 * 60))
    duration_minutes = floor((wg['daylight_duration'][0] - (duration_hours * 60 * 60)) / 60)

    length_str = f"Today, sunrise is at {sunrise} and sunset is at {sunset}. There will be {duration_hours} hours and {duration_minutes} minutes of daylight.\n"

    return results, length_str

if __name__ == "__main__":
    results, length_str = get_forecast()
    print(results, length_str)
