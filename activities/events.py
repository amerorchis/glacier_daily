"""
This module retrieves and processes daily events from the National Park Service API for Glacier National Park.
"""

import os
import sys
import traceback
from datetime import date, datetime

import requests
from requests.exceptions import JSONDecodeError, ReadTimeout


def time_sortable(time: str):
    """
    Convert a time string to a datetime object that is sortable.

    Args:
        time (str): The time string in the format "%I:%M %p".

    Returns:
        datetime: A datetime object with today's date and the given time.
    """
    today = datetime.now().date()
    time_format = "%I:%M %p"
    time_obj = datetime.strptime(time, time_format).time()
    return datetime.combine(today, time_obj)


def events_today(now=date.today().strftime("%Y-%m-%d")):
    """
    Retrieve and process today's events from the National Park Service API.

    Args:
        now (str): The current date in the format '%Y-%m-%d'. Defaults to today's date.

    Returns:
        str: An HTML string containing the list of events or a message if no events are available.
    """

    def fetch_events(endpoint, headers):
        """
        Get events from endpoint
        """
        response = requests.get(endpoint, headers=headers, timeout=245)
        response.raise_for_status()
        response = response.json()
        return response["data"], int(response["total"]) // 10 + 1

    def process_event(event):
        """
        Make text clearer and more readable
        """
        deletions = [
            "Meet in front of the ",
            "Meet in front of ",
            "Meet on the shore of ",
            "Meet in the lobby of the ",
            "Meet in the ",
            "Meet at the ",
            "Meet at ",
        ]
        sortable = time_sortable(event["times"][0]["timestart"])
        start = event["times"][0]["timestart"].replace(":00", "").lower().lstrip("0")
        end = event["times"][0]["timeend"].replace(":00", "").lower().lstrip("0")
        name = (
            event["title"]
            .replace("Campground", "CG")
            .replace(" (St. Mary)", "")
            .replace(" (Apgar)", "")
        )
        loc = (
            event["location"]
            .split("(")[0]
            .split(",")[0]
            .split("<br>")[0]
            .replace("Campground", "CG")
            .replace("Visitor Center", "VC")
        )
        for deletion in deletions:
            loc = loc.replace(deletion, "")
        link = f'http://www.nps.gov/planyourvisit/event-details.htm?id={event["id"]}'
        return {
            "sortable": sortable,
            "string": f'<li style="font-size:12px; line-height:18px; color:#333333;">{start} - {end}: {name}, {loc} <a href="{link}" style="font-size:10px; color:#333333; font-style:italic; text-decoration:underline;">(link)</a></li>',
        }

    def seasonal_message(now_dt):
        """Return the correct seasonal message for a given datetime object."""
        year = now_dt.year
        if datetime(year, 9, 20, 1, 30) < now_dt < datetime(year, 12, 6, 23, 30):
            return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs have concluded for the season.</p>'
        if datetime(year, 12, 6, 1, 30) < now_dt < datetime(
            year, 12, 31, 23, 30
        ) or datetime(year, 1, 1, 1, 30) < now_dt < datetime(year, 4, 1, 1, 29):
            return ""
        if datetime(year, 4, 1, 1, 30) < now_dt < datetime(year, 6, 1, 1, 30):
            return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs not started for the season.</p>'
        return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">There are no ranger programs today.</p>'

    try:
        endpoint = f"http://developer.nps.gov/api/v1/events?parkCode=glac&dateStart={now}&dateEnd={now}"
        key = os.environ["NPS"]
        headers = {"X-Api-Key": key}

        raw_events, pages = fetch_events(endpoint, headers)
        for page in range(2, pages + 1):
            new_endpoint = f"{endpoint}&pageNumber={page}"
            new_events, _ = fetch_events(new_endpoint, headers)
            raw_events.extend(new_events)

        now_dt = datetime(*[int(i) for i in now.split("-")])
        if raw_events:
            events = [process_event(event) for event in raw_events]
            events.sort(key=lambda x: x["sortable"])
            message = '<ul style="margin:0 0 25px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
            message += "\n".join(event["string"] for event in events)
            return message + "</ul>"

        return seasonal_message(now_dt)

    except (JSONDecodeError, ReadTimeout) as e:
        print(f"Failed to retrieve events. {e}", file=sys.stderr)
        traceback.print_exc()
        now_dt = datetime(*[int(i) for i in now.split("-")])
        seasonal_message_str = seasonal_message(now_dt)
        if (
            seasonal_message_str
            != '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">There are no ranger programs today.</p>'
        ):
            return seasonal_message_str
        else:
            return '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger program schedule could not be retrieved.</p>'

    except requests.HTTPError as e:
        print(f"Failed to retrieve events. {e}", file=sys.stderr)
        traceback.print_exc()
        return "502 Response"


if __name__ == "__main__":
    # Example usage
    print(events_today())
