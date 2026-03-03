"""
Generate a static image of peak of the day using Mapbox API and upload to website.
"""

from io import BytesIO

import PIL
import requests
from PIL import Image

from shared.datetime_utils import now_mountain
from shared.ftp import FTPSession
from shared.logging_config import get_logger
from shared.retry import retry
from shared.settings import get_settings

logger = get_logger(__name__)

MAPBOX_ZOOM = 14
MAPBOX_IMAGE_DIMENSIONS = "1020x600"


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
    with FTPSession() as ftp:
        address, _ = ftp.upload(directory, filename, local_path)
    return address


@retry(3, (requests.exceptions.RequestException,), default=None, backoff=5)
def _fetch_mapbox_image(url: str) -> bytes | None:
    """Fetch satellite image from Mapbox API."""
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.content


def peak_sat(peak: dict, skip_upload: bool = False) -> str | None:
    """
    Use mapbox API to get peak image, then send to FTP function.
    return: URL of peak image/header.
    """
    settings = get_settings()
    lat, lon = peak["lat"], peak["lon"]

    # These settings tend to get best peak image
    zoom = MAPBOX_ZOOM
    bearing = 0
    dimensions = MAPBOX_IMAGE_DIMENSIONS

    # Construct url and get image.
    base_url = f"https://api.mapbox.com/styles/v1/{settings.MAPBOX_ACCOUNT}/{settings.MAPBOX_STYLE}/static/"
    url_params = f"{lon},{lat},{zoom},{bearing}/{dimensions}?access_token={settings.MAPBOX_TOKEN}&logo=false"
    try:
        content = _fetch_mapbox_image(f"{base_url}{url_params}")
        if content is None:
            raise requests.RequestException("All fetch attempts failed")

        image = Image.open(BytesIO(content))
        image.save("email_images/today/peak.jpg")

        if skip_upload:
            return None
        return upload_peak()

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
