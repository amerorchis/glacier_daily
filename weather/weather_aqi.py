"""
This module fetches the Air Quality Index (AQI) for West Glacier from the National Park Service.
"""

import requests
from urllib3.exceptions import InsecureRequestWarning
from contextlib import contextmanager

@contextmanager
def suppress_insecure_request_warning():
    """
    Context manager to suppress insecure request warnings.
    """
    # Disable the warning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    yield

def get_air_quality() -> int:
    """
    Fetch the current Air Quality Index (AQI) for West Glacier.
    
    Returns:
        int: The current AQI value or -99 if unavailable.
    """
    try:
        with suppress_insecure_request_warning():

            response = requests.get(
                'https://www.nps.gov/featurecontent/ard/currentdata/json/glac.json',
                verify=False,
                timeout=60
            )

            data = response.json()['locations']

            west_glacier = next((place for place in data if 'West Glacier' in place['name']), None)
            if west_glacier:
                aqi = west_glacier['particulatesPA']['nowCastPM']['currentAQIVal']
                return aqi if aqi != -99 else ''

        return ''

    except requests.exceptions.JSONDecodeError:
        print('JSON decoding error')
        return ''

    except requests.exceptions.RequestException as e:
        print(f'Request error: {e}')
        return ''

if __name__ == "__main__":
    print(get_air_quality())
