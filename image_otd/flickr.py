"""
This module interacts with the Flickr API to retrieve the image of the day.
"""

import random
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import URLError

from flickrapi import FlickrAPI

from shared.settings import get_settings


class FlickrAPIError(Exception):
    """Raised when Flickr API operations fail"""

    pass


@dataclass
class FlickrImage:
    """
    An image downloaded from Flickr.
    """

    path: Path
    title: str
    link: str


def get_flickr() -> FlickrImage:
    """
    Retrieve a random image from the Glacier National Park's Flickr account.

    Returns:
        FlickrImage: Object containing image path, title, and link

    Raises:
        FlickrAPIError: If API calls fail or environment variables are missing
        URLError: If image download fails
    """
    try:
        settings = get_settings()
        flickr = FlickrAPI(
            settings.flickr_key, settings.flickr_secret, format="parsed-json"
        )
        photos = flickr.photos.search(user_id=settings.glaciernps_uid, per_page="1")
        total = int(photos["photos"]["total"])

        random.seed(datetime.today().strftime("%Y:%m:%d"))
        potd_num = random.randint(1, total)  # noqa: S311
        photos = flickr.photos.search(
            user_id=settings.glaciernps_uid, per_page="1", page=potd_num
        )

        # Retry if no photos found
        while len(photos["photos"]["photo"]) == 0:
            potd_num = random.randint(1, total)  # noqa: S311
            photos = flickr.photos.search(
                user_id=settings.glaciernps_uid, per_page="1", page=potd_num
            )

        selected = photos["photos"]["photo"][0]
        server = selected["server"]
        photo_id = selected["id"]
        secret = selected["secret"]
        title = selected["title"]

        pic_url = f"https://live.staticflickr.com/{server}/{photo_id}_{secret}_c.jpg"
        save_loc = Path("email_images/today/raw_image_otd.jpg")
        save_loc.parent.mkdir(parents=True, exist_ok=True)

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

        max_retries = 2
        backoff = 4
        for attempt in range(max_retries):
            try:
                with (
                    urllib.request.urlopen(req) as response,  # noqa: S310
                    open(save_loc, "wb") as out_file,
                ):
                    if response.status == 429:
                        # Too Many Requests, backoff and retry
                        if attempt < max_retries - 1:
                            wait = backoff * (2**attempt)
                            print(
                                f"Received 429 Too Many Requests. Backing off for {wait} seconds..."
                            )
                            time.sleep(wait)
                            continue
                        else:
                            raise FlickrAPIError(
                                "Too many requests (HTTP 429) after retries."
                            )
                    out_file.write(response.read())
                break
            except URLError as e:
                # If it's a 429, handle backoff, else raise
                if hasattr(e, "code") and e.code == 429:
                    if attempt < max_retries - 1:
                        wait = backoff * (2**attempt)
                        print(
                            f"Received 429 Too Many Requests. Backing off for {wait} seconds..."
                        )
                        time.sleep(wait)
                        continue
                    else:
                        raise FlickrAPIError(
                            "Too many requests (HTTP 429) after retries."
                        ) from e
                raise FlickrAPIError(f"Failed to download image: {str(e)}") from e

        link = f"https://flickr.com/photos/glaciernps/{photo_id}"
        return FlickrImage(save_loc, title, link)

    except KeyError as e:
        raise FlickrAPIError(f"Missing environment variable: {str(e)}") from e
    except Exception as e:
        raise FlickrAPIError(f"Flickr API error: {str(e)}") from e
