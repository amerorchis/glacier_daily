import requests
import os
import json

def get_subs(tag = 'Glacier Daily Update'):

    drip_token = os.environ['DRIP_TOKEN']
    account_id = os.environ['DRIP_ACCOUNT']
    api_key = drip_token
    url = f"https://api.getdrip.com/v2/{account_id}/subscribers"

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/vnd.api+json"
    }

    params = {
        "status": "active",
        "tags":tag
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return [data['subscribers'][i]['email'] for i in range(len(data['subscribers']))]
        # Handle `data` JSON response
    except requests.exceptions.RequestException as e:
        # Handle errors
        print("Error:", e)


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
    send_in_drip('')
