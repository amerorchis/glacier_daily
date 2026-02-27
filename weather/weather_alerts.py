"""
This module fetches and processes weather alerts from the National Weather Service for GNP.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from time import sleep
from typing import ClassVar

import requests

from shared.data_types import AlertBullet
from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class WeatherAlert:
    """
    Defines an individual alert
    """

    headline: str
    description: str
    issued_time: datetime
    full_text: str


class WeatherAlertService:
    """
    Defines a weather service
    """

    BASE_URL = "https://api.weather.gov"
    ZONES: ClassVar[list[str]] = [
        f"{BASE_URL}/zones/forecast/MTZ301",
        f"{BASE_URL}/zones/forecast/MTZ302",
        f"{BASE_URL}/zones/county/MTC029",
        f"{BASE_URL}/zones/county/MTC035",
        f"{BASE_URL}/zones/forecast/MTZ002",
        f"{BASE_URL}/zones/forecast/MTZ003",
        f"{BASE_URL}/zones/fire/MTZ105",
    ]
    HEADERS: ClassVar[dict[str, str]] = {"User-Agent": "Mozilla/5.0"}
    MAX_RETRIES = 10
    RETRY_DELAY = 3
    SEVERITY_ORDER: ClassVar[dict[str, int]] = {
        "Extreme": 0,
        "Severe": 1,
    }

    @staticmethod
    def parse_alert_time(text: str) -> datetime | None:
        """Parse alert time from text string."""
        match = re.match(r"^(.+?) issued (.*?)\sM[DS]T", text)
        if not match:
            return None

        time_str = f"{match.group(2)} {now_mountain().year}"
        return datetime.strptime(time_str, "%B %d at %I:%M%p %Y")

    @staticmethod
    def parse_nested_bullets(text: str) -> tuple[str, list[str]]:
        """Parse alert text into headline and bullet points."""
        # Split main title from description
        parts = text.split(": ", 1)
        if len(parts) != 2:
            return text, []

        headline, description = parts

        # Find bullet points using regex
        bullet_points = re.findall(r"\* ([^\n]+?)(?=\n\n|\* |$)", description)

        # Clean up the bullet points
        cleaned_bullets = []
        for point in bullet_points:
            point = point.strip()
            if point:
                # Convert WHAT..., WHERE..., etc. to What:, Where:, etc.
                point = re.sub(
                    r"^(WHAT|WHERE|WHEN|IMPACTS|ADDITIONAL DETAILS)\.+\s*",
                    lambda m: m.group(1).capitalize() + ": ",
                    point,
                )
                cleaned_bullets.append(point)

        return headline, cleaned_bullets

    def format_html_message(self, alerts: list[WeatherAlert]) -> str:
        """Format alerts into HTML message with nested bullet points."""
        if not alerts:
            return ""

        plural = "s" if len(alerts) > 1 else ""
        message = (
            f'<p style="font-size:14px; line-height:22px; font-weight:bold; color:#333333; margin:0 0 5px;">'
            f'<a href="https://weather.gov" style="color:#6c7e44; text-decoration:none;">Alert{plural} from the National Weather Service</a></p>'
        )
        message += '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'

        for alert in alerts:
            headline, bullets = self.parse_nested_bullets(alert.full_text)
            message += f"<li>{headline}"

            if bullets:
                message += "\n<ul style='margin-top:5px; margin-bottom:5px;'>\n"
                for bullet in bullets:
                    message += f"<li>{bullet}</li>\n"
                message += "</ul>"

            message += "</li>\n"

        return message + "</ul>"

    def fetch_alerts(self) -> list[dict]:
        """Fetch alerts with retry logic."""
        for _ in range(self.MAX_RETRIES):
            response = requests.get(
                f"{self.BASE_URL}/alerts/active/area/MT",
                headers=self.HEADERS,
                timeout=10,
            )
            if response.status_code == 200:
                return json.loads(response.content)["features"]
            logger.warning("Weather alert API returned status %s", response.status_code)
            sleep(self.RETRY_DELAY)
        return []

    def filter_local_alerts(self, alerts: list[dict]) -> list[dict]:
        """Filter alerts for local zones."""
        affected_zones = [alert["properties"]["affectedZones"] for alert in alerts]
        return [
            alert["properties"]
            for i, alert in enumerate(alerts)
            if any(zone in affected_zones[i] for zone in self.ZONES)
        ]

    def filter_by_relevance(self, alerts: list[dict]) -> list[dict]:
        """Filter alerts by severity, status, and message type.

        Keeps only actionable alerts:
        - severity must be 'Extreme' or 'Severe'
        - status must be 'Actual' (not test/exercise/draft)
        - messageType must not be 'Cancel'
        """
        return [
            alert
            for alert in alerts
            if alert.get("severity") in self.SEVERITY_ORDER
            and alert.get("status") == "Actual"
            and alert.get("messageType") != "Cancel"
        ]

    def deduplicate_alerts(self, alerts: list[dict]) -> list[dict]:
        """Deduplicate alerts by event type, keeping the most recently sent.

        Uses the structured 'event' field from the NWS API instead of parsing headlines.
        """
        best_by_event: dict[str, dict] = {}
        for alert in alerts:
            event_type = alert.get("event", "")
            sent = alert.get("sent", "")
            if event_type not in best_by_event or sent > best_by_event[event_type].get(
                "sent", ""
            ):
                best_by_event[event_type] = alert
        return list(best_by_event.values())

    def sort_alerts(self, alerts: list[dict]) -> list[dict]:
        """Sort alerts by severity (Extreme first), then by sent time (newest first)."""
        return sorted(
            alerts,
            key=lambda a: (
                self.SEVERITY_ORDER.get(a.get("severity", ""), 99),
                -(
                    datetime.fromisoformat(a["sent"]).timestamp()
                    if a.get("sent")
                    else 0
                ),
            ),
        )

    def process_alerts(self, alerts: list[dict]) -> list[WeatherAlert]:
        """Filter, deduplicate, sort, and convert alerts to WeatherAlert objects."""
        filtered = self.filter_by_relevance(alerts)
        deduped = self.deduplicate_alerts(filtered)
        ordered = self.sort_alerts(deduped)

        processed = []
        for alert in ordered:
            text = f"{alert['headline']}: {alert['description']}".replace(r"\n", "")
            sent_time = (
                datetime.fromisoformat(alert["sent"]) if alert.get("sent") else None
            )
            if sent_time is None:
                sent_time = self.parse_alert_time(text)
            if sent_time is None:
                continue

            processed.append(
                WeatherAlert(
                    headline=alert["headline"],
                    description=alert["description"],
                    issued_time=sent_time,
                    full_text=text,
                )
            )

        return processed


def weather_alerts() -> list[AlertBullet]:
    """
    Fetch and process weather alerts for Glacier National Park.

    Returns:
        list[AlertBullet]: Structured alert data.
    """
    try:
        service = WeatherAlertService()
        raw_alerts = service.fetch_alerts()
        if not raw_alerts:
            return []

        local_alerts = service.filter_local_alerts(raw_alerts)
        processed_alerts = service.process_alerts(local_alerts)

        result = []
        for alert in processed_alerts:
            headline, bullets = service.parse_nested_bullets(alert.full_text)
            result.append(AlertBullet(headline=headline, bullets=bullets))
        return result

    except Exception as e:
        logger.error("Error processing weather alerts: %s", e, exc_info=True)
        return []


if __name__ == "__main__":  # pragma: no cover
    print(weather_alerts())
