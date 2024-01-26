import requests
import json
import urllib3
try:
    from roads.Road import Road
except ModuleNotFoundError:
    from Road import Road
urllib3.disable_warnings()

def closed_roads():
    url = 'https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q=SELECT%20*%20FROM%20glac_road_nds%20WHERE%20status%20=%20%27closed%27'
    r = requests.get(url, verify=False)
    status = json.loads(r.text)
    if not status.get('features'):
        return ''
    
    roads_json = status['features']

    roads = {'Going-to-the-Sun Road': Road('Going-to-the-Sun Road'),
             'Camas Road': Road('Camas Road'),
             'Two Medicine Road': Road('Two Medicine Road'),
             'Many Glacier Road': Road('Many Glacier Road'),
             'Bowman Lake Road': Road('Bowman Lake Road'),
             'Kintla Road': Road('Kintla Road', 'NS')}
    
    for i in roads_json:
        road_name = i['properties']['rdname']
        coordinates = i['geometry']['coordinates'] if len(i['geometry']['coordinates']) > 1 else i['geometry']['coordinates'][0]

        x = {
            'status': i['properties']['status'],
            'reason': i['properties']['reason'],
            'start': coordinates[0],
            'last': coordinates[-1],
            'length': len(coordinates)
            }
        
        if road_name in roads:
            roads[road_name].set_coord(x['start'])
            roads[road_name].set_coord(x['last'])
        elif road_name == 'Inside North Fork Road':
            if x['start'][1] > 48.786:
                roads['Kintla Road'].set_coord(x['start'])
            if x['last'][1] > 48.786:
                roads['Kintla Road'].set_coord(x['last'])

    entirely_closed = []
    statuses = []
    for i in roads:
        road = roads[i]
        road.closure_string()

        if road.entirely_closed:
            entirely_closed.append(road.name)
        
        else:
            statuses.append(road.closure_str)
    
    if len(entirely_closed) > 1:
        entirely_closed[-1] = f'and {entirely_closed[-1]}'

        statuses.append(f'{", ".join(entirely_closed)} are closed in their entirety.')
    
    elif len(entirely_closed) == 1:
        statuses.append(f'{entirely_closed[0]} is closed in its entirety.')

    if statuses:
        message = '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
        for i in statuses:
            message += f"<li>{i}</li>\n"
        return message + "</ul>"
    else:
        return '<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">There are no closures on major roads today!</p>'


def get_road_status() -> str:
    try:
        return closed_roads()
    except Exception as e:
        print(e)
        return ''


if __name__ == "__main__":
    print(get_road_status())

