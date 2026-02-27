"""
Retrieve the hiker/biker status.
"""

import contextlib
import json

import requests
import urllib3

from roads.hiker_biker_closure import HikerBiker
from roads.roads import NPSWebsiteError, closed_roads
from shared.data_types import HikerBikerResult
from shared.logging_config import get_logger

logger = get_logger(__name__)

# The NPS carto.nps.gov GeoJSON API uses a certificate chain that fails
# validation. SSL verification is disabled for these endpoints.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def hiker_biker() -> HikerBikerResult:
    """
    Retrieve hiker biker closure locations.
    """
    try:
        # Find GTSR road closure info.
        closures = closed_roads()
        gtsr = closures.get("Going-to-the-Sun Road", "")

        urls = [
            "https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q="
            "SELECT%20*%20FROM%20glac_hiker_biker_closures%20WHERE%20status%20=%20%27active%27",
            "https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q="
            "SELECT%20*%20FROM%20winter_rec_closure%20WHERE%20status%20=%20%27active%27",
        ]

        data = []

        for url in urls:
            try:
                r = requests.get(url, timeout=5, verify=False)  # noqa: S501
            except requests.exceptions.RequestException:
                logger.error("Hiker/biker status request failed", exc_info=True)
                continue
            r.raise_for_status()
            data.extend(json.loads(r.text).get("features", ""))

        # If there is no hiker/biker info or no GTSR closure return empty result.
        if not data or not gtsr:
            return HikerBikerResult()

        # Make sure this is the right type of closure.
        data = [
            j
            for j in data
            if (
                "Hazard" in j["properties"]["name"]
                or "Road Crew" in j["properties"]["name"]
                or "Avalanche" in j["properties"]["name"]
            )
        ]

        statuses = []
        for i in data:
            # Clean up naming conventions.
            closure_type = (
                i["properties"]["name"]
                .replace("Hazard Closure", "Hazard Closure:")
                .replace("Road Crew Closure", "Road Crew Closure:")
                .replace("Hiker/Biker ", "")
            )

            # If there are coordinates, generate a string with the name of the closure location.
            if i["geometry"]:
                coord = tuple(i["geometry"]["coordinates"])
                statuses.append(
                    f"{closure_type} {HikerBiker(closure_type, coord, gtsr)}"
                )

            # Otherwise pass.
            else:
                continue

        # Return empty result if there are no hiker biker restrictions listed.
        if not statuses or all("None listed" in item for item in statuses):
            return HikerBikerResult()

        # Sort by side (term between : and -)
        with contextlib.suppress(IndexError):
            statuses.sort(key=lambda x: x.split(":")[1].split("-")[0], reverse=True)

        return HikerBikerResult(
            closures=statuses,
            explanatory_note=(
                "Road Crew Closures are in effect during work hours, "
                "Avalanche Hazard Closures are in effect at all times."
            ),
        )
    except (requests.exceptions.HTTPError, NPSWebsiteError):
        return HikerBikerResult()


def get_hiker_biker_status() -> HikerBikerResult:
    """
    Wrap the hiker biker function to catch errors and allow email to send if there is an issue.
    """
    try:
        return hiker_biker()
    except (
        requests.exceptions.RequestException,
        KeyError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        NPSWebsiteError,
    ):
        logger.error("Hiker/biker status error", exc_info=True)
        return HikerBikerResult()


if __name__ == "__main__":  # pragma: no cover
    print(get_hiker_biker_status())
