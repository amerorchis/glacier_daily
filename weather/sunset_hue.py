"""
Get and format a forecast as to the colorfulness of the sunset.
"""

import os
from datetime import datetime

import requests


def get_sunset_hue(test: bool = False) -> str:
    """
    Fetches the sunset hue forecast for a specific location and date.

    Returns:
        str: A formatted HTML string describing the sunset hue forecast, or an empty string if the forecast is not favorable.
    """
    lat = "48.528556"
    long = "-113.991674"
    date = datetime.today().strftime("%Y-%m-%d")
    forecast_type = "sunset"

    url = f"https://api.sunsethue.com/event?latitude={lat}&longitude={long}&date={date}&type={forecast_type}"

    payload = {}
    headers = {"x-api-key": os.environ.get("SUNSETHUE_KEY")}

    try:
        response = requests.get(url, headers=headers, data=payload, timeout=10)
    except requests.exceptions.Timeout:
        return 0, "unknown", ""

    if response.status_code == 200:
        r = response.json()
    else:
        return 0, "unknown", ""

    quality, quality_text, cloud_cover = (
        r.get("data").get("quality", 0),
        r.get("data").get("quality_text", "unknown").lower(),
        r.get("data").get("cloud_cover", 0),
    )

    if test:
        print(quality, quality_text, cloud_cover)

    if quality < 0.41 or cloud_cover > 0.6:
        msg = ""
    else:
        msg = f'The sunset is forecast to be {quality_text} this evening{"." if quality_text == "good" else "!"}'

    return cloud_cover, quality_text, msg


if __name__ == "__main__":  # pragma: no cover
    from dotenv import load_dotenv

    load_dotenv("email.env")
    get_sunset_hue(True)
