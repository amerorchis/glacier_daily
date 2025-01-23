import sys
import os
import pytest
from datetime import datetime
import pytz
from unittest.mock import patch, MagicMock
import json
from requests.exceptions import RequestException

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from weather.night_sky import (
    Forecast,
    ForecastError,
    ForecastValidationError,
    ForecastFetchError,
    KpPeriod,
    DarkPeriod,
    aurora_forecast,
)

# Sample test data
SAMPLE_FORECAST_TEXT = """:Product: 3-Day Forecast
:Issued: 2025 Jan 10 1230 UTC
# Prepared by the U.S. Dept. of Commerce, NOAA, Space Weather Prediction Center
#
A. NOAA Geomagnetic Activity Observation and Forecast

The greatest observed 3 hr Kp over the past 24 hours was 4 (below NOAA
Scale levels).
The greatest expected 3 hr Kp for Jan 10-Jan 12 2025 is 3.67 (below NOAA
Scale levels).

NOAA Kp index breakdown Jan 10-Jan 12 2025

             Jan 10       Jan 11       Jan 12
00-03UT       1.33         2.33         1.67     
03-06UT       3.33         0.67         2.67     
06-09UT       1.67         1.33         1.33     
09-12UT       3.00         2.00         1.33     
12-15UT       1.33         1.67         2.67     
15-18UT       1.67         2.00         3.00     
18-21UT       1.67         3.33         3.67     
21-00UT       1.67         2.67         1.67     

Rationale: No G1 (Minor) or greater geomagnetic storms are expected.  No
significant transient or recurrent solar wind features are forecast.

B. NOAA Solar Radiation Activity Observation and Forecast

Solar radiation, as observed by NOAA GOES-18 over the past 24 hours, was
below S-scale storm level thresholds.

Solar Radiation Storm Forecast for Jan 10-Jan 12 2025

              Jan 10  Jan 11  Jan 12
S1 or greater   10%     10%     10%

Rationale: A slight chance for S1 (Minor) solar radiation storming will
persist through 12 Jan as Region 3947 continues to approach the west
limb.

C. NOAA Radio Blackout Activity and Forecast

No radio blackouts were observed over the past 24 hours.

Radio Blackout Forecast for Jan 10-Jan 12 2025

              Jan 10        Jan 11        Jan 12
R1-R2           45%           45%           40%
R3 or greater   10%           10%           10%

Rationale: There is a chance for R1-R2 (Minor-Moderate) radio blackouts,
with a slight chance for isolated R3 (Strong) or greater events through
12 Jan. This is largely based on the magnetic complexity and persistent
activity of Region 3947."""


@pytest.fixture
def sample_forecast():
    return Forecast(SAMPLE_FORECAST_TEXT)


def test_forecast_initialization(sample_forecast):
    """Test basic forecast initialization"""
    assert isinstance(sample_forecast, Forecast)
    assert len(sample_forecast.forecast_periods) == 24  # 8 periods per day * 3 days
    assert sample_forecast.issue_date.year == 2025
    assert sample_forecast.issue_date.month == 1
    assert sample_forecast.issue_date.day == 10


def test_forecast_validation_error():
    """Test that invalid forecast text raises ForecastValidationError"""
    with pytest.raises(ForecastValidationError):
        Forecast("Invalid forecast text")


@patch("requests.get")
def test_forecast_fetch_error(mock_get):
    """Test that network errors raise ForecastFetchError"""
    mock_get.side_effect = RequestException("Network error")
    with pytest.raises(ForecastFetchError):
        Forecast()


def test_get_aurora_strength():
    """Test aurora strength classification"""
    assert Forecast.get_aurora_strength(2.0) == "not visible"
    assert Forecast.get_aurora_strength(4.0) == "weakly visible"
    assert Forecast.get_aurora_strength(6.0) == "visible"

    with pytest.raises(ValueError):
        Forecast.get_aurora_strength(10.0)


def test_get_next_dark_period(sample_forecast):
    """Test dark period calculation"""
    test_time = datetime(2025, 1, 10, 12, 0, tzinfo=pytz.UTC)
    dark_period = sample_forecast.get_next_dark_period(
        latitude=48.528, longitude=-113.989, start_time=test_time
    )

    assert isinstance(dark_period, DarkPeriod)
    assert dark_period.start > test_time
    assert dark_period.end > dark_period.start


def test_get_forecast_by_location(sample_forecast):
    """Test location-based forecast retrieval"""
    test_time = datetime(2025, 1, 10, 12, 0, tzinfo=pytz.UTC)
    forecast = sample_forecast.get_forecast_by_location(
        latitude=48.528, longitude=-113.989, start_time=test_time
    )

    assert isinstance(forecast, dict)
    assert all(isinstance(k, datetime) for k in forecast.keys())
    assert all(isinstance(v, float) for v in forecast.values())


def test_kp_period_str():
    """Test KpPeriod string representation"""
    test_time = datetime(2024, 1, 10, 12, 0, tzinfo=pytz.UTC)
    period = KpPeriod(test_time, test_time, 3.0)
    assert str(period).startswith("2024-01-10 12:00")
    assert "Kp 3.0" in str(period)


def test_max_min_kp(sample_forecast):
    """Test maximum and minimum Kp value calculations"""
    assert isinstance(sample_forecast.max_kp, float)
    assert isinstance(sample_forecast.min_kp, float)
    assert sample_forecast.min_kp <= sample_forecast.max_kp


@pytest.mark.parametrize(
    "timezone",
    [
        "US/Mountain",
        "US/Pacific",
        "US/Eastern",
    ],
)
def test_get_forecast_different_timezones(sample_forecast, timezone):
    """Test forecast retrieval in different timezones"""
    forecast = sample_forecast.get_forecast(timezone=timezone)
    assert isinstance(forecast, dict)
    assert all(dt.tzinfo.zone == timezone for dt in forecast.keys())


def test_aurora_forecast():
    """Test aurora forecast function with mocked Forecast"""
    with patch("weather.night_sky.Forecast") as MockForecast:
        mock_instance = MockForecast.return_value
        mock_instance.get_forecast_by_location.return_value = {
            datetime(2025, 1, 10, 20, 0, tzinfo=pytz.UTC): 4.0
        }
        MockForecast.get_aurora_strength = Forecast.get_aurora_strength

        cast, msg = aurora_forecast(cloud_cover=0.2)
        assert isinstance(cast, str), "Forecast cast should be a string"
        assert isinstance(msg, str), "Forecast message should be a string"
        assert "Kp" in cast, "Forecast cast should contain Kp value"
        assert any(
            strength in cast
            for strength in ["not visible", "weakly visible", "visible"]
        ), "Forecast cast should contain visibility strength"
