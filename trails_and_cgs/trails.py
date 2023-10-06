import requests
import urllib3
import json

urllib3.disable_warnings()

def remove_duplicate_trails(trail_list):
    name_lengths = {}
    for item in trail_list:
        name = item['properties']['name']
        coordinates = item['geometry']['coordinates']
        length = sum(len(coords) for coords in coordinates)
        # print(name, length)

        if name in name_lengths:
            if length > name_lengths[name]:
                name_lengths[name] = length
        else:
           name_lengths[name] = length

    filtered_list = []
    for item in trail_list:
        name = item['properties']['name']
        coordinates = item['geometry']['coordinates']
        length = sum(len(coords) for coords in coordinates)

        # If trail is the one with the most coordinates, is not a cutoff, and longer than 2 coordinates,
        # add its properties to the list.
        if length > 2 and 'cutoff' not in name.lower() and length == name_lengths[name]:
            filtered_list.append(item['properties'])

    return filtered_list

def closed_trails():
    url = 'https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q=SELECT%20*%20FROM%20nps_trails%20WHERE%20status%20=%20%27closed%27'
    r = requests.get(url, verify=False)
    status = json.loads(r.text)
    
    try:
        trails = status['features']
    except KeyError as k:
        return 'The trail closures page on the park website is currently down.'

    trails = remove_duplicate_trails(trails)
    closures = []

    for i in trails:
        name = i['name']

        if i['status_reason']:
            reason = i['status_reason'].replace('CLOSED','closed').replace('  ', ' ')
        elif i['trail_status_info']:
            reason = i['trail_status_info'].replace('CLOSED','closed').replace('  ', ' ')

        location = i['location']
        msg = f"{name}: {reason} - {location}" if location else f"{name}: {reason}"
        closures.append({'name':name, 'reason':reason, 'msg':msg})

    # If there are any duplicate listings where one has a reason and the other doesn't, remove the one with no reason
    to_delete = []
    for i in range(len(closures)):
        trail = closures[i]
        name, reason = trail['name'], trail.get('reason')
        if name and not reason:
            other_listings = [index for index, item in enumerate(closures) if item.get('name') == name and index != i]
            for x in other_listings:
                if closures[x]['reason']:
                    to_delete.append(i)
                    break
    
    to_delete = set(to_delete)
    to_delete = list(to_delete)
    to_delete.sort(reverse=True)
    for i in to_delete:
        del closures[i]

    closures.pop
    closures = [i['msg'] for i in closures] # Extract messages from list

    if 'Swiftcurrent Pass: Closed Due To Bear Activity' in closures:
        closures.remove('Swiftcurrent Pass: Closed Due To Bear Activity')

    closures = set(closures) # remove duplicates
    closures = sorted(list(closures)) # turn back into a list and sort

    if closures:
        message = '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n'
        for i in closures:
            message += f"<li>{i}</li>\n"
        return message + "</ul>"
    else:
        return 'There are no trail closures in effect today!'

if __name__ == "__main__":
    print(closed_trails())
