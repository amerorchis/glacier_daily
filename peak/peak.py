import random
from datetime import date

def peak():
    with open('peak/PeaksCSV.csv', 'r') as p:
        data = p.readlines()
    peaks = [(i.split(',')[0], i.split(',')[3].replace('\n','')) for i in data[1:] if i]
    random.seed(date.today().strftime('%Y%m%d'))
    today = random.choice(peaks)
    return f"{today[0]} - {int(today[1]):,} ft."
