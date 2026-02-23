"""
Select a random peak, get an image of it, and return the info.
"""

import csv
import json
import random
from datetime import date
from pathlib import Path

from peak.sat import peak_sat
from shared.logging_config import get_logger
from shared.retrieve_from_json import retrieve_from_json

logger = get_logger(__name__)

SCRIPT_DIR = Path(__file__).parent
WIKIPEDIA_JSON = SCRIPT_DIR / "peaks_wikipedia.json"


def _get_peak_summary(name: str, lat: float, lon: float) -> str | None:
    """Get the Wikipedia summary for a peak if available."""
    if not WIKIPEDIA_JSON.exists():
        return None
    with open(WIKIPEDIA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    for peak_data in data.get("peaks", []):
        if (
            peak_data["name"] == name
            and abs(peak_data["lat"] - lat) < 0.001
            and abs(peak_data["lon"] - lon) < 0.001
        ):
            return peak_data.get("summary")
    return None


def peak(test=False, skip_upload: bool = False):
    """
    Select a random peak, and return the relevant information.
    """
    if test:
        logger.debug("Test mode.")

    # Check if we already have today's peak
    else:
        already_retrieved, keys = retrieve_from_json(["peak", "peak_image", "peak_map"])
        if already_retrieved:
            return keys

    with open("peak/PeaksCSV.csv", encoding="utf-8") as p:
        peaks = list(csv.DictReader(p))

    # Select a random one with current date as seed
    random.seed(date.today().strftime("%Y%m%d"))
    today = random.choice(peaks)  # noqa: S311

    peak_img = peak_sat(today, skip_upload=skip_upload) if not test else None

    google_maps = (
        f"https://www.google.com/maps/place/{today['lat']}N+{today['lon'][1:]}W/"
        f"@48.6266614,-114.0284462,97701m/"
        f"data=!3m1!1e3!4m4!3m3!8m2!3d48.8361389!4d-113.6542778?entry=ttu"
    )

    # Build peak text with optional summary
    peak_text = f"{today['name']} - {today['elevation']} ft."
    summary = _get_peak_summary(today["name"], float(today["lat"]), float(today["lon"]))
    if summary:
        peak_text += f" {summary}"

    return peak_text, peak_img, google_maps


if __name__ == "__main__":  # pragma: no cover
    print(peak(test=True))
