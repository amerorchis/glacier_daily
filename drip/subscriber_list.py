"""
This module provides a function to retrieve a list of subscribers from the Drip email marketing platform.
"""

import requests

from shared.logging_config import get_logger
from shared.settings import get_settings

logger = get_logger(__name__)


def subscriber_list(tag="Glacier Daily Update") -> list:
    """
    Retrieve a list of subscribers with a specific tag from Drip.

    Args:
        tag (str): The tag to filter subscribers by. Defaults to 'Glacier Daily Update'.

    Returns:
        list: A list of subscriber emails or subscriber data.
    """
    settings = get_settings()
    url = f"https://api.getdrip.com/v2/{settings.DRIP_ACCOUNT}/subscribers"

    headers = {
        "Authorization": "Bearer " + settings.DRIP_TOKEN,
        "Content-Type": "application/vnd.api+json",
    }

    page = 1
    subs = []

    params = {"status": "active", "tags": tag, "per_page": "1000", "page": page}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        subs.extend(data["subscribers"])

        # Fetch multiple pages if needed
        while data["meta"]["total_pages"] > page:
            page += 1
            params["page"] = page
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            subs.extend(data["subscribers"])

        # If we're getting a list of people to send to just grab emails, else send all of their data.
        if tag in ["Glacier Daily Update", "Test Glacier Daily Update"]:
            subs = [i["email"] for i in subs]

        return subs

    except requests.exceptions.RequestException as e:
        # Handle errors
        logger.error("Failed to retrieve subscribers with tag(s) %s. %s", tag, e)
        return []
