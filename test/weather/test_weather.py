import os
import sys
from unittest.mock import patch

import pytest

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )  # pragma: no cover

from weather.weather import WeatherContent, weather_data

# Mock return values
MOCK_FORECAST_RETURN = (
    [("Location1", 30, 75, "Partly cloudy")],  # Low  # High
    "Forecast message",
)

MOCK_AQI_RETURN = 45
MOCK_ALERTS_RETURN = "<p>Weather alert test</p>"
MOCK_SEASON_RETURN = "summer"
MOCK_SUNSET_HUE_RETURN = (0.3, "Good", "Beautiful sunset expected")
MOCK_AURORA_RETURN = ("Good", "Aurora visible tonight")


@pytest.fixture
def mock_all_weather_services():
    """Fixture to mock all external weather service calls"""
    with patch("weather.weather.get_forecast") as mock_forecast, patch(
        "weather.weather.get_air_quality"
    ) as mock_aqi, patch("weather.weather.weather_alerts") as mock_alerts, patch(
        "weather.weather.get_season"
    ) as mock_season, patch(
        "weather.weather.get_sunset_hue"
    ) as mock_sunset, patch(
        "weather.weather.aurora_forecast"
    ) as mock_aurora:

        # Set up mock returns
        mock_forecast.return_value = MOCK_FORECAST_RETURN
        mock_aqi.return_value = MOCK_AQI_RETURN
        mock_alerts.return_value = MOCK_ALERTS_RETURN
        mock_season.return_value = MOCK_SEASON_RETURN
        mock_sunset.return_value = MOCK_SUNSET_HUE_RETURN
        mock_aurora.return_value = MOCK_AURORA_RETURN

        yield {
            "forecast": mock_forecast,
            "aqi": mock_aqi,
            "alerts": mock_alerts,
            "season": mock_season,
            "sunset": mock_sunset,
            "aurora": mock_aurora,
        }


def test_weather_content_initialization(mock_all_weather_services):
    """Test WeatherContent initialization and data fetching"""
    weather = WeatherContent()

    # Verify all services were called
    mock_all_weather_services["forecast"].assert_called_once()
    mock_all_weather_services["aqi"].assert_called_once()
    mock_all_weather_services["alerts"].assert_called_once()
    mock_all_weather_services["season"].assert_called_once()
    mock_all_weather_services["sunset"].assert_called_once()

    # Verify data was properly stored
    assert weather.results == MOCK_FORECAST_RETURN[0]
    assert weather.season == MOCK_SEASON_RETURN
    assert "Forecasts Around the Park:" in weather.message1
    assert isinstance(weather.message2, str)


@pytest.mark.parametrize(
    "aqi_value,expected_category",
    [
        (30, "good"),
        (75, "moderate"),
        (125, "unhealthy for sensitive groups"),
        (175, "unhealthy"),
        (250, "very unhealthy"),
        (400, "hazardous"),
    ],
)
def test_aqi_categories(aqi_value, expected_category, mock_all_weather_services):
    """Test AQI categorization for different values"""
    mock_all_weather_services["aqi"].return_value = aqi_value
    weather = WeatherContent()
    assert expected_category in weather.message2.lower()


def test_invalid_aqi_handling(mock_all_weather_services):
    """Test handling of invalid AQI values"""
    # Test negative AQI
    mock_all_weather_services["aqi"].return_value = -1
    weather = WeatherContent()
    assert not any(
        cat[1] for cat in WeatherContent.AQI_CATEGORIES if cat[1] in weather.message2
    )

    # Test non-integer AQI
    mock_all_weather_services["aqi"].return_value = "invalid"
    weather = WeatherContent()
    assert not any(
        cat[1] for cat in WeatherContent.AQI_CATEGORIES if cat[1] in weather.message2
    )


def test_weather_data_factory():
    """Test the weather_data factory function"""
    with patch("weather.weather.WeatherContent") as MockWeatherContent:
        instance = MockWeatherContent.return_value
        result = weather_data()

        MockWeatherContent.assert_called_once()
        assert result == instance


def test_concurrent_execution(mock_all_weather_services):
    """Test that weather services are called concurrently"""
    import time

    def slow_forecast(*args, **kwargs):
        time.sleep(0.1)
        return MOCK_FORECAST_RETURN

    def slow_aqi(*args, **kwargs):
        time.sleep(0.1)
        return MOCK_AQI_RETURN

    # Replace mock returns with slow versions
    mock_all_weather_services["forecast"].side_effect = slow_forecast
    mock_all_weather_services["aqi"].side_effect = slow_aqi

    start_time = time.time()
    weather = WeatherContent()
    execution_time = time.time() - start_time

    # If executed concurrently, should take ~0.1 seconds
    # If sequential, would take ~0.2 seconds
    assert execution_time < 0.15  # Adding some buffer for test environment variations


def test_error_handling_in_weather_services(mock_all_weather_services):
    """Test handling of errors from weather services"""
    # Make forecast service raise an exception
    mock_all_weather_services["forecast"].side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc_info:
        weather = WeatherContent()

    assert "API Error" in str(exc_info.value)


# Additional test for HTML formatting
def test_html_formatting(mock_all_weather_services):
    """Test that output messages contain expected HTML formatting"""
    weather = WeatherContent()

    # Check message2 contains expected HTML elements
    assert '<p style="' in weather.message2
    assert "font-size:12px" in weather.message2
    assert "color:#333333" in weather.message2

    # Verify Aurora and Sunset quality information is properly formatted
    assert "Aurora:" in weather.message2
    assert "Sunset Color:" in weather.message2
    assert "Cloud Cover:" in weather.message2
