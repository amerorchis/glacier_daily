"""
This module retrieves information about GNPC events by scraping the GNPC website.
"""

from typing import List, Dict
import requests
from bs4 import BeautifulSoup

try:
    from gnpc_datetime import convert_gnpc_datetimes, datetime_to_string
except ModuleNotFoundError:
    from activities.gnpc_datetime import convert_gnpc_datetimes, datetime_to_string

def get_gnpc_events() -> List[Dict[str, str]]:
    """
    Gather information about upcoming Glacier Conversations and Glacier Book Club then format as 
    list of dicts for json use.
    :return list of dictionaries.
    """
    events = []

    for event in ['glacier-conversations', 'glacier-book-club']:

        # Get data from GNPC website and make BeautifulSoup object
        url = f'https://glacier.org/{event}'
        headers = {'User-Agent': 'GNPC-API'}
        r = requests.get(url, headers=headers, timeout=12)

        if r.status_code != 200:
            return ''

        soup = BeautifulSoup(r.content, 'html.parser')

        # et_pb_row elements with an h4 element will be individual events.
        rows = soup.find_all('div','et_pb_row')
        rows = [row for row in rows if row.find('h4')]

        event_type = 'Glacier Conversation:' if event == 'glacier-conversations'\
        else 'Glacier Book Club:'

        # Extract the information needed for emails from each div.
        for i in rows:
            title = f'{event_type} {i.find("h4").text}'
            thumb = i.find('div', 'thumbs') # Thumbnail links are stored in a hidden div within each event.
            pic = thumb.get_text() if thumb else i.find('img')['src']
            paragraphs = i.find_all('p')
            paragraphs = [p.text for p in paragraphs][:-1]

            # If a div has an id, we can give a link that auto scrolls down to that event.
            div_id = i.get('id')
            div_link = f'#{div_id}' if div_id else ''

            # Check if event has a time listed, which means it hasn't happened yet.
            if ':' in paragraphs[0]:
                events.append({
                    'title': title,
                    'pic': pic,
                    'datetime': paragraphs[0],
                    'description': '\n'.join(paragraphs[1:]).replace('\xa0',' '),
                    'registration': f'https://glacier.org/{event}/{div_link}'
                })

    # Convert time to dt object
    for i in events:
        i['datetime'] = convert_gnpc_datetimes(i['datetime'])

    # Sort in order
    events = sorted(events, key=lambda x: x['datetime'])

    # Convert back to nice string
    for i in events:
        i['datetime'] = datetime_to_string(i['datetime'])

    return events

if __name__ == "__main__":
    print(get_gnpc_events())
