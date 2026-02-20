"""
This module fetches and processes weather alerts from the National Weather Service for GNP.
"""

import json
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from time import sleep
from typing import Optional

import requests

from shared.datetime_utils import now_mountain


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
    ZONES = [
        f"{BASE_URL}/zones/forecast/MTZ301",
        f"{BASE_URL}/zones/forecast/MTZ302",
        f"{BASE_URL}/zones/county/MTC029",
        f"{BASE_URL}/zones/county/MTC035",
        f"{BASE_URL}/zones/forecast/MTZ002",
        f"{BASE_URL}/zones/forecast/MTZ003",
        f"{BASE_URL}/zones/fire/MTZ105",
    ]
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    MAX_RETRIES = 10
    RETRY_DELAY = 3
    MAX_ALERTS = (
        2  # Temporary limit max alerts until we find a way to filter relevant ones
    )

    @staticmethod
    def parse_alert_time(text: str) -> Optional[datetime]:
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
            print(f"Weather error for alerts: status code {response.status_code}")
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

    def process_alerts(self, alerts: list[dict]) -> list[WeatherAlert]:
        """Process and deduplicate alerts."""
        processed_alerts = []
        seen_headlines = set()

        for alert in alerts[: self.MAX_ALERTS]:  # Apply temporary limit
            text = f"{alert['headline']}: {alert['description']}".replace(r"\n", "")
            issued_time = self.parse_alert_time(text)
            if not issued_time:
                continue

            weather_alert = WeatherAlert(
                headline=alert["headline"],
                description=alert["description"],
                issued_time=issued_time,
                full_text=text,
            )

            # Only keep the latest alert for each headline
            alert_type = weather_alert.headline.split(" issued")[0]
            if alert_type not in seen_headlines:
                processed_alerts.append(weather_alert)
                seen_headlines.add(alert_type)
            else:
                existing_alert = next(
                    a
                    for a in processed_alerts
                    if a.headline.split(" issued")[0] == alert_type
                )
                if weather_alert.issued_time > existing_alert.issued_time:
                    processed_alerts.remove(existing_alert)
                    processed_alerts.append(weather_alert)

        return sorted(processed_alerts, key=lambda x: x.issued_time, reverse=True)


def weather_alerts() -> str:
    """
    Fetch and format weather alerts for Glacier National Park.

    Returns:
        str: Formatted weather alerts as HTML string.
    """
    try:
        service = WeatherAlertService()
        raw_alerts = service.fetch_alerts()
        if not raw_alerts:
            return ""

        local_alerts = service.filter_local_alerts(raw_alerts)
        processed_alerts = service.process_alerts(local_alerts)
        return service.format_html_message(processed_alerts)

    except Exception as e:
        print(f"Error processing weather alerts: {e}, {traceback.format_exc()}")
        return ""


if __name__ == "__main__":  # pragma: no cover
    print(weather_alerts())
