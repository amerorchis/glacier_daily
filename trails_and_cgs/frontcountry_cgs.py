"""
This module fetches and processes the status of front country campgrounds in Glacier National Park.
It retrieves data from the NPS API, processes it to identify closures and alerts, and formats the information for display.
"""

import json
import sys
import traceback

import certifi
import requests

from shared.datetime_utils import now_mountain


def campground_alerts():
    """
    Fetches the status of front country campgrounds from the NPS API and processes the data to identify closures and alerts.

    Returns:
        str: A formatted HTML string containing the status of campgrounds, or an error message if the data is unavailable.
    """
    url = "https://carto.nps.gov/user/glaclive/api/v2/sql?format=JSON&q=SELECT%20*%20FROM%20glac_front_country_campgrounds"
    try:
        r = requests.get(url, timeout=10, verify=certifi.where())
    except requests.exceptions.RequestException:
        print(
            f"Handled error with Campground Status, here is the traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        return "The campgrounds page on the park website is currently down."

    try:
        status = json.loads(r.text)
    except json.JSONDecodeError:
        print(
            f"Handled error with Campground Status JSON decode, here is the traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        return "The campgrounds page on the park website is currently down."

    try:
        campgrounds = status["rows"]
    except KeyError:
        return "The campgrounds page on the park website is currently down."

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

    if statuses:
        message = '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
        for i in statuses:
            message += f"<li>{i}</li>\n"
        return message + "</ul>"
    else:
        return ""


def get_campground_status() -> str:
    """
    Wrap the closed campgrounds function to catch errors and allow email to send if there is an issue.

    Returns:
        str: The status of campgrounds or an empty string if an error occurs.
    """
    try:
        return campground_alerts()
    except requests.exceptions.HTTPError:
        print(
            f"Handled error with Campground Status, here is the traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        return ""


if __name__ == "__main__":  # pragma: no cover
    print(get_campground_status())
