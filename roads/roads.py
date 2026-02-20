"""
Get road status from NPS and format into HTML.
"""

import json
import sys
import traceback

import requests

from roads.Road import Road


class NPSWebsiteError(Exception):
    """
    Custom exception for NPS website errors.
    """

    pass


def _get_segment_bounds(coordinates: list) -> tuple[float, float]:
    """
    Extract the west and east longitude bounds from a list of coordinates.

    Returns:
        tuple of (west_lon, east_lon)
    """
    # Flatten nested arrays if needed
    flat = []
    for c in coordinates:
        if isinstance(c[0], list):
            flat.extend(c)
        else:
            flat.append(c)

    lons = [c[0] for c in flat]
    return (min(lons), max(lons))


def _segments_overlap(seg1: tuple[float, float], seg2: tuple[float, float]) -> bool:
    """
    Check if two segments (defined by west/east longitude bounds) overlap.

    Segments that only share an endpoint are NOT considered overlapping.
    This ensures that when a closed segment ends exactly where an open segment
    begins, we still report the closure endpoint correctly.

    Args:
        seg1: (west_lon, east_lon) for first segment
        seg2: (west_lon, east_lon) for second segment

    Returns:
        True if segments overlap (not just touch at an endpoint)
    """
    return seg1[0] < seg2[1] and seg2[0] < seg1[1]


def _fetch_open_segments(road_name: str) -> set[tuple[float, float]]:
    """
    Fetch open road segments for a specific road from NPS API.

    Args:
        road_name: Name of the road to query

    Returns:
        set of (west_lon, east_lon) tuples for open segments
    """
    # URL-encode the road name for the query
    encoded_name = road_name.replace(" ", "%20").replace("-", "%2D")
    url = (
        "https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q="
        f"SELECT%20*%20FROM%20glac_road_nds%20WHERE%20status%20=%20%27open%27"
        f"%20AND%20rdname%20LIKE%20%27%25{encoded_name}%25%27"
    )

    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = json.loads(r.text)
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        # If we can't fetch open segments, return empty set (fail-safe)
        return set()

    open_segments = set()
    for feature in data.get("features", []):
        coords = feature.get("geometry", {}).get("coordinates", [])
        if coords:
            bounds = _get_segment_bounds(coords)
            open_segments.add(bounds)

    return open_segments


def _is_covered_by_open(
    closed_bounds: tuple[float, float], open_segments: set[tuple[float, float]]
) -> bool:
    """
    Check if a closed segment overlaps with any open segment.

    When a segment is marked both open and closed, we default to open
    (the road is actually passable in that section).

    Args:
        closed_bounds: (west_lon, east_lon) for the closed segment
        open_segments: set of (west_lon, east_lon) for open segments

    Returns:
        True if the closed segment overlaps with an open segment
    """
    for open_bounds in open_segments:
        if _segments_overlap(closed_bounds, open_bounds):
            return True
    return False


def closed_roads() -> dict[str, Road]:
    """
    Retrieve closed road info from NPS and convert coordinates to names.

    Note: The NPS API sometimes has overlapping segments marked both 'open' and
    'closed' for the same section of road. When this occurs, we default to 'open'
    since the road is actually passable in that section.
    """
    url = "https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q=\
        SELECT%20*%20FROM%20glac_road_nds%20WHERE%20status%20=%20%27closed%27"
    try:
        r = requests.get(url, timeout=5)
    except requests.exceptions.RequestException as e:
        print(
            f"Handled error with Road Status, here is the traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        raise NPSWebsiteError from e
    r.raise_for_status()
    status = json.loads(r.text)

    if not status.get("features"):
        return ""

    roads_json = status["features"]

    # Fetch open segments for GTSR to detect overlapping open/closed segments
    gtsr_open_segments = _fetch_open_segments("Going-to-the-Sun")

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

        # Normalize Cut Bank Creek Road variants (e.g., "Cut Bank Creek Road: Boundary to RS")
        if road_name.startswith("Cut Bank Creek Road"):
            road_name = "Cut Bank Creek Road"
        coordinates = (
            i["geometry"]["coordinates"]
            if len(i["geometry"]["coordinates"]) > 1
            else i["geometry"]["coordinates"][0]
        )

        # For GTSR, check if this closed segment overlaps with an open segment
        # If so, skip it (default to open when there's conflicting data)
        if road_name == "Going-to-the-Sun Road" and gtsr_open_segments:
            closed_bounds = _get_segment_bounds(coordinates)
            if _is_covered_by_open(closed_bounds, gtsr_open_segments):
                continue  # Skip this closed segment - it's marked open elsewhere

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


def format_road_closures(roads: list[Road]) -> str:
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
    except NPSWebsiteError:
        print(
            f"Handled error with NPS website, here is the traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        return (
            '<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">'
            "The road status page on the park website is currently down.</p>"
        )


if __name__ == "__main__":  # pragma: no cover
    print(get_road_status())
