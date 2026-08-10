"""
This module interacts with the Flickr API to retrieve the image of the day.
"""

import random
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

from flickrapi import FlickrAPI
from PIL import Image

from shared.logging_config import get_logger
from shared.settings import get_settings

logger = get_logger(__name__)


class FlickrAPIError(Exception):
    """Raised when Flickr API operations fail"""


class FlickrRateLimitError(FlickrAPIError):
    """Raised when Flickr rate-limits us — retrying another photo won't help"""


@dataclass
class FlickrImage:
    """
    An image downloaded from Flickr.
    """

    path: Path
    title: str
    link: str


_MIN_WIDTH = 1040  # 2x of 520px email column
_MAX_PHOTO_ATTEMPTS = 5  # candidate photos to try before giving up for the day
_SAVE_LOC = Path("email_images/today/raw_image_otd.jpg")


def _best_image_url(flickr: FlickrAPI, photo_id: str) -> str:
    """Pick the smallest Flickr size that is at least ``_MIN_WIDTH`` wide.

    Falls back to the largest available size if nothing meets the threshold.
    """
    sizes = flickr.photos.getSizes(photo_id=photo_id)["sizes"]["size"]

    # Videos in the photostream list player/MP4 entries alongside their still
    # frames. Those aren't images, so picking one hands PIL a video file. The
    # still-frame sizes are tagged "photo" and stay usable.
    images = [s for s in sizes if s.get("media", "photo") == "photo"]
    if not images:
        raise FlickrAPIError(f"No image sizes available for photo {photo_id}")

    # Sort by width ascending
    images.sort(key=lambda s: int(s["width"]))

    # First size >= _MIN_WIDTH (smallest sufficient)
    for size in images:
        if int(size["width"]) >= _MIN_WIDTH:
            return size["source"]

    # Nothing large enough — use the biggest available
    return images[-1]["source"]


def _check_is_image(url: str, content_type: str, data: bytes) -> None:
    """Reject a download that isn't a usable image before it reaches the email.

    Raises:
        FlickrAPIError: If the response is empty, not an image, or unreadable.
    """
    if not data:
        raise FlickrAPIError(f"Empty response downloading image from {url}")

    if content_type and not content_type.split(";")[0].strip().startswith("image/"):
        raise FlickrAPIError(f"Downloaded content is not an image ({content_type})")

    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except Exception as e:
        raise FlickrAPIError(f"Downloaded image is unreadable: {e!s}") from e


def _download_image(pic_url: str) -> bytes:
    """Download an image, retrying with backoff on rate limiting.

    Returns:
        bytes: The verified image data.

    Raises:
        FlickrRateLimitError: If Flickr keeps returning HTTP 429.
        FlickrAPIError: If the download fails or isn't a usable image.
    """
    req = urllib.request.Request(  # noqa: S310
        pic_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        },
    )

    max_retries = 2  # retry count for image download
    backoff = 4  # initial backoff seconds for 429 responses
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req) as response:  # noqa: S310
                if response.status == 429:
                    # Too Many Requests, backoff and retry
                    if attempt < max_retries - 1:
                        wait = backoff * (2**attempt)
                        logger.warning(
                            "Flickr 429 Too Many Requests, backing off %ds", wait
                        )
                        time.sleep(wait)
                        continue
                    raise FlickrRateLimitError(
                        "Too many requests (HTTP 429) after retries."
                    )
                content_type = response.headers.get("Content-Type", "")
                data = response.read()
        except URLError as e:
            # If it's a 429, handle backoff, else raise
            if hasattr(e, "code") and e.code == 429:
                if attempt < max_retries - 1:
                    wait = backoff * (2**attempt)
                    logger.warning(
                        "Flickr 429 Too Many Requests, backing off %ds", wait
                    )
                    time.sleep(wait)
                    continue
                raise FlickrRateLimitError(
                    "Too many requests (HTTP 429) after retries."
                ) from e
            raise FlickrAPIError(f"Failed to download image: {e!s}") from e

        _check_is_image(pic_url, content_type, data)
        return data

    raise FlickrRateLimitError("Too many requests (HTTP 429) after retries.")


def _random_photo(
    flickr: FlickrAPI, user_id: str, rng: random.Random, total: int
) -> dict | None:
    """Draw one random photo from the photostream, or None if the page is empty."""
    page = rng.randint(1, total)
    photos = flickr.photos.search(user_id=user_id, per_page="1", page=page)
    found = photos["photos"]["photo"]
    return found[0] if found else None


def get_flickr() -> FlickrImage:
    """
    Retrieve a random image from the Glacier National Park's Flickr account.

    The photo is chosen from a date-seeded RNG, so every run on a given day
    makes the same draws. A candidate that can't be turned into a usable image
    (a video, a broken download) is skipped and the next draw is tried, so one
    bad photo doesn't cost the whole day its image.

    Returns:
        FlickrImage: Object containing image path, title, and link

    Raises:
        FlickrAPIError: If API calls fail or no candidate yields a usable image
    """
    try:
        settings = get_settings()
        flickr = FlickrAPI(
            settings.FLICKR_KEY, settings.FLICKR_SECRET, format="parsed-json"
        )
        photos = flickr.photos.search(user_id=settings.GLACIERNPS_UID, per_page="1")
        total = int(photos["photos"]["total"])
    except KeyError as e:
        raise FlickrAPIError(f"Missing environment variable: {e!s}") from e
    except Exception as e:
        raise FlickrAPIError(f"Flickr API error: {e!s}") from e

    rng = random.Random(datetime.today().strftime("%Y:%m:%d"))  # noqa: S311
    last_error = "no candidates drawn"

    for attempt in range(1, _MAX_PHOTO_ATTEMPTS + 1):
        try:
            selected = _random_photo(flickr, settings.GLACIERNPS_UID, rng, total)
            if selected is None:
                last_error = "empty search page"
                continue

            pic_url = _best_image_url(flickr, selected["id"])
            data = _download_image(pic_url)
        except FlickrRateLimitError:
            # Another photo would hit the same limit — give up for this run
            raise
        except Exception as e:
            last_error = str(e)
            logger.warning(
                "Flickr candidate %d/%d unusable, drawing another: %s",
                attempt,
                _MAX_PHOTO_ATTEMPTS,
                e,
            )
            continue

        _SAVE_LOC.parent.mkdir(parents=True, exist_ok=True)
        with open(_SAVE_LOC, "wb") as out_file:
            out_file.write(data)

        link = f"https://flickr.com/photos/glaciernps/{selected['id']}"
        return FlickrImage(_SAVE_LOC, selected["title"], link)

    raise FlickrAPIError(
        f"No usable photo after {_MAX_PHOTO_ATTEMPTS} attempts: {last_error}"
    )
