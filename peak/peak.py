"""
Select a random peak, get an image of it, and return the info.
"""

import random
from datetime import date
import sys
import os
import csv

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from peak.sat import peak_sat
from shared.retrieve_from_json import retrieve_from_json

def peak(test = False):
    """
    Select a random peak, and return the relevant information.
    """
    if test:
        print('Test mode.')

    # Check if we already have today's peak
    else:
        already_retrieved, keys = retrieve_from_json(['peak', 'peak_image', 'peak_map'])
        if already_retrieved:
            return keys

    with open('peak/PeaksCSV.csv', 'r', encoding='utf-8') as p:
        peaks = list(csv.DictReader(p))

    # Select a random one with current date as seed
    random.seed(date.today().strftime('%Y%m%d'))
    today = random.choice(peaks)

    peak_img = peak_sat(today) if not test else None

    google_maps = f"https://www.google.com/maps/place/{today['lat']}N+{today['lon'][1:]}W/" \
                  f"@48.6266614,-114.0284462,97701m/" \
                  f"data=!3m1!1e3!4m4!3m3!8m2!3d48.8361389!4d-113.6542778?entry=ttu"

    return f"{today['name']} - {today['elevation']} ft.", peak_img, google_maps

if __name__ == "__main__":
    print(peak(test = True))
