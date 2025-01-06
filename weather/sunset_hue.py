from datetime import datetime
import os
import requests

def get_sunset_hue() -> str:
    """
    Fetches the sunset hue forecast for a specific location and date.

    Returns:
        str: A formatted HTML string describing the sunset hue forecast, or an empty string if the forecast is not favorable.
    """
    lat = "48.528556"
    long = "-113.991674"
    date = datetime.today().strftime('%Y-%m-%d')
    forecast_type = "sunset"

    url = f"https://api.sunsethue.com/event?latitude={lat}&longitude={long}&date={date}&type={forecast_type}"

    payload = {}
    headers = {
        "x-api-key": os.environ.get('SUNSETHUE_KEY')
    }

    response = requests.get(url, headers=headers, data=payload, timeout=10)

    if response.status_code == 200:
        r = response.json()
    else:
        return ''

    quality, quality_text, cloud_cover = r.get('data').get('quality', 0), r.get('data').get('quality_text', '').lower(), r.get('data').get('cloud_cover', 0)
    if quality < 0.41 or cloud_cover > 0.4:
        return ''

    return f'<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">The sunset is forecast to be {quality_text} this evening{"." if quality_text == "good" else "!"}</p>'

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("email.env")
    print(get_sunset_hue())
