"""
This module fetches and processes weather alerts from the National Weather Service for Glacier National Park.
"""

import json
from time import sleep
import requests
import re
from datetime import datetime, timedelta
from typing import List, Dict

def handle_duplicates(alerts: List[str]) -> List[str]:
    """
    Remove duplicate alerts, keeping only the latest issued alert for each type.
    
    Args:
        alerts (List[str]): List of alert strings.
    
    Returns:
        List[str]: List of unique alert strings.
    """
    # print(len(alerts))
    headlines = []
    to_remove = []
    for text, index in zip(alerts, range(len(alerts))):
        matches = re.match(r'(.+) issued (.*?)\sM[DS]T', text, re.DOTALL)
        if matches:
            headlines.append((
                matches.group(1), # Type of alert
                datetime.strptime(f'{matches.group(2)} {datetime.now().year}', "%B %d at %I:%M%p %Y"), # Time issued
                text, # Content of alert
                index)) # Index in list
    
    while headlines:
        alert = headlines.pop()
        name = alert[0]
        date = alert[1]
        index = alert[3]

        # For each headline, check against other headlines for the same type of alert and keep only the later issued one.
        for i in headlines:
            check_name = i[0]
            check_date = i[1]
            check_index = i[3]
            if check_name == name:
                if check_date < date:
                    to_remove.append(check_index)
                    # print(f'Deleting {check_name} at {check_date}')
                elif check_date > date:
                    to_remove.append(index)
                    # print(f'Deleting {name} at {date}')

    # Remove each item that is duplicate
    to_remove = list(set(to_remove))
    to_remove.sort()
    while to_remove:
        index = to_remove.pop()
        alerts.pop(index)
    
    return alerts


def weather_alerts() -> str:
    """
    Fetch and format weather alerts for Glacier National Park.
    
    Returns:
        str: Formatted weather alerts as HTML string.
    """
    zones = ['https://api.weather.gov/zones/forecast/MTZ301',
             'https://api.weather.gov/zones/forecast/MTZ302',
             'https://api.weather.gov/zones/county/MTC029',
             'https://api.weather.gov/zones/county/MTC035',
             'https://api.weather.gov/zones/forecast/MTZ002',
             'https://api.weather.gov/zones/forecast/MTZ003',
             'https://api.weather.gov/zones/fire/MTZ105']

    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(f'https://api.weather.gov/alerts/active/area/MT', headers=headers)

    retries = 0
    while r.status_code != 200 and retries < 10:
        print(f'Weather error for alerts: status code {r.status_code}')
        r = requests.get(f'https://api.weather.gov/alerts/active/area/MT', headers=headers)
        retries += 1
        sleep(3)

    alerts = json.loads(r.content)['features']
    a = True
    affected_zones = [i['properties']['affectedZones'] for i in alerts]
    
    local_alerts = []
    for i in range(len(alerts)):
        for zone in zones:
            if zone in affected_zones[i] and alerts[i]['properties'] not in local_alerts:
                local_alerts.append(alerts[i]['properties'])

    alert_text = [f'{i["headline"]}: {i["description"]}'.replace(r'\n','') for i in local_alerts]

    if alert_text:
        # !!! Temporary measure to limit length of this section. Deal with permanently later.
        if len(alert_text) > 2:
            alert_text = alert_text[:2]

        try:
            alert_text = handle_duplicates(alert_text)
            message = '<p style="font-size:14px; line-height:22px; font-weight:bold; color:#333333; margin:0 0 5px;"><a href="https://weather.gov" style="color:#6c7e44; text-decoration:none;">Alert from the National Weather Service</a></p>'
            message += '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
            
            if len(alert_text) > 1:
                message = message.replace('Alert', 'Alerts')

            for i in alert_text:
                message += f"<li>{i}</li>\n"
            return message + "</ul>"
        
        except Exception as e:
            print(e)
            pass

    return ""

if __name__ == "__main__":
    print(weather_alerts())
