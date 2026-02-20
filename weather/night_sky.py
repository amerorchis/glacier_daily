"""
Retrieve and process aurora forecast.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple, Optional

import pytz
import requests
from astral import LocationInfo
from astral.sun import sun
from requests.exceptions import RequestException

from shared.datetime_utils import format_time_with_timezone


class ForecastError(Exception):
    """Base class for forecast-related errors."""


class ForecastValidationError(ForecastError):
    """Raised when forecast data is invalid or corrupted."""


class ForecastFetchError(ForecastError):
    """Raised when forecast data cannot be fetched from NOAA."""


@dataclass
class KpPeriod:
    """Represents a single Kp forecast period."""

    start_time: datetime
    end_time: datetime
    kp_value: float

    def __str__(self) -> str:
        """Stringify"""
        return f"{self.start_time.strftime('%Y-%m-%d %H:%M')} {self.start_time.tzname}: Kp {self.kp_value}"


class DarkPeriod(NamedTuple):
    """Represents a period of darkness between sunset and sunrise."""

    start: datetime  # sunset time
    end: datetime  # sunrise time


class Forecast:
    """NOAA Kp-index forecast parser and analyzer."""

    FORECAST_URL = "https://services.swpc.noaa.gov/text/3-day-forecast.txt"

    STORM_LEVELS = {
        "G5": 9.0,  # Extreme
        "G4": 8.0,  # Severe
        "G3": 7.0,  # Strong
        "G2": 6.0,  # Moderate
        "G1": 5.0,  # Minor
    }

    AURORA_LEVELS = {
        "not visible": (0.0, 3.5),  # No visible aurora
        "weakly visible": (3.5, 5.0),  # Weak, visible aurora
        "visible": (5.0, 9.0),  # Strong aurora display
    }

    def __init__(self, forecast_text: Optional[str] = None):
        """Initialize forecast object, fetching from NOAA if no text provided."""
        if forecast_text is None:
            try:
                response = requests.get(self.FORECAST_URL, timeout=10)
                response.raise_for_status()
                forecast_text = response.text
            except RequestException as e:
                raise ForecastFetchError(
                    f"Failed to fetch NOAA forecast: {str(e)}"
                ) from e

        self.raw_text = forecast_text.strip()
        self.forecast_periods: list[KpPeriod] = []

        if not self._validate_text_structure():
            raise ForecastValidationError("Invalid forecast text structure")

        self._parse_date()
        self._parse_kp_indices()
        self._validate_data()

    @classmethod
    def from_file(cls, filepath: str) -> "Forecast":
        """Create Forecast instance from a local file."""
        with open(filepath) as f:
            return cls(f.read())

    def _validate_text_structure(self) -> bool:
        """Validate the basic structure of the forecast text."""
        required_sections = [
            ":Product: 3-Day Forecast",
            ":Issued:",
            "NOAA Kp index breakdown",
        ]
        return all(section in self.raw_text for section in required_sections)

    def _parse_date(self) -> None:
        """Parse and validate the forecast issue date."""
        match = re.search(
            r":Issued:\s+(\d{4}\s+\w+\s+\d{1,2}\s+\d{4})\s+UTC", self.raw_text
        )
        if not match:
            raise ForecastValidationError("Could not find valid issue date")

        try:
            date_str = match.group(1)
            self.issue_date = datetime.strptime(date_str, "%Y %b %d %H%M")
            self.issue_date = pytz.UTC.localize(self.issue_date)
        except ValueError as e:
            raise ForecastValidationError(f"Invalid date format: {e}") from e

    def _parse_kp_indices(self) -> None:
        """Parse and validate the Kp indices from the forecast text."""
        lines = self.raw_text.split("\n")

        # Find the Kp index section
        start_idx = None
        for i, line in enumerate(lines):
            if "NOAA Kp index breakdown" in line:
                start_idx = i + 2  # Skip the header and blank line
                break

        if start_idx is None:
            raise ForecastValidationError("Could not find Kp index breakdown section")

        # Parse dates from header line
        date_line = lines[start_idx]
        date_pattern = r"(\w{3})\s+(\d{1,2})"  # Matches "Jan 10", "Feb 5", etc.
        date_matches = re.finditer(date_pattern, date_line)

        dates = []
        for match in date_matches:
            month_str, day_str = match.groups()
            # Create date using the issue_date's year
            try:
                date = self.issue_date.replace(
                    month=datetime.strptime(month_str, "%b").month, day=int(day_str)
                )

                # Handle year boundary case (December -> January)
                if date < self.issue_date and date.month == 12:
                    date = date.replace(year=date.year + 1)
                elif date < self.issue_date and date.month == 1:
                    date = date.replace(year=self.issue_date.year + 1)

                dates.append(date)
            except ValueError as e:
                raise ForecastValidationError(
                    f"Invalid date in header: {month_str} {day_str}"
                ) from e

        if not dates:
            raise ForecastValidationError("Could not parse forecast dates")

        # Parse values for each time period
        for i in range(8):
            time_values = lines[start_idx + 1 + i].split()
            time_values = [
                i for i in time_values if "G" not in i
            ]  # Filter out any storm notes
            if len(time_values) != 4:  # Time range + 3 values
                raise ForecastValidationError(f"Invalid data line: {time_values}")

            time_range = time_values[0]
            start_hour = int(time_range.split("-")[0][:2])
            end_hour = int(time_range.split("-")[1][:2])

            for day_idx, kp_str in enumerate(time_values[1:]):
                try:
                    kp_value = float(kp_str)
                except ValueError as exc:
                    raise ForecastValidationError(
                        f"Invalid Kp value: {kp_str}"
                    ) from exc

                start_time = dates[day_idx].replace(hour=start_hour, minute=0)
                end_time = dates[day_idx].replace(hour=end_hour, minute=0)
                if end_hour == 0:  # Handle day boundary
                    end_time += timedelta(days=1)

                period = KpPeriod(start_time, end_time, kp_value)
                self.forecast_periods.append(period)

    def _validate_data(self) -> None:
        """Validate parsed forecast data for completeness and consistency."""
        if not self.forecast_periods:
            raise ForecastValidationError("No forecast periods parsed")

        # Check for gaps and overlaps
        sorted_periods = sorted(self.forecast_periods, key=lambda x: x.start_time)
        for i in range(len(sorted_periods) - 1):
            if sorted_periods[i].end_time != sorted_periods[i + 1].start_time:
                raise ForecastValidationError(
                    "Gap or overlap detected in forecast periods"
                )

        # Validate Kp values
        if any(not 0 <= period.kp_value <= 9 for period in self.forecast_periods):
            raise ForecastValidationError("Invalid Kp values detected")

    def get_next_dark_period(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
    ) -> DarkPeriod:
        """Find next period of darkness (sunset to sunrise) for given location.

        Args:
            latitude: Latitude in degrees (positive is North)
            longitude: Longitude in degrees (positive is East)
            start_time: Time to start searching from
            elevation: Optional elevation in meters

        Returns:
            DarkPeriod with start (sunset) and end (sunrise) times
        """
        if start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")

        # Create location
        location = LocationInfo(
            name="observation_point",
            region="",
            timezone="UTC",
            latitude=latitude,
            longitude=longitude,
        )

        # Get sun events for the starting day
        s = sun(location.observer, date=start_time, tzinfo=start_time.tzinfo)

        # If we're before today's sunset, use today's sunset and tomorrow's sunrise
        if start_time < s["sunset"]:
            sunset = s["sunset"]
            # Get tomorrow's sunrise
            tomorrow = start_time + timedelta(days=1)
            tomorrow_sun = sun(
                location.observer, date=tomorrow, tzinfo=start_time.tzinfo
            )
            sunrise = tomorrow_sun["sunrise"]
        else:
            # Use tomorrow's sunset and the day after's sunrise
            tomorrow = start_time + timedelta(days=1)
            tomorrow_sun = sun(
                location.observer, date=tomorrow, tzinfo=start_time.tzinfo
            )
            sunset = tomorrow_sun["sunset"]
            # Get the day after tomorrow's sunrise
            day_after = start_time + timedelta(days=2)
            day_after_sun = sun(
                location.observer, date=day_after, tzinfo=start_time.tzinfo
            )
            sunrise = day_after_sun["sunrise"]

        return DarkPeriod(start=sunset, end=sunrise)

    def get_forecast_by_location(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        start_time: Optional[datetime] = None,
    ) -> dict[datetime, float]:
        """Get Kp forecast for next dark period at given location."""
        # Set default start time to now
        if start_time is None:
            start_time = datetime.now(pytz.UTC)
        elif start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")

        # Set default timezone based on longitude
        if timezone is None:
            raise ValueError("timezone must be provided")

        # Get next dark period
        dark_period = self.get_next_dark_period(latitude, longitude, start_time)

        # Get forecast for dark period
        return self.get_forecast(
            start_time=dark_period.start, end_time=dark_period.end, timezone=timezone
        )

    def get_forecast(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        timezone: str = "US/Mountain",
    ) -> dict[datetime, float]:
        """Get Kp forecast for specified time range in given timezone."""
        tz = pytz.timezone(timezone)

        # Convert time range to UTC for comparison
        if start_time and start_time.tzinfo is None:
            start_time = tz.localize(start_time)
        if end_time and end_time.tzinfo is None:
            end_time = tz.localize(end_time)

        if start_time:
            start_time = start_time.astimezone(pytz.UTC)
        if end_time:
            end_time = end_time.astimezone(pytz.UTC)

        # Filter and convert periods to target timezone
        filtered_periods = [
            period
            for period in self.forecast_periods
            if (not start_time or period.end_time > start_time)
            and (not end_time or period.start_time < end_time)
        ]

        return {
            period.start_time.astimezone(tz): period.kp_value
            for period in sorted(filtered_periods, key=lambda x: x.start_time)
        }

    @classmethod
    def get_aurora_strength(cls, kp_value: float) -> str:
        """Get qualitative description of aurora strength for a given Kp value."""
        if not 0 <= kp_value <= 9:
            raise ValueError("Kp value must be between 0 and 9")

        for strength, (min_kp, max_kp) in cls.AURORA_LEVELS.items():
            if min_kp <= kp_value < max_kp:
                return strength
        return "STRONG"  # For Kp = 9.0

    @classmethod
    def strftime(cls, time: datetime) -> str:
        """Format datetime object to string."""
        return format_time_with_timezone(time)

    @property
    def max_kp(self) -> float:
        """Maximum forecasted Kp value."""
        return max(period.kp_value for period in self.forecast_periods)

    @property
    def min_kp(self) -> float:
        """Minimum forecasted Kp value."""
        return min(period.kp_value for period in self.forecast_periods)

    def __str__(self) -> str:
        """Human-readable string representation of the forecast."""
        return (
            f"NOAA Kp Forecast\n"
            f"Issued: {self.issue_date.strftime('%Y-%m-%d %H:%M %Z')}\n"
            f"Forecast Range: {self.forecast_periods[0].start_time.strftime('%Y-%m-%d %H:%M')} to "
            f"{self.forecast_periods[-1].end_time.strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Kp Range: {self.min_kp:.2f} to {self.max_kp:.2f}"
        )


def aurora_forecast(cloud_cover: float = 0.0) -> tuple[str, str]:
    """Get and format the forecast"""
    f = Forecast()

    cloudy = cloud_cover >= 0.3

    # Get the dark period and forecast
    latitude, longitude = 48.528, -113.989
    timezone = "US/Mountain"
    start_time = datetime.now(pytz.UTC)

    dark_period = f.get_next_dark_period(latitude, longitude, start_time)
    wg_forecast = f.get_forecast_by_location(
        latitude=latitude, longitude=longitude, timezone=timezone
    )

    # Interpolate 3-hour periods into hourly forecasts
    hourly_forecast = {}
    for period_start, kp_value in wg_forecast.items():
        # Each period is 3 hours, create 3 one-hour periods
        for hour_offset in range(3):
            hour_time = period_start + timedelta(hours=hour_offset)
            hourly_forecast[hour_time] = kp_value

    # Filter to only hours that are actually dark
    dark_hourly_forecast = {
        time: kp
        for time, kp in hourly_forecast.items()
        if time >= dark_period.start and time < dark_period.end
    }

    if not dark_hourly_forecast:
        # No dark hours in the forecast range
        return "No aurora forecast available", ""

    # Find the peak Kp during dark hours
    v_time = max(dark_hourly_forecast, key=dark_hourly_forecast.get)
    v = dark_hourly_forecast[v_time]

    cast = f"{v} Kp ({Forecast.get_aurora_strength(v)})"
    msg = ""
    if v > 3.8:
        msg = f"The aurora will be visible tonight with a peak Kp of {v} at {Forecast.strftime(v_time)} "
        if cloudy:
            msg += "but it will be cloudy."
        else:
            msg += "and skies are forecast to be clear! <strong>It's a great night to see the northern lights!</strong>"

    return cast, msg


if __name__ == "__main__":  # pragma: no cover
    print(aurora_forecast(cloud_cover=0.2))
