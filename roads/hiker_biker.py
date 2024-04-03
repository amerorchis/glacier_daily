"""
Retrieve and format the hiker/biker status.
"""

import json
import requests
import urllib3

try:
    from roads.HikerBiker import HikerBiker
except ModuleNotFoundError:
    from HikerBiker import HikerBiker
urllib3.disable_warnings()

def hiker_biker():
    """"
    Retrieve and format hiker biker closure locations.
    """
    url = "https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q="\
        "SELECT%20*%20FROM%20glac_hiker_biker_closures%20WHERE%20status%20=%20%27active%27"
    r = requests.get(url, verify=False, timeout=5)
    raw = json.loads(r.text)
    data = raw.get('features', '')

    if not data:
        return ''

    hb_data = dict()
    for i in data:
        coord = None
        if i['geometry']:
            coord = tuple(i['geometry']['coordinates'])

        closure_type = i['properties']['name'].replace('Hazard Closure', \
                                                       'Hazard Closure (in effect at all times):')\
        .replace('Road Crew Closure', 'Road Crew Closure (in effect during work hours):')\
        .replace('Hiker/Biker ', '')

        hb_data[closure_type] = coord

    statuses = []
    for key, item in hb_data.items():
        if item:
            statuses.append(f'{key} {HikerBiker(key, item).closure_str}')
        else:
            statuses.append(f'{key} None in effect')

    if not statuses or all('None in effect' in item for item in statuses):
        return ''

    message = '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px;'\
        'line-height:18px; color:#333333;">\n'
    for i in statuses:
        message += f"<li>{i}</li>\n"
    return message + "</ul>"


def get_hiker_biker_status() -> str:
    """
    Wrap the hiker biker function to catch errors and allow email to send if there is an issue.
    """
    try:
        return hiker_biker()
    except Exception as e:
        print(e)
        return ''

if __name__ == "__main__":
    print(hiker_biker())
