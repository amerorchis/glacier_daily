from unittest.mock import patch

import pytest

from shared.data_types import AlertBullet, WeatherResult
from weather.weather import AQI_CATEGORIES, _get_aqi, weather_data

# Mock return values
MOCK_FORECAST_RETURN = (
    [("Location1", 30, 75, "Partly cloudy")],
    "Forecast message",
)

MOCK_ALERTS_RETURN = [AlertBullet(headline="Weather alert test", bullets=["Detail"])]
MOCK_SEASON_RETURN = "summer"
MOCK_SUNSET_HUE_RETURN = (0.3, "Good", "Beautiful sunset expected")
MOCK_AURORA_RETURN = ("Good", "Aurora visible tonight")


@pytest.fixture
def mock_all_weather_services():
    """Fixture to mock all external weather service calls"""
    with (
        patch(
            "weather.weather.get_forecast", return_value=MOCK_FORECAST_RETURN
        ) as mock_forecast,
        patch("weather.weather._get_aqi", return_value=(45, "good.")) as mock_aqi,
        patch(
            "weather.weather.weather_alerts", return_value=MOCK_ALERTS_RETURN
        ) as mock_alerts,
        patch(
            "weather.weather.get_season", return_value=MOCK_SEASON_RETURN
        ) as mock_season,
        patch(
            "weather.weather.get_sunset_hue", return_value=MOCK_SUNSET_HUE_RETURN
        ) as mock_sunset,
        patch(
            "weather.weather.aurora_forecast", return_value=MOCK_AURORA_RETURN
        ) as mock_aurora,
    ):
        yield {
            "forecast": mock_forecast,
            "aqi": mock_aqi,
            "alerts": mock_alerts,
            "season": mock_season,
            "sunset": mock_sunset,
            "aurora": mock_aurora,
        }


def test_weather_data_returns_weather_result(mock_all_weather_services):
    """Test weather_data returns WeatherResult with correct fields"""
    result = weather_data()

    # Verify all services were called
    mock_all_weather_services["forecast"].assert_called_once()
    mock_all_weather_services["aqi"].assert_called_once()
    mock_all_weather_services["alerts"].assert_called_once()
    mock_all_weather_services["season"].assert_called_once()
    mock_all_weather_services["sunset"].assert_called_once()

    assert isinstance(result, WeatherResult)
    assert result.forecasts == MOCK_FORECAST_RETURN[0]
    assert result.daylight_message == MOCK_FORECAST_RETURN[1]
    assert result.season == MOCK_SEASON_RETURN
    assert result.aqi_value == 45
    assert result.aqi_category == "good."
    assert result.aurora_quality == "Good"
    assert result.aurora_message == "Aurora visible tonight"
    assert result.sunset_quality == "Good"
    assert result.sunset_message == "Beautiful sunset expected"
    assert result.cloud_cover_pct == 30
    assert result.alerts == MOCK_ALERTS_RETURN


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
    mock_all_weather_services["aqi"].return_value = (
        aqi_value,
        next(
            (cat for threshold, cat in AQI_CATEGORIES if aqi_value <= threshold),
            "unknown.",
        ),
    )
    result = weather_data()
    assert expected_category in result.aqi_category.lower()


def test_get_aqi_function():
    """Test the _get_aqi helper function directly"""
    with patch("weather.weather.get_air_quality", return_value=45):
        value, category = _get_aqi()
        assert value == 45
        assert "good" in category.lower()

    with patch("weather.weather.get_air_quality", return_value=-1):
        value, category = _get_aqi()
        assert value is None
        assert category == ""

    with patch("weather.weather.get_air_quality", return_value="invalid"):
        value, category = _get_aqi()
        assert value is None
        assert category == ""


def test_error_handling_in_weather_services(mock_all_weather_services):
    """Test handling of errors from weather services"""
    mock_all_weather_services["forecast"].side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc_info:
        weather_data()

    assert "API Error" in str(exc_info.value)


def test_empty_forecasts(mock_all_weather_services):
    """Test handling of empty/None forecasts"""
    mock_all_weather_services["forecast"].return_value = (None, "Forecast message")
    result = weather_data()
    assert result.forecasts == []
