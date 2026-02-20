#!/home/pi/.local/bin/uv run --python 3.9 python
"""
Generate all of the data with a ThreadPoolExecutor, then upload it to the glacier.org
server with FTP.
"""

import base64
import concurrent.futures
import json
import os
from time import sleep

import requests

from activities.events import events_today
from activities.gnpc_events import get_gnpc_events
from drip.html_friendly import html_safe
from image_otd.image_otd import get_image_otd, prepare_pic_otd
from notices.notices import get_notices
from peak.peak import peak
from peak.sat import prepare_peak_upload
from product_otd.product import get_product, prepare_potd_upload
from roads.hiker_biker import get_hiker_biker_status
from roads.roads import get_road_status
from shared.datetime_utils import (
    cross_platform_strftime,
    format_date_readable,
    now_mountain,
)
from shared.ftp import FTPSession, upload_file
from shared.logging_config import get_logger
from shared.settings import get_settings
from sunrise_timelapse.get_timelapse import process_video
from trails_and_cgs.frontcountry_cgs import get_campground_status
from trails_and_cgs.trails import get_closed_trails
from weather.weather import weather_data
from weather.weather_img import prepare_weather_upload, weather_image
from web_version import web_version

logger = get_logger(__name__)


def gen_data(ftp_session=None):
    """
    Use threads to gather the data from every module, then store it in a dictionary.
    Make sure text is all HTML safe, then return it.

    When ftp_session is provided, image uploads are deferred out of threads
    and performed sequentially on the shared connection.
    """
    defer = ftp_session is not None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        weather_future = executor.submit(weather_data)
        trails_future = executor.submit(get_closed_trails)
        cg_future = executor.submit(get_campground_status)
        roads_future = executor.submit(get_road_status)
        hiker_biker_future = executor.submit(get_hiker_biker_status)
        events_future = executor.submit(events_today)
        image_future = executor.submit(get_image_otd, skip_upload=defer)
        peak_future = executor.submit(peak, skip_upload=defer)
        sunrise_future = executor.submit(process_video)
        product_future = executor.submit(get_product, skip_upload=defer)
        notices_futures = executor.submit(get_notices)

        sunrise_vid, sunrise_still, sunrise_str = sunrise_future.result()
        potd_title, potd_image, potd_link, potd_desc = product_future.result()
        weather = weather_future.result()
        image_otd, image_otd_title, image_otd_link = image_future.result()
        peak_name, peak_img, peak_map = peak_future.result()

    weather_img = weather_image(weather.results or [], skip_upload=defer)

    # Upload all images on the shared FTP session
    if ftp_session:
        if image_otd is None:
            image_otd, _ = ftp_session.upload(*prepare_pic_otd())
        if peak_img is None:
            peak_img, _ = ftp_session.upload(*prepare_peak_upload())
        if potd_image is None:
            potd_image, _ = ftp_session.upload(*prepare_potd_upload())
        if weather_img is None:
            weather_img, _ = ftp_session.upload(*prepare_weather_upload())

    drip_template_fields = {
        "date": now_mountain().strftime("%Y-%m-%d"),
        "today": format_date_readable(now_mountain()),
        "events": events_future.result(),
        "weather1": weather.message1,
        "weather_image": weather_img,
        "weather2": weather.message2,
        "season": weather.season,
        "trails": trails_future.result(),
        "campgrounds": cg_future.result(),
        "roads": roads_future.result(),
        "hikerbiker": hiker_biker_future.result(),
        "notices": notices_futures.result(),
        "peak": peak_name,
        "peak_image": peak_img,
        "peak_map": peak_map,
        "product_link": potd_link,
        "product_image": potd_image,
        "product_title": potd_title,
        "product_desc": potd_desc,
        "image_otd": image_otd,
        "image_otd_title": image_otd_title,
        "image_otd_link": image_otd_link,
        "sunrise_vid": sunrise_vid,
        "sunrise_still": sunrise_still,
        "sunrise_str": sunrise_str,
    }

    for key, value in drip_template_fields.items():
        if value is None:
            drip_template_fields[key] = ""
        else:
            drip_template_fields[key] = html_safe(value)

    return drip_template_fields


def write_data_to_json(data: dict, doctype: str) -> str:
    """
    Make a JSON file with the data, then return the filepath.
    """
    data = {i: base64.b64encode(data[i].encode("utf-8")).decode("utf-8") for i in data}

    data["date"] = now_mountain().strftime("%Y-%m-%d")
    data["time_generated"] = cross_platform_strftime(
        now_mountain(), "%-I:%M %p"
    ).lower()
    data["gnpc-events"] = get_gnpc_events()
    filepath = f"server/{doctype}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(data))

    return filepath


def send_to_server(file: str, directory: str) -> None:
    """
    Upload file to glacier.org using FTP.
    :return None.
    """

    filename = file.split("/")[-1]
    upload_file(directory, filename, file)


def purge_cache():
    """
    Purge the Cloudflare cache for the site.
    """
    settings = get_settings()
    purge_key = settings.CACHE_PURGE
    zone_id = settings.ZONE_ID
    if not purge_key or not zone_id:
        logger.warning("No CACHE_PURGE key or ZONE_ID set, skipping cache purge.")
        return

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {purge_key}",
    }
    data = {"purge_everything": True}

    response = requests.post(url, headers=headers, json=data, timeout=30)
    if response.status_code == 200:
        logger.info("Cache purged successfully.")
    else:
        logger.error(f"Failed to purge cache: {response.status_code} - {response.text}")


def refresh_cache():
    """
    Refresh the Drip cache by hitting the endpoint.
    """
    url = "https://api.glacierconservancy.org/email.json"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            logger.info("Cache refreshed successfully.")
        else:
            logger.error(
                f"Failed to refresh cache: {response.status_code} - {response.text}"
            )
    except requests.RequestException as e:
        logger.error(f"Error refreshing cache: {e}")


def clear_cache():
    """Remove cached email.json so all modules re-fetch fresh data."""
    cache_file = "server/email.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)


def serve_api(force: bool = False):
    """
    Get the data, then upload it to server for API.
    Uses a single FTP session for all uploads.
    """
    if force:
        clear_cache()

    with FTPSession() as ftp:
        data = gen_data(ftp_session=ftp)
        web = web_version(data)
        printable = web_version(data, "server/printable.html", "printable.html")
        json_file = write_data_to_json(data, "email.json")
        ftp.upload("api", json_file.split("/")[-1], json_file)
        ftp.upload("email", web.split("/")[-1], web)
        ftp.upload("printable", printable.split("/")[-1], printable)

    purge_cache()
    sleep(3)  # Wait for cache to purge
    refresh_cache()


if __name__ == "__main__":  # pragma: no cover
    import argparse as _argparse

    from shared.logging_config import setup_logging

    get_settings()  # Load email.env so ENVIRONMENT is available
    setup_logging()

    _parser = _argparse.ArgumentParser(description="Generate and upload data")
    _parser.add_argument(
        "--force",
        action="store_true",
        help="Clear cached data and re-fetch everything fresh",
    )
    _args = _parser.parse_args()

    if _args.force:
        clear_cache()

    environment = get_settings().ENVIRONMENT
    if environment == "development":
        gen_data()
    elif environment == "production":
        serve_api(force=_args.force)
