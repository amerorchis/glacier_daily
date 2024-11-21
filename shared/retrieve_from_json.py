import json
import base64
from datetime import datetime

def retrieve_from_json(keys_to_retrieve) -> tuple:
    """
    Check if we already have data from today in email.json
    Args:
        *keys_to_retrieve: Variable list of keys to retrieve from the JSON if date matches
    
    Returns:
        tuple: (bool, list of decoded values if exists, else None)
    """
    try:
        with open('server/email.json', 'r', encoding='utf8') as f:
            data = json.load(f)

        # Check if date matches today
        stored_date = data.get('date')
        today = datetime.now().strftime('%Y-%m-%d')

        if stored_date == today:
            # Retrieve and decode the requested values
            decoded_values = []
            for key in keys_to_retrieve:
                value = data.get(key, '')
                decoded_value = base64.b64decode(value).decode('utf-8') if value else None
                if decoded_value:
                    decoded_values.append(decoded_value)

            if len(decoded_values) == len(keys_to_retrieve):
                return True, decoded_values

        return False, None

    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return False, None
