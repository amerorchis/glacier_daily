import sys
from datetime import datetime, date
import requests
from requests.exceptions import JSONDecodeError, ReadTimeout
import os

def time_sortable(time: str):
    today = datetime.now().date()
    time_format = "%I:%M %p"
    time_obj = datetime.strptime(time, time_format).time()
    return datetime.combine(today, time_obj)

def events_today(now = date.today().strftime('%Y-%m-%d')):
    try:
        # Create the request
        endpoint = f"https://developer.nps.gov/api/v1/events?parkCode=glac&dateStart={now}&dateEnd={now}"

        # Add authentication request
        key = os.environ['NPS']
        HEADERS = {"X-Api-Key":key}

        # Get response from API
        r = requests.get(endpoint,headers=HEADERS, timeout=245)
        response = r.json()
        raw_events = response['data']
        pages = int(response['total']) // 10 + 1
        year = datetime.now().year

        if pages > 1:
            for i in range(2, pages+1):
                new_endpoint = endpoint + f"&pageNumber={i}"
                r = requests.get(new_endpoint, headers=HEADERS)
                raw_events.extend(r.json()['data'])

        now = datetime.now()
        if raw_events:
            events = []
            for i in range(len(raw_events)):
                e = raw_events[i]
                sortable = time_sortable(e["times"][0]["timestart"])
                start = e["times"][0]["timestart"].replace(' ','').replace(':00','').lower()
                start = start[1:] if start[0] == '0' else start
                end = e["times"][0]["timeend"].replace(' ','').replace(':00','').lower()
                end = end[1:] if end[0] == '0' else end
                name = e["title"].replace('Campground', 'CG').replace(' (St. Mary)','').replace(' (Apgar)','')
                loc = e["location"].split("(")[0].split(",")[0].split('<br>')[0].replace('Campground', 'CG').replace('Visitor Center', 'VC')
                deletions = ['Meet in front of the ', 'Meet in front of ', 'Meet on the shore of ','Meet in the lobby of the ', 'Meet in the ', 'Meet at the ', 'Meet at ']
                for i in deletions:
                    loc = loc.replace(i, '')
                link = f'https://www.nps.gov/planyourvisit/event-details.htm?id={e["id"]}'
                events.append({'sortable':sortable, 'string':f'<li>{start}-{end}: {name}, {loc} <a href="{link}" style="font-size:10px; color:#333333; font-style: italic; text-decoration: underline;">(link)</a></li>'})

            events.sort(key=lambda x: x["sortable"])
            message = '<ul style="margin:0 0 25px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
            for i in events:
                message += f"{i['string']}\n"
            return message + '</ul>'

        elif datetime(year, 9, 20, 1, 30) < now < datetime(year, 12, 6, 23, 30):
            return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs have concluded for the season.</p>'

        elif datetime(year, 12, 6, 1, 30) < now < datetime(year, 12, 31, 23, 30) or datetime(1, 1, 1, 1, 30)< datetime(1, 4, 1, 1, 30):
            return ''

        elif datetime(year, 4, 1, 1, 30) < now < datetime(year, 6, 1, 1, 30):
            return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs not started for the season.</p>'

        else:
            return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">There are no ranger programs today.</p>'

    except (JSONDecodeError, ReadTimeout) as e:
        print(f'Failed retrieve events. {e}', file=sys.stderr)
        return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger program schedule could not be retrieved.</p>'

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("email.env")
    print(events_today())
