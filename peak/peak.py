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

logger = get_logger(__name__)

SCRIPT_DIR = Path(__file__).parent
WIKIPEDIA_JSON = SCRIPT_DIR / "peaks_wikipedia.json"
PEAKS_CSV = SCRIPT_DIR / "PeaksCSV.csv"
PEAK_COORD_MATCH_TOLERANCE = 0.001

# Anchor for the peak rotation. Peaks are shuffled into a new random order every
# len(peaks) days and then handed out one per day, so every peak appears exactly
# once per cycle. Changing this date reshuffles which peak lands on which day.
PEAK_CYCLE_EPOCH = date(2026, 1, 1)


def _get_peak_summary(name: str, lat: float, lon: float) -> str | None:
    """Get the Wikipedia summary for a peak if available."""
    if not WIKIPEDIA_JSON.exists():
        return None
    with open(WIKIPEDIA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    for peak_data in data.get("peaks", []):
        if (
            peak_data["name"] == name
            and abs(peak_data["lat"] - lat) < PEAK_COORD_MATCH_TOLERANCE
            and abs(peak_data["lon"] - lon) < PEAK_COORD_MATCH_TOLERANCE
        ):
            return peak_data.get("summary")
    return None


def select_peak(peaks: list[dict], day: date) -> dict:
    """
    Pick the peak for a given day.

    Each cycle of len(peaks) days gets its own seeded shuffle of the full list,
    and the day's position within that cycle indexes into it. Every peak is used
    exactly once per cycle, so coverage is even instead of the long droughts and
    clustered repeats that come from drawing at random each day.
    """
    cycle, offset = divmod((day - PEAK_CYCLE_EPOCH).days, len(peaks))
    order = list(peaks)
    random.Random(f"peaks-{cycle}").shuffle(order)  # noqa: S311
    return order[offset]


def peak(test: bool = False, skip_upload: bool = False) -> tuple[str, str | None, str]:
    """
    Select a random peak, and return the relevant information.
    """
    if test:
        logger.debug("Test mode.")

    with open(PEAKS_CSV, encoding="utf-8") as p:
        peaks = list(csv.DictReader(p))

    today = select_peak(peaks, date.today())

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
