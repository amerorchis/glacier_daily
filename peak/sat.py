"""
Generate a static image of peak of the day using Mapbox API and upload to website.
"""

import sys
import os
from datetime import datetime
from io import BytesIO
import requests

import PIL
from PIL import Image

from dotenv import load_dotenv

load_dotenv("email.env")

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from shared.ftp import upload_file


def upload_peak() -> str:
    """
    Upload the file from the today folder as the image with today's day as name,
    then return the URL.
    """

    today = datetime.now()
    filename = f"{today.month}_{today.day}_{today.year}_peak.jpg"
    file = "email_images/today/peak.jpg"
    directory = "peak"
    address, _ = upload_file(directory, filename, file)
    return address


def peak_sat(peak: dict) -> str:
    """
    Use mapbox API to get peak image, then send to FTP function.
    return: URL of peak image/header.
    """
    lat, lon = peak["lat"], peak["lon"]

    # These settings tend to get best peak image
    zoom = 14
    bearing = 0
    dimensions = "1020x600@2x"
    access_token = os.environ["MAPBOX_TOKEN"]

    # This uses a custom mapbox style from your account, the default works fine if you
    # haven't set one.
    mapbox_account = os.environ.get("MAPBOX_ACCOUNT", "mapbox")
    mapbox_style = os.environ.get("MAPBOX_STYLE", "satellite-streets-v12")

    # Construct url and get image.
    base_url = (
        f"https://api.mapbox.com/styles/v1/{mapbox_account}/{mapbox_style}/static/"
    )
    url_params = f"{lon},{lat},{zoom},{bearing}/{dimensions}?access_token={access_token}&logo=false"
    try:
        r = requests.get(f"{base_url}{url_params}", timeout=10)

        # If successful, save file, then return URL from FTP function.
        if r.status_code == 200:
            image = Image.open(BytesIO(r.content))
            image.save("email_images/today/peak.jpg")

            return upload_peak()
        else:
            raise requests.RequestException("Bad status code")

    except (requests.RequestException, PIL.UnidentifiedImageError) as e:
        # If it fails, give the default peak header.
        print(f"Peak sat image failed. {e}")
        return "https://glacier.org/daily/summer/peak.jpg"


if __name__ == "__main__":
    peak_sat(
        {
            "name": "Long Knife Peak",
            "elevation": "9910",
            "lat": "48.99815",
            "lon": "-114.21147",
        }
    )
