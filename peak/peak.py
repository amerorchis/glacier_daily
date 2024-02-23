import random
from datetime import date
try:
    from peak.sat import peak_sat
except ModuleNotFoundError:
    from sat import peak_sat


def peak(test = False):
    """
    Select a random peak, and return the relevant information.
    """

    # Grab list from CSV and turn into Python list
    with open('peak/PeaksCSV.csv', 'r') as p:
        data = p.readlines()
    peaks = [i.split(',') for i in data[1:] if i]
    for index, mt in enumerate(peaks):
        peaks[index] = {
            'name': mt[0],
            'elevation': mt[3].strip(),
            'lat': mt[1],
            'lon': mt[2]
        }

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
