from datetime import datetime
import json
import os
from ftplib import FTP
import base64
import concurrent.futures
from datetime import datetime

from activities.events import events_today
from peak.peak import peak
from trails_and_cgs.trails import closed_trails
from trails_and_cgs.frontcountry_cgs import campground_alerts
from weather.weather import weather_data
from weather.weather_img import weather_image
from image_otd.image_otd import resize_full
from sunrise_timelapse.vid_frame import process_video
from product_otd.product import get_product
from notices.notices import get_notices
from drip.html_friendly import html_safe


def gen_data():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        weather_future = executor.submit(weather_data)
        trails_future = executor.submit(closed_trails)
        cg_future = executor.submit(campground_alerts)
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
        
    drip_template_fields = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'today': datetime.now().strftime("%B %-d, %Y"),
        'events':events_future.result(),
        'weather1':weather.message1,
        'weather_image': weather_image(weather.results),
        'weather2':weather.message2,
        'trails':trails_future.result(),
        'campgrounds':cg_future.result(),
        'notices':notices_futures.result(),
        'peak':peak_future.result(),
        'product_link': potd_link,
        'product_image': potd_image,
        'product_title':potd_title,
        'product_desc':potd_desc,
        'image_otd': image_otd,
        'image_otd_title': image_otd_title,
        'image_otd_link': image_otd_link,
        'sunrise_vid': sunrise_vid,
        'sunrise_still': sunrise_still,
    }
    
    for key, value in drip_template_fields.items():
        if value == None:
            drip_template_fields[key] = ""
        else:
            drip_template_fields[key] = html_safe(value)

    return drip_template_fields


def send_to_server(data):

    data = {i: base64.b64encode(data[i].encode('utf-8')).decode('utf-8') for i in data.keys()}

    data['date'] = datetime.now().strftime('%Y-%m-%d')

    with open("server/email.json", "w") as f:
        f.write(json.dumps(data))
    
    file_path = f'email.json'
    directory = 'api'

    # Connect to the FTP server
    username = os.environ['FTP_USERNAME']
    password = os.environ['FTP_PASSWORD']
    server = 'ftp.glacier.org'
    ftp = FTP(server)
    ftp.login(username, password)
    ftp.cwd(directory)

    try:
        # Open the local file in binary mode
        with open('server/email.json', 'rb') as f:
            # Upload the file to the FTP server
            ftp.storbinary('STOR ' + file_path, f)

    except:
        print('Failed upload JSON file.')
        pass

    # Close the FTP connection
    ftp.quit()

    return f'https://glacier.org/daily/{directory}/{file_path}'

def serve_api():
    data = gen_data()
    send_to_server(data)

if __name__ == "__main__":
    serve_api()
    