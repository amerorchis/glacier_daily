"""
This module provides functions to interact with the Drip email marketing platform, including retrieving subscribers and triggering workflows.
"""

import json
from dataclasses import dataclass

import requests

from drip.scheduled_subs import update_scheduled_subs
from drip.subscriber_list import subscriber_list
from shared.constants import DRIP_BATCH_SIZE
from shared.logging_config import get_logger
from shared.retry import retry
from shared.settings import get_settings

logger = get_logger(__name__)


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


@retry(2, (requests.exceptions.RequestException,), default=None, backoff=10)
def _post_drip_batch(url: str, headers: dict, data: dict) -> requests.Response | None:
    """Post a batch of events to Drip API."""
    return requests.post(url, headers=headers, data=json.dumps(data), timeout=15)


def bulk_workflow_trigger(sub_list: list) -> BatchResult:
    """
    Trigger a Drip bulk event batch to send at higher throughput than individual API calls.

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
        subs_json = []
        for i in subs:
            update = {
                "email": i,
                "action": event,
            }
            subs_json.append(update)

        data = {"batches": [{"events": subs_json}]}

        response = _post_drip_batch(url, headers, data)
        if response is None:
            result.failed += len(subs)
            continue

        try:
            r = response.json()
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse JSON response from Drip bulk workflow. Status: %s",
                response.status_code,
            )
            logger.debug("Drip non-JSON response body: %s", response.text[:200])
            result.failed += len(subs)
            continue

        if response.status_code == 201:
            logger.info("Drip: Bulk workflow add successful!")
            result.sent += len(subs)
        else:
            errors = r.get("errors", [])
            err = errors[0] if errors else {}
            code = err.get("code", "unknown")
            message = err.get("message") or "(no message)"
            raw = getattr(response, "text", None)
            if raw:
                logger.debug("Drip error response body: %s", raw[:200])
            logger.error(
                "Failed to add subscribers to the campaign. Error message: %s - %s",
                code,
                message,
            )
            result.failed += len(subs)

    return result
