"""
This module fetches and processes various weather-related data including forecasts, air quality index (AQI),
weather alerts, aurora forecasts, seasonal information, and sunset hues.
"""

import concurrent.futures

from shared.data_types import WeatherResult
from weather.forecast import get_forecast
from weather.night_sky import aurora_forecast
from weather.season import get_season
from weather.sunset_hue import get_sunset_hue
from weather.weather_alerts import weather_alerts
from weather.weather_aqi import get_air_quality

AQI_CATEGORIES: list[tuple[int, str]] = [
    (50, "good."),
    (100, "moderate."),
    (
        150,
        "unhealthy for sensitive groups. Children, older adults, active people, and people with heart or lung disease (such as asthma) should reduce prolonged or heavy exertion outdoors.",
    ),
    (
        200,
        "unhealthy. Children, older adults, active people, and people with heart or lung disease (such as asthma) should avoid prolonged or heavy exertion outdoors. Everyone else should reduce prolonged or heavy exertion outdoors.",
    ),
    (
        300,
        "very unhealthy. Children, older adults, active people, and people with heart or lung disease (such as asthma) should avoid all outdoor exertion. Everyone else should avoid prolonged or heavy exertion outdoors.",
    ),
    (500, "hazardous. Everyone should avoid all physical activity outdoors."),
]


def _get_aqi() -> tuple[int | None, str]:
    """
    Retrieve Air Quality Index (AQI) value and category.

    Returns:
        tuple: (aqi_value, aqi_category) where aqi_value is int or None,
               and aqi_category is the descriptive string.
    """
    aqi_num = get_air_quality()

    if not isinstance(aqi_num, int) or aqi_num < 0:
        return None, ""

    # Find the appropriate AQI category
    quality = next(
        (cat for threshold, cat in AQI_CATEGORIES if aqi_num <= threshold),
        "unknown.",
    )

    return aqi_num, quality


def weather_data() -> WeatherResult:
    """
    Fetch all weather-related data concurrently and return structured result.

    Returns:
        WeatherResult: Structured weather data.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            "forecast": executor.submit(get_forecast),
            "aqi": executor.submit(_get_aqi),
            "alerts": executor.submit(weather_alerts),
            "season": executor.submit(get_season),
            "sunset_hue": executor.submit(get_sunset_hue),
        }

        forecasts, daylight_message = futures["forecast"].result()
        aqi_value, aqi_category = futures["aqi"].result()
        alerts = futures["alerts"].result()
        season = futures["season"].result()
        cloud_cover, sunset_quality, sunset_message = futures["sunset_hue"].result()
        aurora_quality, aurora_message = aurora_forecast(cloud_cover)

    return WeatherResult(
        daylight_message=daylight_message,
        forecasts=forecasts if forecasts else [],
        season=season,
        aqi_value=aqi_value,
        aqi_category=aqi_category,
        aurora_quality=aurora_quality,
        aurora_message=aurora_message,
        sunset_quality=sunset_quality,
        sunset_message=sunset_message,
        cloud_cover_pct=round(cloud_cover * 100),
        alerts=alerts,
    )


if __name__ == "__main__":  # pragma: no cover
    result = weather_data()
    print(f"Daylight: {result.daylight_message}")
    print(f"AQI: {result.aqi_value} ({result.aqi_category})")
    print(f"Aurora: {result.aurora_quality}")
    print(f"Alerts: {len(result.alerts)}")
