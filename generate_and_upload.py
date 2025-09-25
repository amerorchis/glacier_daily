#!/usr/bin/env python3.9
"""
Generate all of the data with a ThreadPoolExecutor, then upload it to the glacier.org
server with FTP.
"""
import base64
import concurrent.futures
import json
import os
import sys
from datetime import datetime
from weakref import ref

import requests

from activities.events import events_today
from activities.gnpc_events import get_gnpc_events
from drip.html_friendly import html_safe
from image_otd.image_otd import get_image_otd
from notices.notices import get_notices
from peak.peak import peak
from product_otd.product import get_product
from roads.hiker_biker import get_hiker_biker_status
from roads.roads import get_road_status
from shared.datetime_utils import cross_platform_strftime, format_date_readable
from shared.ftp import upload_file
from sunrise_timelapse.get_timelapse import process_video
from trails_and_cgs.frontcountry_cgs import get_campground_status
from trails_and_cgs.trails import get_closed_trails
from weather.weather import weather_data
from weather.weather_img import weather_image
from web_version import web_version


def gen_data():
    """
    Use threads to gather the data from every module, then store it in a dictionary.
    Make sure text is all HTML safe, then return it.
    """

    with concurrent.futures.ThreadPoolExecutor() as executor:
        weather_future = executor.submit(weather_data)
        trails_future = executor.submit(get_closed_trails)
        cg_future = executor.submit(get_campground_status)
        roads_future = executor.submit(get_road_status)
        hiker_biker_future = executor.submit(get_hiker_biker_status)
        events_future = executor.submit(events_today)
        image_future = executor.submit(get_image_otd)
        peak_future = executor.submit(peak)
        sunrise_future = executor.submit(process_video)
        product_future = executor.submit(get_product)
        notices_futures = executor.submit(get_notices)

        sunrise_vid, sunrise_still, sunrise_str = sunrise_future.result()
        potd_title, potd_image, potd_link, potd_desc = product_future.result()
        weather = weather_future.result()
        image_otd, image_otd_title, image_otd_link = image_future.result()
        peak_name, peak_img, peak_map = peak_future.result()

    drip_template_fields = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "today": format_date_readable(datetime.now()),
        "events": events_future.result(),
        "weather1": weather.message1,
        "weather_image": weather_image(weather.results),
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
    data = {
        i: base64.b64encode(data[i].encode("utf-8")).decode("utf-8")
        for i in data.keys()
    }

    data["date"] = datetime.now().strftime("%Y-%m-%d")
    data["time_generated"] = cross_platform_strftime(
        datetime.now(), "%-I:%M %p"
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
    purge_key = os.getenv("CACHE_PURGE")
    zone_id = os.getenv("ZONE_ID")
    if not purge_key or not zone_id:
        print(
            "No CACHE_PURGE key or ZONE_ID set, skipping cache purge.", file=sys.stderr
        )
        return

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {purge_key}",
    }
    data = {"purge_everything": True}

    response = requests.post(url, headers=headers, json=data, timeout=5)
    if response.status_code == 200:
        print("Cache purged successfully.")
    else:
        print(
            f"Failed to purge cache: {response.status_code} - {response.text}",
            file=sys.stderr,
        )


def refresh_cache():
    """
    Refresh the Drip cache by hitting the endpoint.
    """
    url = "https://api.glacierconservancy.org/email.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("Cache refreshed successfully.")
        else:
            print(
                f"Failed to refresh cache: {response.status_code} - {response.text}",
                file=sys.stderr,
            )
    except requests.RequestException as e:
        print(f"Error refreshing cache: {e}", file=sys.stderr)


def serve_api():
    """
    Get the data, then upload it to server for API.
    """
    data = gen_data()
    web = web_version(data)
    printable = web_version(data, "server/printable.html", "printable.html")
    send_to_server(write_data_to_json(data, "email.json"), "api")
    send_to_server(web, "email")
    send_to_server(printable, "printable")
    purge_cache()
    refresh_cache()


if __name__ == "__main__":  # pragma: no cover
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "development":
        gen_data()
    elif environment == "production":
        serve_api()
