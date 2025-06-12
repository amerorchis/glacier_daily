"""
Get road status from NPS and format into HTML.
"""

import json
import os
import sys
import traceback
from typing import Dict, List

import requests
import urllib3

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )  # pragma: no cover

from roads.Road import Road

urllib3.disable_warnings()


def closed_roads() -> Dict[str, Road]:
    """
    Retrieve closed road info from NPS and convert coordinates to names.
    """
    url = "https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q=\
        SELECT%20*%20FROM%20glac_road_nds%20WHERE%20status%20=%20%27closed%27"
    try:
        r = requests.get(url, verify=False, timeout=5)
    except requests.exceptions.RequestException as e:
        print(
            f"Handled error with Road Status, here is the traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        return {}
    r.raise_for_status()
    status = json.loads(r.text)

    if not status.get("features"):
        return ""

    roads_json = status["features"]

    roads = {
        "Going-to-the-Sun Road": Road("Going-to-the-Sun Road"),
        "Camas Road": Road("Camas Road"),
        "Two Medicine Road": Road("Two Medicine Road"),
        "Many Glacier Road": Road("Many Glacier Road"),
        "Bowman Lake Road": Road("Bowman Lake Road"),
        "Kintla Road": Road("Kintla Road", "NS"),
        "Cut Bank Creek Road": Road("Cut Bank Road"),
    }

    for i in roads_json:
        # Fix the weird way Two Med is shown sometimes
        road_name = i["properties"]["rdname"].replace("to Running Eagle", "Road")
        coordinates = (
            i["geometry"]["coordinates"]
            if len(i["geometry"]["coordinates"]) > 1
            else i["geometry"]["coordinates"][0]
        )

        x = {
            "status": i["properties"]["status"],
            "reason": i["properties"]["reason"],
            "start": coordinates[0],
            "last": coordinates[-1],
            "length": len(coordinates),
        }

        if road_name in roads:
            roads[road_name].set_coord(x["start"])
            roads[road_name].set_coord(x["last"])
        elif (
            road_name == "Inside North Fork Road"
        ):  # Handle weird naming for Kintla Road
            if x["start"][1] > 48.787:
                roads["Kintla Road"].set_coord(x["start"])
            if x["last"][1] > 48.787:
                roads["Kintla Road"].set_coord(x["last"])

    # Return dictionary of roads that have a closure found.
    return {key: value for (key, value) in roads.items() if value}


def format_road_closures(roads: List[Road]) -> str:
    """
    Take list of Road objects and turn into html formatted string.
    """
    entirely_closed = []
    statuses = []
    for _, road in roads.items():
        road.closure_string()

        if road.entirely_closed:
            entirely_closed.append(road.name)

        # Don't include if start and stop is same location.
        elif not (road.orientation == "EW" and (road.east_loc == road.west_loc)):
            statuses.append(str(road))

    if len(entirely_closed) > 1:
        entirely_closed[-1] = f"and {entirely_closed[-1]}"

        statuses.append(f'{", ".join(entirely_closed)} are closed in their entirety.')

    elif len(entirely_closed) == 1:
        statuses.append(f"{entirely_closed[0]} is closed in its entirety.")

    if statuses:
        message = (
            '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px;'
            'line-height:18px; color:#333333;">\n'
        )
        for i in statuses:
            message += f"<li>{i}</li>\n"
        return message + "</ul>"

    return (
        '<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">'
        "There are no closures on major roads today!</p>"
    )


def get_road_status() -> str:
    """
    Wrap the closed roads function to catch errors and allow email to send if there is an issue.
    """
    try:
        return format_road_closures(closed_roads())
    except requests.exceptions.HTTPError:
        print(
            f"Handled error with Road Status, here is the traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        return ""


if __name__ == "__main__":  # pragma: no cover
    print(get_road_status())
