"""
This module retrieves information about GNPC events by scraping the GNPC website.
"""

import os
import sys
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )  # pragma: no cover

from activities.gnpc_datetime import convert_gnpc_datetimes, datetime_to_string


class GNPCError(Exception):
    """Base exception for GNPC-related errors"""

    pass


class GNPCRequestError(GNPCError):
    """Raised when there's an error making requests to GNPC website"""

    pass


class GNPCParsingError(GNPCError):
    """Raised when there's an error parsing GNPC website content"""

    pass


def scrape_events_page(url: str, event_type: str) -> List[Dict[str, str]]:
    """
    Scrape events from a specific GNPC page.

    Args:
        url: The URL to scrape
        event_type: Type of event (Glacier Conversation or Book Club)

    Returns:
        List of event dictionaries

    Raises:
        GNPCRequestError: If there's an error accessing the website
        GNPCParsingError: If there's an error parsing the content
    """
    try:
        headers = {"User-Agent": "GNPC-API"}
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
    except RequestException as e:
        raise GNPCRequestError(f"Failed to access {url}: {str(e)}")

    try:
        soup = BeautifulSoup(r.content, "html.parser")
        rows = soup.find_all("div", "et_pb_row")
        rows = [row for row in rows if row.find("h4")]

        events = []
        for row in rows:
            try:
                # Get title
                h4 = row.find("h4")
                if not h4:
                    continue
                title = f"{event_type} {h4.text}"

                # Get picture URL
                thumb = row.find("div", "thumbs")
                img = row.find("img")
                if thumb:
                    pic = thumb.get_text()
                elif img and img.get("src"):
                    pic = img["src"]
                else:
                    pic = ""  # Default empty string if no image found

                # Get paragraphs
                paragraphs = row.find_all("p")
                if not paragraphs:
                    continue

                paragraphs = [p.text for p in paragraphs][:-1]
                if not paragraphs or ":" not in paragraphs[0]:
                    continue

                # Get link
                div_id = row.get("id")
                div_link = f"#{div_id}" if div_id else ""

                events.append(
                    {
                        "title": title,
                        "pic": pic,
                        "datetime": paragraphs[0],
                        "description": "\n".join(paragraphs[1:]).replace("\xa0", " "),
                        "registration": f"{url}{div_link}",
                    }
                )
            except (AttributeError, IndexError, KeyError) as e:
                # Log error but continue processing other events
                print(f"Error parsing event: {str(e)}")
                continue

        return events
    except Exception as e:
        raise GNPCParsingError(f"Failed to parse content from {url}: {str(e)}")


def get_gnpc_events() -> List[Dict[str, str]]:
    """
    Gather information about upcoming Glacier Conversations and Glacier Book Club.

    Returns:
        List of dictionaries containing event information.

    Raises:
        GNPCError: If there's an error fetching or parsing events
    """
    events = []
    event_types = {
        "glacier-conversations": "Glacier Conversation:",
        "glacier-book-club": "Glacier Book Club:",
    }

    for event_path, event_type in event_types.items():
        try:
            url = f"https://glacier.org/{event_path}"
            page_events = scrape_events_page(url, event_type)
            events.extend(page_events)
        except GNPCError as e:
            print(f"Error processing {event_path}: {str(e)}")
            continue

    if not events:
        return []

    try:
        # Convert times to datetime objects
        for event in events:
            event["datetime"] = convert_gnpc_datetimes(event["datetime"])

        # Sort events by datetime
        events = sorted(events, key=lambda x: x["datetime"])

        # Convert back to formatted strings
        for event in events:
            event["datetime"] = datetime_to_string(event["datetime"])

        return events
    except Exception as e:
        raise GNPCError(f"Error processing event dates: {str(e)}")
