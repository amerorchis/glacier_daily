"""
This module fetches the Air Quality Index (AQI) for West Glacier from the National Park Service.
"""

from __future__ import annotations

import time
import uuid

import requests

from shared.logging_config import get_logger

logger = get_logger(__name__)


def add_cache_buster(url: str) -> str:
    """
    Append cache-busting parameters to the given URL.
    Args:
        url (str): The original URL.
    Returns:
        str: The URL with appended cache-busting parameters.
    """
    # Generate the UUID (Random)
    generated_uuid = str(uuid.uuid4())

    # Generate Timestamp (Milliseconds)
    timestamp = int(time.time() * 1000)

    # Check if URL already has query parameters to decide between '?' and '&'
    separator = "&" if "?" in url else "?"

    # Construct the final URL using an f-string
    final_url = f"{url}{separator}uuid={generated_uuid}&_={timestamp}"

    return final_url


def get_air_quality() -> int | str:
    """
    Fetch the current Air Quality Index (AQI) for West Glacier.

    Returns:
        int: The current AQI value or -99 if unavailable.
    """
    try:
        url = "https://www.nps.gov/featurecontent/ard/currentdata/json/glac.json"
        url_with_cache_buster = add_cache_buster(url)

        response = requests.get(
            url_with_cache_buster,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            },
        )
        response.raise_for_status()
        data = response.json()["locations"]

        west_glacier = next(
            (place for place in data if "West Glacier" in place["name"]), None
        )
        if west_glacier:
            aqi = west_glacier["particulatesPA"]["nowCastPM"]["currentAQIVal"]
            return aqi if aqi != -99 else ""

        return ""

    except requests.exceptions.JSONDecodeError:
        logger.error("AQI JSON decoding error")
        return ""

    except requests.exceptions.RequestException as e:
        logger.error("AQI request error: %s", e)
        return ""


if __name__ == "__main__":  # pragma: no cover
    print(get_air_quality())
