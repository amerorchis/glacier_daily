"""
This module provides a function to update subscriber information in the Drip email marketing platform.
"""

import json
import urllib.parse

import requests

from shared.settings import get_settings


def update_subscriber(updates: dict):
    """
    Update subscriber information in Drip.

    Args:
        updates (dict): A dictionary containing the subscriber information to be updated.

    Returns:
        None
    """
    email = updates.get("email", "")
    email = urllib.parse.quote(email, safe="@")
    settings = get_settings()
    url = f"https://api.getdrip.com/v2/{settings.DRIP_ACCOUNT}/subscribers"

    headers = {
        "Authorization": "Bearer " + settings.DRIP_TOKEN,
        "Content-Type": "application/vnd.api+json",
    }

    data = {"subscribers": [updates]}

    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
    r = response.json()

    if response.status_code == 200:
        print(f"Drip: {email} was updated!")
    else:
        print(
            f"Failed to update {email}. Error message:",
            r["errors"][0]["code"],
            " - ",
            r["errors"][0]["message"],
        )
