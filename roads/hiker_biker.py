"""
Retrieve and format the hiker/biker status.
"""

import json
import sys
import traceback
import requests
import urllib3

try:
    from roads.HikerBiker import HikerBiker
    from roads.roads import closed_roads
except ModuleNotFoundError:
    from roads import closed_roads
    from HikerBiker import HikerBiker
urllib3.disable_warnings()

def hiker_biker():
    """"
    Retrieve and format hiker biker closure locations.
    """
    # Find GTSR road closure info.
    gtsr = closed_roads().get('Going-to-the-Sun Road', '')

    url = "https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q="\
        "SELECT%20*%20FROM%20glac_hiker_biker_closures%20WHERE%20status%20=%20%27active%27"
    r = requests.get(url, verify=False, timeout=5)
    r.raise_for_status()
    data = json.loads(r.text).get('features', '')

    # If there is no hiker/biker info or no GTSR closure return empty string.
    if not data or not gtsr:
        return ''

    statuses = []
    for i in data:
        # Clean up naming conventions.
        closure_type = i['properties']['name']\
        .replace('Hazard Closure', 'Hazard Closure (in effect at all times):')\
        .replace('Road Crew Closure', 'Road Crew Closure (in effect during work hours):')\
        .replace('Hiker/Biker ', '')

        # If there are coordinates, generate a string with the name of the closure location.
        if i['geometry']:
            coord = tuple(i['geometry']['coordinates'])
            statuses.append(f"{closure_type} {HikerBiker(closure_type, coord, gtsr)}")

        # Otherwise note that none are listed.
        else:
            statuses.append(f'{closure_type} None listed')

    # Return empty string if there are no hiker biker restrictions listed.
    if not statuses or all('None listed' in item for item in statuses):
        return ''

    # Generate HTML for this section of the email.
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
    except requests.exceptions.HTTPError:
        print(traceback.format_exc(), file=sys.stderr)
        return ''

if __name__ == "__main__":
    print(get_hiker_biker_status())
