import requests
import os
from io import BytesIO
from PIL import Image
from datetime import datetime
from ftplib import FTP

from dotenv import load_dotenv
load_dotenv("email.env")


def upload_peak():
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

    try:
        # Open the local file in binary mode
        with open('email_images/today/peak.jpg', 'rb') as f:
            # Upload the file to the FTP server
            ftp.storbinary('STOR ' + file_path, f)

    except:
        print('Failed upload product image')
        pass

    # Close the FTP connection
    ftp.quit()

    return f'https://glacier.org/daily/{directory}/{file_path}'

def peak_sat(peak: dict) -> str:
    lat, lon = peak['lat'], peak['lon']
    zoom = 14
    bearing = 0
    dimensions = '1020x600@2x'
    access_token = os.environ['MAPBOX_TOKEN']

    base_url = "https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/static/"
    url_params = f"{lon},{lat},{zoom},{bearing}/{dimensions}?access_token={access_token}&logo=false"

    r = requests.get(f'{base_url}{url_params}')

    if r.status_code == 200:
        image = Image.open(BytesIO(r.content))
        image.save('email_images/today/peak.jpg')
    
        return upload_peak()
    
    else:
        print('Peak sat image failed.')
        return 'https://glacier.org/daily/peak.jpg'

if __name__ == "__main__":
    peak_sat({'name': 'Long Knife Peak', 'elevation': '9910', 'lat': '48.99815', 'lon': '-114.21147'})
