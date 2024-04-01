"""
Generate a static image of peak of the day using Mapbox API and upload to website.
"""

import os
from datetime import datetime
from io import BytesIO
from ftplib import FTP
import requests
from PIL import Image

from dotenv import load_dotenv
load_dotenv("email.env")


def upload_peak() -> str:
    """
    Upload the file from the today folder as the image with today's day as name,
    then return the URL.
    """
    username = os.environ['FTP_USERNAME']
    password = os.environ['FTP_PASSWORD']
    server = 'ftp.glacier.org'
    today = datetime.now()
    file_path = f'{today.month}_{today.day}_{today.year}_peak.jpg'
    directory = 'peak'

    # Connect to the FTP server
    ftp = FTP(server)
    ftp.login(username, password)
    ftp.cwd(directory)

    # Open the local file in binary mode
    with open('email_images/today/peak.jpg', 'rb') as f:
        # Upload the file to the FTP server
        ftp.storbinary('STOR ' + file_path, f)

    # Close the FTP connection
    ftp.quit()

    return f'https://glacier.org/daily/{directory}/{file_path}'

def peak_sat(peak: dict) -> str:
    """
    Use mapbox API to get peak image, then send to FTP function.
    return: URL of peak image/header.
    """
    lat, lon = peak['lat'], peak['lon']

    # These settings tend to get best peak image
    zoom = 14
    bearing = 0
    dimensions = '1020x600@2x'
    access_token = os.environ['MAPBOX_TOKEN']

    # This uses a custom mapbox style from your account, the default works fine if you
    # haven't set one.
    mapbox_account = os.environ.get('MAPBOX_ACCOUNT','mapbox')
    mapbox_style = os.environ.get('MAPBOX_STYLE', 'satellite-streets-v12')

    # Construct url and get image.
    base_url = f"https://api.mapbox.com/styles/v1/{mapbox_account}/{mapbox_style}/static/"
    url_params = f"{lon},{lat},{zoom},{bearing}/{dimensions}?access_token={access_token}&logo=false"
    r = requests.get(f'{base_url}{url_params}', timeout=10)

    # If successful, save file, then return URL from FTP function.
    if r.status_code == 200:
        image = Image.open(BytesIO(r.content))
        image.save('email_images/today/peak.jpg')

        return upload_peak()

    # If it fails, give the default peak header.
    print('Peak sat image failed.')
    return 'https://glacier.org/daily/summer/peak.jpg'

if __name__ == "__main__":
    peak_sat({'name': 'Long Knife Peak', 'elevation': '9910', 'lat': '48.99815','lon':'-114.21147'})
