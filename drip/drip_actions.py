"""
This module provides functions to interact with the Drip email marketing platform, including retrieving subscribers and triggering workflows.
"""

import json
import os
import sys

import requests

from drip.scheduled_subs import update_scheduled_subs
from drip.subscriber_list import subscriber_list


def record_drip_event(email: str, event: str = "Glacier Daily Update trigger") -> None:
    """
    Record a single event for a single subscriber using Drip's record event endpoint.

    Args:
        email (str): The subscriber's email address.
        event (str): The event name to record. Defaults to 'Glacier Daily Update trigger'.

    Returns:
        None
    """
    drip_token = os.environ["DRIP_TOKEN"]
    account_id = os.environ["DRIP_ACCOUNT"]
    api_key = drip_token

    url = f"https://api.getdrip.com/v2/{account_id}/events"
    headers = {
        "Authorization": "Bearer " + api_key,
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
        print(f"Drip: Event '{event}' recorded successfully for {email}!")
    else:
        print(
            f"Failed to record event for {email}. Error message: {response}",
            file=sys.stderr,
        )


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
    drip_token = os.environ["DRIP_TOKEN"]
    account_id = os.environ["DRIP_ACCOUNT"]
    api_key = drip_token

    url = f"https://api.getdrip.com/v2/{account_id}/events/batches"
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/vnd.api+json",
        "User-Agent": "Glacier Daily API (glacier.org)",
    }

    event = "Glacier Daily Update trigger"

    chunks_of_1000 = [sub_list[i : i + 1000] for i in range(0, len(sub_list), 1000)]

    for subs in chunks_of_1000:
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
        r = response.json()

        if response.status_code == 201:
            print("Drip: Bulk workflow add successful!")
        else:
            print(
                "Failed to add subscribers to the campaign. Error message:",
                r["errors"][0]["code"],
                " - ",
                r["errors"][0]["message"],
            )


def send_in_drip(email: str, campaign_id: str = "169298893") -> None:
    """
    Send an email to a single subscriber using Drip.

    Args:
        email (str): The subscriber's email address.
        campaign_id (str): The campaign ID. Defaults to '169298893'.

    Returns:
        None
    """
    drip_token = os.environ["DRIP_TOKEN"]
    account_id = os.environ["DRIP_ACCOUNT"]
    api_key = drip_token

    url = f"https://api.getdrip.com/v2/{account_id}/workflows/{campaign_id}/subscribers"
    headers = {
        "Authorization": "Bearer " + api_key,
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
    r = response.json()

    if response.status_code == 201:
        print(f"Drip: Email sent successfully to {email}!")
    else:
        print(
            f"Failed to subscribe {email} to the campaign. Error message:",
            r["errors"][0]["code"],
            " - ",
            r["errors"][0]["message"],
            file=sys.stderr,
        )


if __name__ == "__main__":
    # Example usage
    email = "andrew@glacier.org"
    record_drip_event(email)
