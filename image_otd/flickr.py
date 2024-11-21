from flickrapi import FlickrAPI
import random
from datetime import datetime
from urllib.request import urlretrieve
from pathlib import Path
from os import environ

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("email.env")

flickr_key = environ['flickr_key']
flickr_secret = environ['flickr_secret']
glaciernps_uid = environ['glaciernps_uid']

def get_flickr():
    flickr = FlickrAPI(flickr_key, flickr_secret, format='parsed-json')
    photos = flickr.photos.search(user_id=glaciernps_uid, per_page='1')
    total = photos['photos']['total']

    random.seed(datetime.today().strftime("%Y:%m:%d"))
    potd_num = random.randint(1, total)
    photos = flickr.photos.search(user_id=glaciernps_uid, per_page='1', page=potd_num)

    while len(photos['photos']['photo']) == 0:
        potd_num = random.randint(1, total)
        photos = flickr.photos.search(user_id=glaciernps_uid, per_page='1', page=potd_num)

    selected = photos['photos']['photo'][0]

    server, id, secret, title = selected['server'], selected['id'], selected['secret'], selected['title']
    pic_url = f'https://live.staticflickr.com/{server}/{id}_{secret}_c.jpg'
    save_loc = Path('email_images/today/raw_image_otd.jpg')

    link = f'https://flickr.com/photos/glaciernps/{id}'
    urlretrieve(pic_url, save_loc)

    return save_loc, title, link

if __name__ == "__main__":
    print(get_flickr())
