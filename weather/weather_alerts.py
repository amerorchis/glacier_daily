import json
from time import sleep
import requests
import re
from datetime import datetime

def handle_duplicates(alerts):
    # print(len(alerts))
    headlines = []
    to_remove = []
    for text, index in zip(alerts, range(len(alerts))):
        matches = re.match(r'(.+) issued (.*?)\sM[DS]T', text, re.DOTALL)
        if matches:
            headlines.append((
                matches.group(1),
                datetime.strptime(f'{matches.group(2)} {datetime.now().year}', "%B %d at %I:%M%p %Y"),
                text,
                index))
    
    while headlines:
        alert = headlines.pop()
        name = alert[0]
        date = alert[1]
        index = alert[3]

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

    to_remove = list(set(to_remove))
    to_remove.sort()
    while to_remove:
        index = to_remove.pop()
        alerts.pop(index)
    
    return alerts


def weather_alerts():
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
        try:
            alert_text = handle_duplicates(alert_text)
        except:
            pass

        message = '<p style="font-size:14px; line-height:22px; font-weight:bold; color:#333333; margin:0 0 5px;"><a href="weather.gov" style="color:#6c7e44; text-decoration:none;">Alert from the National Weather Service</a></p>'
        message += '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
        
        if len(alert_text) > 1:
            message = message.replace('Alert', 'Alerts')

        for i in alert_text:
            message += f"<li>{i}</li>\n"
        return message + "</ul>"
    else:
        return ""

if __name__ == "__main__":
    print(weather_alerts())
    # aurora alerts source: Aurora alerts at https://services.swpc.noaa.gov/json/planetary_k_index_1m.json
