"""
This module retrieves and processes daily events from the National Park Service API for Glacier National Park.
"""

from datetime import datetime

import requests
from requests.exceptions import JSONDecodeError

from shared.data_types import Event, EventsResult
from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger
from shared.retry import retry
from shared.settings import get_settings

logger = get_logger(__name__)

NPS_EVENTS_PAGE_SIZE = 10


def time_sortable(time: str):
    """
    Convert a time string to a datetime object that is sortable.

    Args:
        time (str): The time string in the format "%I:%M %p".

    Returns:
        datetime: A datetime object with today's date and the given time.
    """
    today = now_mountain().date()
    time_format = "%I:%M %p"
    time_obj = datetime.strptime(time, time_format).time()
    return datetime.combine(today, time_obj)


@retry(3, (requests.exceptions.RequestException,), default=None, backoff=5)
def fetch_events(endpoint, headers):
    """Get events from endpoint."""
    response = requests.get(endpoint, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data["data"], int(data["total"]) // NPS_EVENTS_PAGE_SIZE + 1


def events_today(now=None) -> EventsResult:
    """
    Retrieve and process today's events from the National Park Service API.

    Args:
        now (str): The current date in the format '%Y-%m-%d'. Defaults to today's date.

    Returns:
        EventsResult: Structured events data.
    """

    def process_event(event):
        """
        Extract structured event data.
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
        if "Native America Speaks - " in name:
            name = name.split(" - ")[0]
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
        link = f"http://www.nps.gov/planyourvisit/event-details.htm?id={event['id']}"
        return Event(
            start_time=start,
            end_time=end,
            name=name,
            location=loc,
            link=link,
            sortable=sortable,
        )

    def seasonal_message(now_dt) -> str:
        """Return the correct seasonal message for a given datetime object."""
        year = now_dt.year
        if datetime(year, 9, 20, 1, 30) < now_dt < datetime(year, 12, 6, 23, 30):
            return "Ranger programs have concluded for the season."
        if datetime(year, 12, 6, 1, 30) < now_dt < datetime(
            year, 12, 31, 23, 30
        ) or datetime(year, 1, 1, 1, 30) < now_dt < datetime(year, 4, 1, 1, 29):
            return ""
        if datetime(year, 4, 1, 1, 30) < now_dt < datetime(year, 6, 1, 1, 30):
            return "Ranger programs not started for the season."
        return "There are no ranger programs today."

    if now is None:
        now = now_mountain().strftime("%Y-%m-%d")

    def _handle_fetch_failure() -> EventsResult:
        year, month, day = (int(i) for i in now.split("-"))
        now_dt = datetime(year, month, day)
        msg = seasonal_message(now_dt)
        if msg != "There are no ranger programs today.":
            return EventsResult(seasonal_message=msg)
        return EventsResult(
            error_message="Ranger program schedule could not be retrieved."
        )

    try:
        endpoint = f"http://developer.nps.gov/api/v1/events?parkCode=glac&dateStart={now}&dateEnd={now}"
        headers = {"X-Api-Key": get_settings().NPS}

        result = fetch_events(endpoint, headers)
        if result is None:
            return _handle_fetch_failure()

        raw_events, pages = result
        for page in range(2, pages + 1):
            new_endpoint = f"{endpoint}&pageNumber={page}"
            page_result = fetch_events(new_endpoint, headers)
            if page_result is not None:
                new_events, _ = page_result
                raw_events.extend(new_events)

        year, month, day = (int(i) for i in now.split("-"))
        now_dt = datetime(year, month, day)
        if raw_events:
            events = [process_event(event) for event in raw_events]
            events.sort(key=lambda x: x.sortable)
            return EventsResult(events=events)

        msg = seasonal_message(now_dt)
        return EventsResult(seasonal_message=msg)

    except (requests.exceptions.RequestException, JSONDecodeError) as e:
        logger.error("Failed to retrieve events: %s", e)
        return _handle_fetch_failure()


if __name__ == "__main__":
    # Example usage
    print(events_today())
