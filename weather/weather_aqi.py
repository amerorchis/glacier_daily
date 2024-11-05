import requests
from urllib3.exceptions import InsecureRequestWarning
from contextlib import contextmanager

@contextmanager
def suppress_insecure_request_warning():
    # Disable the warning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    yield

def get_air_quality():
    try:
        with suppress_insecure_request_warning():

            response = requests.get(
                'https://www.nps.gov/featurecontent/ard/currentdata/json/glac.json',
                verify=False
            )

            data = response.json()['locations']

            west_glacier = next((place for place in data if 'West Glacier' in place['name']), None)
            if west_glacier:
                    aqi = west_glacier['particulatesPA']['nowCastPM']['currentAQIVal']
                    return aqi if aqi != -99 else ''

        return ''

    except requests.exceptions.RequestException as e:
        print(f'Request error: {e}')
        return ''

    except requests.exceptions.JSONDecodeError as j:
        print('JSON decoding error')
        return ''

if __name__ == "__main__":
    print(get_air_quality())