import random
from datetime import date
try:
    from peak.sat import peak_sat
except ModuleNotFoundError:
    from sat import peak_sat


def peak():
    with open('peak/PeaksCSV.csv', 'r') as p:
        data = p.readlines()
    peaks = [i.split(',') for i in data[1:] if i]
    for i in range(len(peaks)):
        mt = peaks[i]
        peaks[i] = {
            'name': mt[0],
            'elevation': mt[3].strip(),
            'lat': mt[1],
            'lon': mt[2]
        }

    random.seed(date.today().strftime('%Y%m%d'))
    today = random.choice(peaks)
    peak_img = peak_sat(today)

    return f"{today['name']} - {today['elevation']} ft.", peak_img

if __name__ == "__main__":
    print(peak())
