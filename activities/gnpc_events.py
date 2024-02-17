import requests
from bs4 import BeautifulSoup
# import json

try:
    from gnpc_datetime import convert_gnpc_datetimes, datetime_to_string
except ModuleNotFoundError:
    from activities.gnpc_datetime import convert_gnpc_datetimes, datetime_to_string

def scrape_events_from_web():
    events = []

    for event in ['glacier-conversations', 'glacier-book-club']:
        url = f'https://glacier.org/{event}'
        headers = {'User-Agent': 'GNPC-API'}
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            return ''
        
        soup = BeautifulSoup(r.content, 'html.parser')
        rows = soup.find_all('div','et_pb_row')

        rows = [row for row in rows if row.find('h4')]

        event_type = 'Glacier Conversation:' if event == 'glacier-conversations' else 'Glacier Book Club:'
        for i in rows:
            title = f'{event_type} {i.find("h4").text}'
            pic = i.find('img')['src']
            paragraphs = i.find_all('p')
    
            paragraphs = [p.text for p in paragraphs][:-1]

            # Check if event has a time listed, which means it hasn't happened.
            if ':' in paragraphs[0]:
                events.append({
                    'title': title,
                    'pic': pic,
                    'datetime': paragraphs[0],
                    'description': '\n'.join(paragraphs[1:]).replace('\xa0',' '),
                    'registration': f'https://glacier.org/{event}/'
                })

    return events

def get_gnpc_events():
    events = scrape_events_from_web()

    # Convert time to dt object
    for i in events:
        i['datetime'] = convert_gnpc_datetimes(i['datetime'])

    # Sort in order
    events = sorted(events, key=lambda x: x['datetime'])

    # Convert back to nice string
    for i in events:
        i['datetime'] = datetime_to_string(i['datetime'])

    """with open('activities/gnpc.json', 'w') as json_file:
        json.dump(events, json_file, indent=4)"""

    return events

if __name__ == "__main__":
    print(get_gnpc_events())
