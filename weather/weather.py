"""
This module fetches and processes various weather-related data including forecasts, air quality index (AQI), weather alerts, aurora forecasts, seasonal information, and sunset hues.
"""

import concurrent.futures
import os
from typing import List, Optional, Tuple

from weather.forecast import get_forecast
from weather.night_sky import aurora_forecast
from weather.season import get_season
from weather.sunset_hue import get_sunset_hue
from weather.weather_alerts import weather_alerts
from weather.weather_aqi import get_air_quality


class WeatherContent:
    """
    Object for all of the data related to the weather forecast.
    """

    AQI_CATEGORIES: List[Tuple[int, str]] = [
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

    def __init__(self):
        """
        Initialize WeatherContent instance and fetch weather data.
        """
        self.results: Optional[List[Tuple[str, int, int, str]]] = None
        self.message1: str = ""
        self.message2: str = ""
        self.season: Optional[str] = None
        self._fetch_weather_data()
        self.message1 += "<br><br>Forecasts Around the Park:"

    def _fetch_weather_data(self) -> None:
        """
        Concurrently fetch various weather-related data using ThreadPoolExecutor.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Create a dictionary to store futures for cleaner management
            futures = {
                "forecast": executor.submit(get_forecast),
                "aqi": executor.submit(self._get_aqi),
                "alerts": executor.submit(weather_alerts),
                "season": executor.submit(get_season),
                "sunset_hue": executor.submit(get_sunset_hue),
            }

            # Retrieve results
            self.results, self.message1 = futures["forecast"].result()
            self.message2 = futures["aqi"].result()
            self.season = futures["season"].result()
            cloud_cover, sunset_quality, sunset_message = futures["sunset_hue"].result()
            aurora_quality, aurora_message = aurora_forecast(cloud_cover)

            color_quality = (
                f'<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">Evening Viewing Forecasts:<br>'
                f"Aurora: {aurora_quality} | "
                f"Sunset Color: {sunset_quality} | "
                f"Cloud Cover: {round(cloud_cover * 100)}%"
                "</p>"
            )

            message = (
                '<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">'
                + " ".join(filter(bool, [aurora_message, sunset_message]))
                + "</p>"
            )
            # Append additional weather information
            additional_info = [color_quality, message, futures["alerts"].result()]

            # Add non-empty additional information to message2
            self.message2 += "".join(filter(bool, additional_info))

    def _get_aqi(self) -> str:
        """
        Retrieve and format Air Quality Index (AQI) information.

        Returns:
            str: Formatted AQI information or empty string if invalid.
        """
        aqi_num = get_air_quality()

        if not isinstance(aqi_num, int) or aqi_num < 0:
            return ""

        # Find the appropriate AQI category
        quality = next(
            (cat for threshold, cat in self.AQI_CATEGORIES if aqi_num <= threshold),
            "unknown.",
        )

        return (
            f'<p style="margin:0 0 12px; font-size:12px; '
            f'line-height:18px; color:#333333;">'
            f"The current AQI in West Glacier is {aqi_num}. "
            f"This air quality is considered {quality}</p>"
        )


def weather_data() -> WeatherContent:
    """
    Create and return a WeatherContent instance.

    Returns:
        WeatherContent: Instance with fetched weather data.
    """
    return WeatherContent()


if __name__ == "__main__":  # pragma: no cover
    from dotenv import load_dotenv

    load_dotenv("email.env")
    print(weather_data().message2)
