from drip.subscriber_list import subscriber_list
from drip.scheduled_subs import update_scheduled_subs

import requests
import os
import json


def get_subs(tag):
    updates = update_scheduled_subs()
    subs =  subscriber_list(tag)

    # Update subscriber list based on changes today (drip updates aren't fast enough)
    for i in updates['start']:
        if i not in subs:
            subs.append(i)

    for i in updates['end']:
        if i in subs:
            subs.remove(i)
    
    return subs


def send_in_drip(email, campaign_id='169298893'):

    drip_token = os.environ['DRIP_TOKEN']
    account_id = os.environ['DRIP_ACCOUNT']
    api_key = drip_token

    url = f"https://api.getdrip.com/v2/{account_id}/workflows/{campaign_id}/subscribers"
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/vnd.api+json"
    }

    data = {
        "subscribers": [{
            "email": email,
        }]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    r = response.json()
    
    if response.status_code == 201:
        print(f'Drip: Email sent successfully to {email}!')
    else:
        print(f"Failed to subscribe {email} to the campaign. Error message:", r["errors"][0]["code"], ' - ', r["errors"][0]["message"])

if __name__ == "__main__":
    print(get_subs('Glacier Daily Update'))
