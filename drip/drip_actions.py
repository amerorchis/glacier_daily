"""
This module provides functions to interact with the Drip email marketing platform, including retrieving subscribers and triggering workflows.
"""

import json
from dataclasses import dataclass

import requests

from drip.scheduled_subs import update_scheduled_subs
from drip.subscriber_list import subscriber_list
from shared.logging_config import get_logger
from shared.settings import get_settings

logger = get_logger(__name__)

DRIP_BATCH_SIZE = 1000


@dataclass
class BatchResult:
    """Result of a bulk workflow trigger operation."""

    sent: int = 0
    failed: int = 0


def get_subs(tag: str) -> list:
    """
    Retrieve and update the list of subscribers with a specific tag.

    Args:
        tag (str): The tag to filter subscribers by.

    Returns:
        list: A list of subscriber emails.
    """
    updates = update_scheduled_subs()
    subs = subscriber_list(tag)

    # Update subscriber list based on changes today (drip updates aren't fast enough)
    for i in updates["start"]:
        if i not in subs:
            subs.append(i)

    for i in updates["end"]:
        if i in subs:
            subs.remove(i)

    return subs


def bulk_workflow_trigger(sub_list: list) -> BatchResult:
    """
    Trigger a bulk workflow action in Drip to increase capacity from 3,600/hour to 50,000/hour.

    Args:
        sub_list (list): A list of subscriber emails.

    Returns:
        BatchResult: Counts of sent and failed subscribers.
    """
    result = BatchResult()
    settings = get_settings()

    url = f"https://api.getdrip.com/v2/{settings.DRIP_ACCOUNT}/events/batches"
    headers = {
        "Authorization": "Bearer " + settings.DRIP_TOKEN,
        "Content-Type": "application/vnd.api+json",
        "User-Agent": "Glacier Daily API (glacier.org)",
    }

    event = "Glacier Daily Update trigger"

    chunks = [
        sub_list[i : i + DRIP_BATCH_SIZE]
        for i in range(0, len(sub_list), DRIP_BATCH_SIZE)
    ]

    for subs in chunks:
        subs_json = list()
        for i in subs:
            update = {
                "email": i,
                "action": event,
            }
            subs_json.append(update)

        data = {"batches": [{"events": subs_json}]}

        response = requests.post(
            url, headers=headers, data=json.dumps(data), timeout=30
        )

        try:
            r = response.json()
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse JSON response from Drip bulk workflow. "
                "Status: %s, Body: %s",
                response.status_code,
                response.text[:200],
            )
            result.failed += len(subs)
            continue

        if response.status_code == 201:
            logger.info("Drip: Bulk workflow add successful!")
            result.sent += len(subs)
        else:
            logger.error(
                "Failed to add subscribers to the campaign. Error message: %s - %s",
                r["errors"][0]["code"],
                r["errors"][0]["message"],
            )
            result.failed += len(subs)

    return result
