import requests
import json
import urllib3
from datetime import datetime
urllib3.disable_warnings()

def campground_alerts():
    url = 'https://carto.nps.gov/user/glaclive/api/v2/sql?format=JSON&q=SELECT%20*%20FROM%20glac_front_country_campgrounds'
    r = requests.get(url, verify=False)
    status = json.loads(r.text)
    
    try:
        campgrounds = status['rows']
    except KeyError:
        return 'The campgrounds page on the park website is currently down.'

    closures = []
    season_closures = []
    statuses = []

    for i in campgrounds:
        name = i['name'].replace('  ',' ')

        if i['status'] == 'closed':
            if 'season' in i['service_status']:
                season_closures.append(name)
            else:
                closures.append(f'{name} CG: currently closed.')

        notice = f'{i["description"]}' if i["description"] and ('camping only' in i["description"].lower() or 'posted' in i["description"].lower()) else None
        if notice:
            notice = notice.replace(' <br><br><a href="https://www.nps.gov/glac/planyourvisit/reservation-campgrounds.htm" target="_blank">Campground Details</a><br><br>', '')
            notice = notice.replace('<b>','').replace('</b>','')
            notice =  '. '.join(i.capitalize() for i in notice.split('. '))
            notice = f'{name} CG: {notice}'
            statuses.append(notice)

    statuses, closures, season_closures = set(statuses), set(closures), set(season_closures) # remove duplicates
    statuses, closures, season_closures = sorted(list(statuses)), sorted(list(closures)), sorted(list(season_closures)) # turn back into a list and sort
    statuses.extend(closures)

    if season_closures:
        seasonal = [f'Closed for the season: {", ".join(season_closures)}'] if datetime.now().month > 8 else [f'Not yet open for the season: {", ".join(season_closures)}']
        statuses.extend(seasonal)

    if statuses:
        message = '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
        for i in statuses:
            message += f"<li>{i}</li>\n"
        return message + "</ul>"
    else:
        return ""

if __name__ == "__main__":
    print(campground_alerts())
