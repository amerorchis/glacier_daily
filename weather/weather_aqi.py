import requests

def get_air_quality():

    try:
        response = requests.get('https://www.nps.gov/featurecontent/ard/currentdata/json/glac.json')
        data = response.json()['locations']
        for place in data:
            if 'West Glacier' in place['name']:
                return place['particulatesPA']['nowCastPM']['currentAQIVal']
        
        return
                
    except requests.exceptions.JSONDecodeError as j:
        print('AQI error')
        return

if __name__ == "__main__":
    print(get_air_quality())