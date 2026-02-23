"""
Generate a static image of peak of the day using Mapbox API and upload to website.
"""

from io import BytesIO

import PIL
import requests
from PIL import Image

from shared.datetime_utils import now_mountain
from shared.ftp import upload_file
from shared.logging_config import get_logger
from shared.settings import get_settings

logger = get_logger(__name__)


def prepare_peak_upload() -> tuple[str, str, str]:
    """Return (directory, filename, local_path) for peak image upload."""
    today = now_mountain()
    filename = f"{today.month}_{today.day}_{today.year}_peak.jpg"
    return "peak", filename, "email_images/today/peak.jpg"


def upload_peak() -> str:
    """
    Upload the file from the today folder as the image with today's day as name,
    then return the URL.
    """
    directory, filename, local_path = prepare_peak_upload()
    address, _ = upload_file(directory, filename, local_path)
    return address


def peak_sat(peak: dict, skip_upload: bool = False) -> str | None:
    """
    Use mapbox API to get peak image, then send to FTP function.
    return: URL of peak image/header.
    """
    settings = get_settings()
    lat, lon = peak["lat"], peak["lon"]

    # These settings tend to get best peak image
    zoom = 14
    bearing = 0
    dimensions = "1020x600@2x"

    # Construct url and get image.
    base_url = f"https://api.mapbox.com/styles/v1/{settings.MAPBOX_ACCOUNT}/{settings.MAPBOX_STYLE}/static/"
    url_params = f"{lon},{lat},{zoom},{bearing}/{dimensions}?access_token={settings.MAPBOX_TOKEN}&logo=false"
    try:
        r = requests.get(f"{base_url}{url_params}", timeout=10)

        # If successful, save file, then return URL from FTP function.
        if r.status_code == 200:
            image = Image.open(BytesIO(r.content))
            image.save("email_images/today/peak.jpg")

            if skip_upload:
                return None
            return upload_peak()
        else:
            raise requests.RequestException("Bad status code")

    except (requests.RequestException, PIL.UnidentifiedImageError) as e:
        # If it fails, give the default peak header.
        logger.error("Peak sat image failed: %s", e)
        return "https://glacier.org/daily/summer/peak.jpg"


if __name__ == "__main__":  # pragma: no cover
    peak_sat(
        {
            "name": "Long Knife Peak",
            "elevation": "9910",
            "lat": "48.99815",
            "lon": "-114.21147",
        }
    )
