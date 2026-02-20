"""
Get any values that have been retrieved already from today's JSON file.
"""

import base64
import json

from shared.datetime_utils import now_mountain


def retrieve_from_json(keys_to_retrieve: list) -> tuple:
    """
    Check if we already have data from today in email.json
    Args:
        *keys_to_retrieve: Variable list of keys to retrieve from the JSON if date matches

    Returns:
        tuple: (bool, list of decoded values if exists, else None)
    """
    try:
        with open("server/email.json", encoding="utf8") as f:
            data = json.load(f)

        # Check if date matches today
        stored_date = data.get("date")
        today = now_mountain().strftime("%Y-%m-%d")

        if stored_date == today:
            # Retrieve and decode the requested values
            decoded_values = []
            for key in keys_to_retrieve:
                value = data.get(key, "")
                decoded_value = (
                    base64.b64decode(value).decode("utf-8") if value else None
                )
                if decoded_value:
                    decoded_values.append(decoded_value)

            if len(decoded_values) == len(keys_to_retrieve):
                return True, decoded_values

        return False, None

    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return False, None
