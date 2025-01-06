"""
This module provides a function to retrieve a list of subscribers from the Drip email marketing platform.
"""

import requests
import os
import sys

def subscriber_list(tag = 'Glacier Daily Update') -> list:
    """
    Retrieve a list of subscribers with a specific tag from Drip.

    Args:
        tag (str): The tag to filter subscribers by. Defaults to 'Glacier Daily Update'.

    Returns:
        list: A list of subscriber emails or subscriber data.
    """
    drip_token = os.environ['DRIP_TOKEN']
    account_id = os.environ['DRIP_ACCOUNT']
    api_key = drip_token
    url = f"https://api.getdrip.com/v2/{account_id}/subscribers"

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/vnd.api+json"
    }

    page = 1
    subs = []

    params = {
        "status": "active",
        "tags": tag,
        "per_page": "1000",
        "page": page
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        subs.extend([data['subscribers'][i] for i in range(len(data['subscribers']))])

        # Fetch multiple pages if needed
        while data['meta']['total_pages'] > page:
            page += 1
            params['page'] = page
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            subs.extend([data['subscribers'][i] for i in range(len(data['subscribers']))])

        # If we're getting a list of people to send to just grab emails, else send all of their data.
        if tag in ['Glacier Daily Update', 'Test Glacier Daily Update']:
            subs = [i['email'] for i in subs]

        return subs

    except requests.exceptions.RequestException as e:
        # Handle errors
        print(f'Failed to retrieve subscribers with tag(s) {tag}. {e}', file=sys.stderr)
        return []
