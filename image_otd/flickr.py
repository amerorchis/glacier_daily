"""
This module interacts with the Flickr API to retrieve the image of the day.
"""

import random
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from os import environ
from pathlib import Path
from typing import Dict
from urllib.request import URLError, urlretrieve

from flickrapi import FlickrAPI


def get_env_vars() -> Dict[str, str]:
    """Get required environment variables."""
    required_vars = ["flickr_key", "flickr_secret", "glaciernps_uid"]
    env_vars = {}

    for var in required_vars:
        if var not in environ:
            raise FlickrAPIError(f"Missing environment variable: {var}")
        env_vars[var] = environ[var]

    return env_vars


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
        env_vars = get_env_vars()
        flickr = FlickrAPI(
            env_vars["flickr_key"], env_vars["flickr_secret"], format="parsed-json"
        )
        photos = flickr.photos.search(user_id=environ["glaciernps_uid"], per_page="1")
        total = int(photos["photos"]["total"])

        random.seed(datetime.today().strftime("%Y:%m:%d"))
        potd_num = random.randint(1, total)
        photos = flickr.photos.search(
            user_id=environ["glaciernps_uid"], per_page="1", page=potd_num
        )

        # Retry if no photos found
        while len(photos["photos"]["photo"]) == 0:
            potd_num = random.randint(1, total)
            photos = flickr.photos.search(
                user_id=environ["glaciernps_uid"], per_page="1", page=potd_num
            )

        selected = photos["photos"]["photo"][0]
        server = selected["server"]
        photo_id = selected["id"]
        secret = selected["secret"]
        title = selected["title"]

        pic_url = f"https://live.staticflickr.com/{server}/{photo_id}_{secret}_c.jpg"
        save_loc = Path("email_images/today/raw_image_otd.jpg")
        save_loc.parent.mkdir(parents=True, exist_ok=True)

        print(f"Downloading image from {pic_url} to {save_loc}")

        req = urllib.request.Request(
            pic_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; GlacierDailyBot/1.0)"},
        )

        max_retries = 2
        backoff = 4
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req) as response, open(
                    save_loc, "wb"
                ) as out_file:
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
