import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytz
from requests.exceptions import RequestException

from weather.night_sky import (
    DarkPeriod,
    Forecast,
    ForecastError,
    ForecastFetchError,
    ForecastValidationError,
    KpPeriod,
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
        latitude=48.528,
        longitude=-113.989,
        start_time=test_time,
        timezone="US/Mountain",
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

        # Mock the dark period (e.g., 8pm to 6am next day in Mountain time)
        tz = pytz.timezone("US/Mountain")
        dark_start = tz.localize(datetime(2025, 1, 10, 20, 0))  # 8pm
        dark_end = tz.localize(datetime(2025, 1, 11, 6, 0))  # 6am next day
        mock_instance.get_next_dark_period.return_value = DarkPeriod(
            start=dark_start, end=dark_end
        )

        # Mock forecast with 3-hour periods that will be interpolated
        mock_instance.get_forecast_by_location.return_value = {
            tz.localize(datetime(2025, 1, 10, 18, 0)): 4.0,  # 6pm-9pm period (Kp 4.0)
            tz.localize(
                datetime(2025, 1, 10, 21, 0)
            ): 3.0,  # 9pm-midnight period (Kp 3.0)
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


def test_forecast_fetch_success():
    """Test successful fetch from NOAA when no text provided."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_FORECAST_TEXT
    mock_resp.raise_for_status = MagicMock()
    with patch("weather.night_sky.requests.get", return_value=mock_resp):
        f = Forecast()
        assert len(f.forecast_periods) == 24


def test_forecast_from_file(tmp_path):
    """Test Forecast.from_file classmethod."""
    filepath = tmp_path / "forecast.txt"
    filepath.write_text(SAMPLE_FORECAST_TEXT)
    f = Forecast.from_file(str(filepath))
    assert len(f.forecast_periods) == 24
    assert f.issue_date.year == 2025


def test_parse_date_missing():
    """Test missing :Issued: date raises ForecastValidationError."""
    bad_text = SAMPLE_FORECAST_TEXT.replace(
        ":Issued: 2025 Jan 10 1230 UTC", ":Issued: no date here"
    )
    with pytest.raises(
        ForecastValidationError, match="Could not find valid issue date"
    ):
        Forecast(bad_text)


def test_parse_date_invalid_format():
    """Test invalid date format in :Issued: line raises ForecastValidationError."""
    bad_text = SAMPLE_FORECAST_TEXT.replace(
        ":Issued: 2025 Jan 10 1230 UTC", ":Issued: 2025 Xxx 99 1230 UTC"
    )
    with pytest.raises(ForecastValidationError):
        Forecast(bad_text)


def test_invalid_kp_value():
    """Test invalid (non-numeric) Kp value raises ForecastValidationError."""
    bad_text = SAMPLE_FORECAST_TEXT.replace(
        "1.33         2.33         1.67", "abc          2.33         1.67"
    )
    with pytest.raises(ForecastValidationError, match="Invalid Kp value"):
        Forecast(bad_text)


def test_invalid_data_line():
    """Test data line with wrong number of columns raises ForecastValidationError."""
    # Replace a data line to have too few columns
    bad_text = SAMPLE_FORECAST_TEXT.replace(
        "00-03UT       1.33         2.33         1.67",
        "00-03UT       1.33         2.33",
    )
    with pytest.raises(ForecastValidationError, match="Invalid data line"):
        Forecast(bad_text)


def test_get_next_dark_period_after_sunset(sample_forecast):
    """Test dark period calculation when start_time is after sunset (uses next day)."""
    # Use MST time after sunset (sunset is ~5:10 PM MST in January)
    mst = pytz.timezone("US/Mountain")
    test_time = mst.localize(
        datetime(2025, 1, 10, 22, 0)
    )  # 10pm MST, well after sunset
    dark_period = sample_forecast.get_next_dark_period(
        latitude=48.528, longitude=-113.989, start_time=test_time
    )
    assert isinstance(dark_period, DarkPeriod)
    # Should return NEXT day's sunset since we're already past today's
    assert dark_period.start > test_time
    assert dark_period.end > dark_period.start


def test_get_next_dark_period_naive_start_time(sample_forecast):
    """Test that naive start_time raises ValueError."""
    naive_time = datetime(2025, 1, 10, 12, 0)  # No timezone
    with pytest.raises(ValueError, match="timezone-aware"):
        sample_forecast.get_next_dark_period(
            latitude=48.528, longitude=-113.989, start_time=naive_time
        )


def test_get_forecast_by_location_naive_start_time(sample_forecast):
    """Test that naive start_time raises ValueError in get_forecast_by_location."""
    naive_time = datetime(2025, 1, 10, 12, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        sample_forecast.get_forecast_by_location(
            latitude=48.528,
            longitude=-113.989,
            timezone="US/Mountain",
            start_time=naive_time,
        )


def test_get_forecast_by_location_none_timezone(sample_forecast):
    """Test that None timezone raises ValueError."""
    test_time = datetime(2025, 1, 10, 12, 0, tzinfo=pytz.UTC)
    with pytest.raises(ValueError, match="timezone must be provided"):
        sample_forecast.get_forecast_by_location(
            latitude=48.528,
            longitude=-113.989,
            timezone=None,
            start_time=test_time,
        )


def test_get_forecast_naive_times(sample_forecast):
    """Test get_forecast with naive start_time and end_time (localizes them)."""
    start = datetime(2025, 1, 10, 18, 0)  # naive
    end = datetime(2025, 1, 11, 6, 0)  # naive
    forecast = sample_forecast.get_forecast(
        start_time=start, end_time=end, timezone="US/Mountain"
    )
    assert isinstance(forecast, dict)
    assert len(forecast) > 0


def test_aurora_strength_kp_9():
    """Test aurora strength for Kp = 9.0 returns STRONG."""
    assert Forecast.get_aurora_strength(9.0) == "STRONG"


def test_forecast_str(sample_forecast):
    """Test __str__ method produces readable output."""
    result = str(sample_forecast)
    assert "NOAA Kp Forecast" in result
    assert "Issued:" in result
    assert "Forecast Range:" in result
    assert "Kp Range:" in result


def test_strftime():
    """Test Forecast.strftime classmethod."""
    tz = pytz.timezone("US/Mountain")
    dt = tz.localize(datetime(2025, 1, 10, 20, 0))
    result = Forecast.strftime(dt)
    assert isinstance(result, str)
    assert "8" in result or "20" in result  # 8pm or 20:00


def test_aurora_forecast_cloudy():
    """Test aurora forecast with cloudy skies and visible aurora."""
    with patch("weather.night_sky.Forecast") as MockForecast:
        mock_instance = MockForecast.return_value
        tz = pytz.timezone("US/Mountain")
        dark_start = tz.localize(datetime(2025, 1, 10, 20, 0))
        dark_end = tz.localize(datetime(2025, 1, 11, 6, 0))
        mock_instance.get_next_dark_period.return_value = DarkPeriod(
            start=dark_start, end=dark_end
        )
        # High Kp values that trigger aurora message
        mock_instance.get_forecast_by_location.return_value = {
            tz.localize(datetime(2025, 1, 10, 21, 0)): 5.0,
        }
        MockForecast.get_aurora_strength = Forecast.get_aurora_strength
        MockForecast.strftime = Forecast.strftime

        cast, msg = aurora_forecast(cloud_cover=0.5)  # cloudy
        assert "visible" in cast
        assert "cloudy" in msg


def test_aurora_forecast_clear_and_visible():
    """Test aurora forecast with clear skies and visible aurora."""
    with patch("weather.night_sky.Forecast") as MockForecast:
        mock_instance = MockForecast.return_value
        tz = pytz.timezone("US/Mountain")
        dark_start = tz.localize(datetime(2025, 1, 10, 20, 0))
        dark_end = tz.localize(datetime(2025, 1, 11, 6, 0))
        mock_instance.get_next_dark_period.return_value = DarkPeriod(
            start=dark_start, end=dark_end
        )
        mock_instance.get_forecast_by_location.return_value = {
            tz.localize(datetime(2025, 1, 10, 21, 0)): 5.0,
        }
        MockForecast.get_aurora_strength = Forecast.get_aurora_strength
        MockForecast.strftime = Forecast.strftime

        cast, msg = aurora_forecast(cloud_cover=0.1)  # clear
        assert "visible" in cast
        assert "great night" in msg


def test_aurora_forecast_no_dark_hours():
    """Test aurora forecast when no dark hours overlap with forecast."""
    with patch("weather.night_sky.Forecast") as MockForecast:
        mock_instance = MockForecast.return_value
        tz = pytz.timezone("US/Mountain")
        dark_start = tz.localize(datetime(2025, 1, 10, 20, 0))
        dark_end = tz.localize(datetime(2025, 1, 11, 6, 0))
        mock_instance.get_next_dark_period.return_value = DarkPeriod(
            start=dark_start, end=dark_end
        )
        # Return forecast periods that don't overlap with dark period
        mock_instance.get_forecast_by_location.return_value = {
            tz.localize(datetime(2025, 1, 10, 12, 0)): 2.0,  # noon, before dark
        }
        MockForecast.get_aurora_strength = Forecast.get_aurora_strength

        result = aurora_forecast(cloud_cover=0.0)
        assert result == ("No aurora forecast available", "")
