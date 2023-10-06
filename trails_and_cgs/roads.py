import requests
import json

# This doesn't really work because the park doesn't store road closures in a useful format.

def closed_roads():
    url = 'https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q=SELECT%20*%20FROM%20glac_road_nds%20WHERE%20status%20=%20%27closed%27'
    r = requests.get(url, verify=False)
    status = json.loads(r.text)
    roads = status['features']
    roads = [x['properties'] for x in roads]
    for i in roads:
        print(i)
    closures = [f"{i['rdname']}: {i['reason']}" for i in roads]