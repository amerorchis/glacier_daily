#!/usr/bin/env python3.9
"""
Generate all of the data with a ThreadPoolExecutor, then upload it to the glacier.org
server with FTP.
"""
from datetime import datetime
import json
import sys
import os
from ftplib import FTP
import base64
import concurrent.futures

from activities.events import events_today
from activities.gnpc_events import get_gnpc_events
from peak.peak import peak
from roads.roads import get_road_status
from roads.hiker_biker import get_hiker_biker_status
from trails_and_cgs.trails import closed_trails
from trails_and_cgs.frontcountry_cgs import campground_alerts
from weather.weather import weather_data
from weather.weather_img import weather_image
from image_otd.image_otd import resize_full
from sunrise_timelapse.vid_frame import process_video
from product_otd.product import get_product
from notices.notices import get_notices
from drip.html_friendly import html_safe
from web_version import web_version


def gen_data():
    """
    Use threads to gather the data from every module, then store it in a dictionary.
    Make sure text is all HTML safe, then return it.
    """

    with concurrent.futures.ThreadPoolExecutor() as executor:
        weather_future = executor.submit(weather_data)
        trails_future = executor.submit(closed_trails)
        cg_future = executor.submit(campground_alerts)
        roads_future = executor.submit(get_road_status)
        hiker_biker_future = executor.submit(get_hiker_biker_status)
        events_future = executor.submit(events_today)
        image_future = executor.submit(resize_full)
        peak_future = executor.submit(peak)
        sunrise_future = executor.submit(process_video)
        product_future = executor.submit(get_product)
        notices_futures = executor.submit(get_notices)

        sunrise_vid, sunrise_still = sunrise_future.result()
        potd_title, potd_image, potd_link, potd_desc = product_future.result()
        weather = weather_future.result()
        image_otd, image_otd_title, image_otd_link = image_future.result()
        peak_name, peak_img, peak_map = peak_future.result()

    drip_template_fields = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'today': datetime.now().strftime("%B %-d, %Y"),
        'events': events_future.result(),
        'weather1':weather.message1,
        'weather_image': weather_image(weather.results),
        'weather2': weather.message2,
        'season': weather.season,
        'trails': trails_future.result(),
        'campgrounds': cg_future.result(),
        'roads': roads_future.result(),
        'hikerbiker': hiker_biker_future.result(),
        'notices': notices_futures.result(),
        'peak': peak_name,
        'peak_image': peak_img,
        'peak_map': peak_map,
        'product_link': potd_link,
        'product_image': potd_image,
        'product_title': potd_title,
        'product_desc': potd_desc,
        'image_otd': image_otd,
        'image_otd_title': image_otd_title,
        'image_otd_link': image_otd_link,
        'sunrise_vid': sunrise_vid,
        'sunrise_still': sunrise_still,
    }

    for key, value in drip_template_fields.items():
        if value is None:
            drip_template_fields[key] = ""
        else:
            drip_template_fields[key] = html_safe(value)

    return drip_template_fields

def write_data_to_json(data: dict, doctype: str) -> str:
    data = {i: base64.b64encode(data[i].encode('utf-8')).decode('utf-8') for i in data.keys()}

    data['date'] = datetime.now().strftime('%Y-%m-%d')
    data['time_generated'] = datetime.now().strftime('%-I:%M %p')
    data['gnpc-events'] = get_gnpc_events()
    filepath = f"server/{doctype}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(data))

    return filepath

def send_to_server(filepath: str, directory: str) -> str:
    """
    Upload file to glacier.org using FTP.
    :return A string of the URL it was updated too.
    """

    # Connect to the FTP server
    username = os.environ['FTP_USERNAME']
    password = os.environ['FTP_PASSWORD']
    server = 'ftp.glacier.org'
    ftp = FTP(server)
    ftp.login(username, password)
    ftp.cwd(directory)

    filename = filepath.split('/')[-1]
    try:
        # Open the local file in binary mode
        with open(filepath, 'rb') as f:
            # Upload the file to the FTP server
            ftp.storbinary('STOR ' + filename, f)

    except Exception as e:
        print(f'Failed upload {filepath} file. {e}', file=sys.stderr)

    # Close the FTP connection
    ftp.quit()

    return f'https://glacier.org/daily/{directory}/{filename}'


def serve_api():
    """
    Get the data, then upload it to server for API.
    """
    data = gen_data()
    web = web_version(data)
    printable = web_version(data, 'server/printable.html', 'printable.html')
    send_to_server(write_data_to_json(data, 'email.json'), 'api')
    send_to_server(web, 'email')
    send_to_server(printable, 'printable')

if __name__ == "__main__":
    serve_api()
