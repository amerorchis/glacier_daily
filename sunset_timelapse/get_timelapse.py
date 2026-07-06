"""
Select tonight's sunset timelapse video and matching thumbnail.

The timelapse system publishes sunset entries into the same two JSON
feeds the sunrise flow consumes (daily_timelapse_data.json and
sunrise_thumbnails.json). Sunset entries use the id
``{M}_{D}_{YYYY}_sunset_timelapse`` and thumbnails named
``{M}_{D}_{YYYY}_sunset.jpg``, plus a rolling ``latest_sunset`` entry.
"""

from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger
from sunrise_timelapse.get_timelapse import fetch_glacier_data

logger = get_logger(__name__)

# Descriptor for a sunset published today. The sunset email is
# today-or-nothing: main.py only triggers the send when the selected
# video carries this descriptor, while the "Latest" fallback remains
# available to the web version / email.json.
TONIGHT_DESCRIPTOR = "Tonight's"


def select_sunset_video(
    timelapse_data: list,
) -> tuple[str | None, str | None, str | None]:
    """
    Select a sunset video: today's entry first, then the latest_sunset fallback.

    Args:
        timelapse_data (list): JSON data from the timelapse endpoint

    Returns:
        tuple[Optional[str], Optional[str], Optional[str]]: (video_id, video_url, descriptor)
    """
    if not timelapse_data:
        return None, None, None

    try:
        today = now_mountain()
        today_id = f"{today.month}_{today.day}_{today.year}_sunset_timelapse"

        # Skip the first entry which is just the date
        video_entries = [
            entry
            for entry in timelapse_data
            if isinstance(entry, dict) and "id" in entry
        ]

        # First, look for tonight's video
        for entry in video_entries:
            if entry.get("id") == today_id:
                return entry.get("id"), entry.get("url"), TONIGHT_DESCRIPTOR

        # Fallback to the rolling latest_sunset entry. Unlike the sunrise
        # flow there is no "first valid entry" fallback — the feed mixes
        # sunrise and sunset entries, so an arbitrary entry could be a
        # sunrise video.
        for entry in video_entries:
            if entry.get("id") == "latest_sunset":
                id_ = entry.get("vid_src").split("/")[-1].rsplit("_", 2)[0]
                return id_, entry.get("url"), "Latest"

        return None, None, None

    except Exception as e:
        logger.error("Error selecting sunset video: %s", e)
        return None, None, None


def find_matching_sunset_thumbnail(video_id: str, thumbnail_data: list) -> str | None:
    """
    Find the thumbnail that matches the selected sunset video.

    Args:
        video_id (str): ID of the selected video
        thumbnail_data (list): JSON data from the thumbnail endpoint

    Returns:
        Optional[str]: Full URL to the thumbnail image
    """
    if not video_id or not thumbnail_data:
        return None

    try:
        # Extract date pattern from video_id (e.g., "8_20_2025" from "8_20_2025_sunset_timelapse")
        video_date_part = video_id.replace("_sunset_timelapse", "")
        expected_thumbnail = f"{video_date_part}_sunset.jpg"

        # Skip the first entry which is just the date
        thumbnail_entries = [
            entry
            for entry in thumbnail_data
            if isinstance(entry, dict) and "path" in entry
        ]

        for entry in thumbnail_entries:
            thumbnail_path = entry.get("path", "")
            if expected_thumbnail in thumbnail_path:
                return f"https://glacier.org{thumbnail_path}"

        return None

    except Exception as e:
        logger.error("Error finding matching sunset thumbnail: %s", e)
        return None


def process_sunset_video() -> tuple[str, str, str]:
    """
    Fetch remote timelapse data and select the sunset video and thumbnail.

    Returns:
        tuple[str, str, str]: (video_url, thumbnail_url, descriptor_string)
        video_url is the webcam-timelapse page URL (not the raw mp4) and
        thumbnail_url is an absolute https://glacier.org URL.
        Returns ("", "", "") if any error occurs.
    """
    try:
        # Fetch remote data
        timelapse_data = fetch_glacier_data("timelapse")
        thumbnail_data = fetch_glacier_data("thumbnails")

        if not timelapse_data or not thumbnail_data:
            logger.warning("Failed to fetch remote sunset timelapse data")
            return "", "", ""

        # Select video based on today's date first, then latest_sunset
        video_id, video_url, descriptor = select_sunset_video(timelapse_data)

        if not video_id or not video_url:
            logger.warning("No suitable sunset video found")
            return "", "", ""

        # Find matching thumbnail
        thumbnail_url = find_matching_sunset_thumbnail(video_id, thumbnail_data)

        if not thumbnail_url:
            logger.warning("No matching thumbnail found for sunset video %s", video_id)
            return "", "", ""

        return video_url, thumbnail_url, descriptor or ""

    except Exception as e:
        logger.exception("Unexpected error in process_sunset_video: %s", e)
        return "", "", ""


if __name__ == "__main__":  # pragma: no cover
    print(process_sunset_video())
