"""
Structured data types for module outputs.

These frozen dataclasses replace the HTML strings that modules previously returned.
Templates (Jinja2) handle all HTML rendering using these structured types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """A single park ranger event."""

    start_time: str  # "8:30 am"
    end_time: str  # "10 am"
    name: str  # "Creekside Stroll"
    location: str  # "Apgar VC"
    link: str  # NPS event URL
    sortable: datetime  # For sort ordering (excluded from JSON serialization)


@dataclass(frozen=True)
class EventsResult:
    """Result from the events module."""

    events: list[Event] = field(default_factory=list)
    seasonal_message: str = ""  # "Ranger programs have concluded for the season."
    error_message: str = ""  # "Ranger program schedule could not be retrieved."


@dataclass(frozen=True)
class TrailsResult:
    """Result from the trails module."""

    closures: list[str] = field(default_factory=list)
    no_closures_message: str = ""  # "There are no trail closures in effect today!"
    error_message: str = ""  # "The trail closures page is currently down."


@dataclass(frozen=True)
class CampgroundsResult:
    """Result from the campgrounds module."""

    statuses: list[str] = field(default_factory=list)
    error_message: str = ""


@dataclass(frozen=True)
class RoadsResult:
    """Result from the roads module."""

    closures: list[str] = field(default_factory=list)
    no_closures_message: str = ""  # "There are no closures on major roads today!"
    error_message: str = ""


@dataclass(frozen=True)
class HikerBikerResult:
    """Result from the hiker/biker module."""

    closures: list[str] = field(default_factory=list)
    explanatory_note: str = ""


@dataclass(frozen=True)
class NoticesResult:
    """Result from the notices module."""

    notices: list[str] = field(
        default_factory=list
    )  # May contain HTML links from Google Sheet
    fallback_message: str = ""  # "There were no notices for today." or error msg


@dataclass(frozen=True)
class AlertBullet:
    """A single weather alert with headline and optional bullet points."""

    headline: str
    bullets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WeatherResult:
    """Result from the weather module.

    Note: weather_image_url is NOT included here — it's generated separately
    by weather_image() in gen_data() and stored as a top-level field.
    """

    daylight_message: str = ""  # "Today, sunrise is at 6:14am..."
    forecasts: list[tuple[str, int, int, str]] = field(
        default_factory=list
    )  # [(location, high, low, condition)]
    season: str | None = None
    aqi_value: int | None = None
    aqi_category: str = ""  # "good", "moderate", etc.
    aurora_quality: str = ""  # "3.2 Kp (not visible)"
    aurora_message: str = ""
    sunset_quality: str = ""  # "good", "moderate", etc.
    sunset_message: str = ""
    cloud_cover_pct: int = 0
    alerts: list[AlertBullet] = field(default_factory=list)
