"""
This module provides a function to update subscriber information in the Drip email marketing platform.
"""

import json
import os
import urllib.parse

import requests


def update_subscriber(updates: dict):
    """
    Update subscriber information in Drip.

    Args:
        updates (dict): A dictionary containing the subscriber information to be updated.

    Returns:
        None
    """
    email = updates.get("email")
    email = urllib.parse.quote(email, safe="@")
    drip_token = os.environ["DRIP_TOKEN"]
    account_id = os.environ["DRIP_ACCOUNT"]
    api_key = drip_token
    url = f"https://api.getdrip.com/v2/{account_id}/subscribers"

    headers = {
        "Authorization": "Bearer " + api_key,
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
