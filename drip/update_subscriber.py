"""
This module provides a function to update subscriber information in the Drip email marketing platform.
"""

import json
import urllib.parse

import requests

from shared.logging_config import get_logger
from shared.retry import retry
from shared.settings import get_settings

logger = get_logger(__name__)


@retry(2, (requests.exceptions.RequestException,), default=None, backoff=10)
def _post_subscriber_update(
    url: str, headers: dict, data: dict
) -> requests.Response | None:
    """Post subscriber update to Drip API."""
    return requests.post(url, headers=headers, data=json.dumps(data), timeout=30)


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

    response = _post_subscriber_update(url, headers, data)
    if response is None:
        logger.error("Failed to update %s: all retry attempts exhausted", email)
        return

    try:
        r = response.json()
    except json.JSONDecodeError:
        logger.error("Failed to parse Drip response for %s", email)
        return

    if response.status_code == 200:
        logger.info("Drip: %s was updated", email)
    else:
        errors = r.get("errors", [{}])
        err = errors[0] if errors else {}
        logger.error(
            "Failed to update %s: %s - %s",
            email,
            err.get("code", "unknown"),
            err.get("message", "(no message)"),
        )
