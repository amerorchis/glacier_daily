"""
This module fetches and processes the status of front country campgrounds in Glacier National Park.
It retrieves data from the NPS API, processes it to identify closures and alerts.
"""

import json

import requests
import urllib3

from shared.data_types import CampgroundsResult
from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger

logger = get_logger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def campground_alerts() -> CampgroundsResult:
    """
    Fetches the status of front country campgrounds from the NPS API and processes the data to identify closures and alerts.

    Returns:
        CampgroundsResult: Structured campground status data.
    """
    url = "https://carto.nps.gov/user/glaclive/api/v2/sql?format=JSON&q=SELECT%20*%20FROM%20glac_front_country_campgrounds"
    try:
        r = requests.get(url, timeout=10, verify=False)  # noqa: S501
    except requests.exceptions.RequestException:
        logger.error("Campground status request failed", exc_info=True)
        return CampgroundsResult(
            error_message="The campgrounds page on the park website is currently down."
        )

    try:
        status = json.loads(r.text)
    except json.JSONDecodeError:
        logger.error("Campground status JSON decode error", exc_info=True)
        return CampgroundsResult(
            error_message="The campgrounds page on the park website is currently down."
        )

    try:
        campgrounds = status["rows"]
    except KeyError:
        return CampgroundsResult(
            error_message="The campgrounds page on the park website is currently down."
        )

    closures = []
    season_closures = []
    statuses = []

    for i in campgrounds:
        name = i["name"].replace("  ", " ")

        if i["status"] == "closed":
            if "season" in i["service_status"]:
                season_closures.append(name)
            else:
                closures.append(f"{name} CG: currently closed.")

        notice = (
            f"{i['description']}"
            if i["description"]
            and (
                "camping only" in i["description"].lower()
                or "posted" in i["description"].lower()
            )
            else None
        )
        if notice:
            notice = notice.replace(
                ' <br><br><a href="https://www.nps.gov/glac/planyourvisit/reservation-campgrounds.htm" target="_blank">Campground Details</a><br><br>',
                "",
            )
            notice = notice.replace("<b>", "").replace("</b>", "")
            notice = ". ".join(i.capitalize() for i in notice.split(". "))
            notice = f"{name} CG: {notice}"
            statuses.append(notice)

    statuses, closures, season_closures = (
        set(statuses),
        set(closures),
        set(season_closures),
    )  # remove duplicates
    statuses, closures, season_closures = (
        sorted(list(statuses)),
        sorted(list(closures)),
        sorted(list(season_closures)),
    )  # turn back into a list and sort
    statuses.extend(closures)

    if season_closures:
        seasonal = (
            [f"Closed for the season: {', '.join(season_closures)}"]
            if now_mountain().month >= 8
            else [f"Not yet open for the season: {', '.join(season_closures)}"]
        )
        statuses.extend(seasonal)

    return CampgroundsResult(statuses=statuses)


def get_campground_status() -> CampgroundsResult:
    """
    Wrap the closed campgrounds function to catch errors and allow email to send if there is an issue.

    Returns:
        CampgroundsResult: Structured campground status data, or empty result on error.
    """
    try:
        return campground_alerts()
    except requests.exceptions.HTTPError:
        logger.error("Campground status HTTP error", exc_info=True)
        return CampgroundsResult()


if __name__ == "__main__":  # pragma: no cover
    print(get_campground_status())
