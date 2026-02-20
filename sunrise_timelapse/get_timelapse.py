"""
Select the best thumbnail frame from the timelapse video.
"""

import sys
from typing import Optional

import requests

from shared.datetime_utils import now_mountain
from shared.env_loader import load_env
from shared.retrieve_from_json import retrieve_from_json

load_env()


class TimelapseError(Exception):
    """Base exception for timelapse processing errors."""

    pass


class VideoProcessingError(TimelapseError):
    """Exception raised for errors during video processing."""

    pass


class FileOperationError(TimelapseError):
    """Exception raised for file operation errors."""

    pass


def fetch_glacier_data(endpoint_type: str) -> list:
    """
    Fetch data from glacier.org JSON endpoints.

    Args:
        endpoint_type (str): Either "timelapse" or "thumbnails"

    Returns:
        list: JSON data from the endpoint, empty list if error
    """
    endpoint_map = {
        "timelapse": "daily_timelapse_data.json",
        "thumbnails": "sunrise_thumbnails.json",
    }

    if endpoint_type not in endpoint_map:
        print(f"Invalid endpoint type: {endpoint_type}", file=sys.stderr)
        return []

    try:
        cache_buster = str(int(now_mountain().timestamp()))
        filename = endpoint_map[endpoint_type]
        url = f"http://timelapse.glacierconservancy.org/{filename}?{cache_buster}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint_type} data: {e}", file=sys.stderr)
        return []


def select_video(
    timelapse_data: list,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Select video based on today's date first, then fallback to latest.

    Args:
        timelapse_data (dict): JSON data from timelapse endpoint

    Returns:
        tuple[Optional[str], Optional[str], Optional[str]]: (video_id, video_url, descriptor)
    """
    if not timelapse_data:
        return None, None, None

    try:
        today = now_mountain()
        today_id = f"{today.month}_{today.day}_{today.year}_sunrise_timelapse"

        # Skip the first entry which is just the date
        video_entries = [
            entry
            for entry in timelapse_data
            if isinstance(entry, dict) and "id" in entry
        ]

        # First, look for today's video
        for entry in video_entries:
            if entry.get("id") == today_id:
                return entry.get("id"), entry.get("url"), "This Morning's"

        # Fallback to latest
        for entry in video_entries:
            if entry.get("id") == "latest":
                id_ = entry.get("vid_src").split("/")[-1].rsplit("_", 2)[0]
                return id_, entry.get("url"), "Latest"

        # If no latest found, return the first valid entry
        if video_entries:
            return video_entries[0].get("id"), video_entries[0].get("url"), "Latest"

        return None, None, None

    except Exception as e:
        print(f"Error selecting video: {e}", file=sys.stderr)
        return None, None, None


def find_matching_thumbnail(video_id: str, thumbnail_data: list) -> Optional[str]:
    """
    Find thumbnail that matches the selected video.

    Args:
        video_id (str): ID of the selected video
        thumbnail_data (dict): JSON data from thumbnail endpoint

    Returns:
        Optional[str]: Full URL to the thumbnail image
    """
    if not video_id or not thumbnail_data:
        return None

    try:
        # Extract date pattern from video_id (e.g., "8_20_2025" from "8_20_2025_sunrise_timelapse")
        video_date_part = video_id.replace("_sunrise_timelapse", "")
        expected_thumbnail = f"{video_date_part}_sunrise.jpg"

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
        print(f"Error finding matching thumbnail: {e}", file=sys.stderr)
        return None


def process_video() -> tuple[str, str, str]:
    """
    Process the sunrise timelapse by fetching remote data and selecting appropriate video and thumbnail.
    Args:
        test (bool): Whether to use test mode (kept for backward compatibility, not used).

    Returns:
        tuple[str, str, str]: (video_url, thumbnail_url, descriptor_string)
        Returns ("", "", "") if any error occurs.
    """
    try:
        # Check if we already have today's data cached
        already_retrieved, keys = retrieve_from_json(
            ["sunrise_vid", "sunrise_still", "sunrise_descriptor"]
        )
        if already_retrieved and len(keys) == 3:
            return keys[0], keys[1], keys[2]

        # Fetch remote data
        timelapse_data = fetch_glacier_data("timelapse")
        thumbnail_data = fetch_glacier_data("thumbnails")

        if not timelapse_data or not thumbnail_data:
            print("Failed to fetch remote data", file=sys.stderr)
            return "", "", ""

        # Select video based on today's date first, then latest
        video_id, video_url, descriptor = select_video(timelapse_data)

        if not video_id or not video_url:
            print("No suitable video found", file=sys.stderr)
            return "", "", ""

        # Find matching thumbnail
        thumbnail_url = find_matching_thumbnail(video_id, thumbnail_data)

        if not thumbnail_url:
            print(f"No matching thumbnail found for video {video_id}", file=sys.stderr)
            return "", "", ""

        return video_url, thumbnail_url, descriptor or ""

    except Exception as e:
        print(f"Unexpected error in process_video: {e}", file=sys.stderr)
        return "", "", ""


if __name__ == "__main__":  # pragma: no cover
    print(process_video())
