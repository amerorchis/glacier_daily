"""
This module interacts with the Flickr API to retrieve the image of the day.
"""

from dataclasses import dataclass
from flickrapi import FlickrAPI
import random
from datetime import datetime
from urllib.request import urlretrieve, URLError
from pathlib import Path
from os import environ
from typing import Dict


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

        try:
            urlretrieve(pic_url, save_loc)
        except URLError as e:
            raise FlickrAPIError(f"Failed to download image: {str(e)}")

        link = f"https://flickr.com/photos/glaciernps/{photo_id}"
        return FlickrImage(save_loc, title, link)

    except KeyError as e:
        raise FlickrAPIError(f"Missing environment variable: {str(e)}")
    except Exception as e:
        raise FlickrAPIError(f"Flickr API error: {str(e)}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("email.env")
    print(get_flickr())
