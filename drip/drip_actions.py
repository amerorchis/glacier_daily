"""
This module provides functions to interact with the Drip email marketing platform, including retrieving subscribers and triggering workflows.
"""

import json

import requests

from drip.scheduled_subs import update_scheduled_subs
from drip.subscriber_list import subscriber_list
from shared.logging_config import get_logger
from shared.settings import get_settings

logger = get_logger(__name__)

DRIP_BATCH_SIZE = 1000


def record_drip_event(email: str, event: str = "Glacier Daily Update trigger") -> None:
    """
    Record a single event for a single subscriber using Drip's record event endpoint.

    Args:
        email (str): The subscriber's email address.
        event (str): The event name to record. Defaults to 'Glacier Daily Update trigger'.

    Returns:
        None
    """
    settings = get_settings()

    url = f"https://api.getdrip.com/v2/{settings.DRIP_ACCOUNT}/events"
    headers = {
        "Authorization": "Bearer " + settings.DRIP_TOKEN,
        "Content-Type": "application/vnd.api+json",
        "User-Agent": "Glacier Daily API (glacier.org)",
    }

    data = {
        "events": [
            {
                "email": email,
                "action": event,
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)

    if response.status_code == 204:
        logger.info(f"Drip: Event '{event}' recorded successfully for {email}!")
    else:
        logger.error(f"Failed to record event for {email}. Error message: {response}")


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


def bulk_workflow_trigger(sub_list: list) -> None:
    """
    Trigger a bulk workflow action in Drip to increase capacity from 3,600/hour to 50,000/hour.

    Args:
        sub_list (list): A list of subscriber emails.

    Returns:
        None
    """
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
                f"Failed to parse JSON response from Drip bulk workflow. "
                f"Status: {response.status_code}, Body: {response.text[:200]}"
            )
            continue

        if response.status_code == 201:
            logger.info("Drip: Bulk workflow add successful!")
        else:
            logger.error(
                f"Failed to add subscribers to the campaign. Error message: "
                f"{r['errors'][0]['code']} - {r['errors'][0]['message']}"
            )


def send_in_drip(
    email: str,
    campaign_id: str = "",
) -> None:
    """
    Send an email to a single subscriber using Drip.

    Args:
        email (str): The subscriber's email address.
        campaign_id (str): The campaign ID. Defaults to settings.DRIP_CAMPAIGN_ID.

    Returns:
        None
    """
    settings = get_settings()
    if not campaign_id:
        campaign_id = settings.DRIP_CAMPAIGN_ID

    url = f"https://api.getdrip.com/v2/{settings.DRIP_ACCOUNT}/workflows/{campaign_id}/subscribers"
    headers = {
        "Authorization": "Bearer " + settings.DRIP_TOKEN,
        "Content-Type": "application/vnd.api+json",
    }

    data = {
        "subscribers": [
            {
                "email": email,
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)

    try:
        r = response.json()
    except json.JSONDecodeError:
        logger.error(
            f"Failed to parse JSON response from Drip send. "
            f"Status: {response.status_code}, Body: {response.text[:200]}"
        )
        return

    if response.status_code == 201:
        logger.info(f"Drip: Email sent successfully to {email}!")
    else:
        logger.error(
            f"Failed to subscribe {email} to the campaign. Error message: "
            f"{r['errors'][0]['code']} - {r['errors'][0]['message']}"
        )


if __name__ == "__main__":
    # Example usage
    email = "andrew@glacier.org"
    record_drip_event(email)
