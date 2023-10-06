import requests

def get_air_quality(zip_code = 59936):
    """
    EPA data just isn't cutting it, but this is how you would get that:

    api_url = f"https://www.airnowapi.org/aq/observation/zipCode/current?format=application/json&zipCode={zip_code}&api_key=9D84A88F-45A7-4474-B25B-085A67CED6E6"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        return data[0]['AQI']
    else:
        print(f"Error occurred. Status code: {response.status_code}")
        return None
    """
    try:
        response = requests.get('https://www.nps.gov/featurecontent/ard/currentdata/json/glac.json')
        data = response.json()['locations']
        for place in data:
            if 'West Glacier' in place['name']:
                return place['particulatesPA']['nowCastPM']['currentAQIVal']
                break
    except requests.exceptions.JSONDecodeError as j:
        print('AQI error')
        return

if __name__ == "__main__":
    print(get_air_quality())