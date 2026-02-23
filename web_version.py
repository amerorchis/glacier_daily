"""
This module generates a daily update for Glacier National Park and saves it as an HTML file.
The multiple class encapsulations are necessary for the template to work here and in Drip.
"""

from jinja2 import Environment, FileSystemLoader

from shared.datetime_utils import format_short_date, format_time_12hr, now_mountain


class DailyUpdate:
    """An object to encapsulate the information"""

    def __init__(self, data: dict[str, object]):
        """
        Initialize the DailyUpdate with data.

        :param data: dictionary containing the daily update data.
        """
        for k, v in data.items():
            setattr(self, k, v)
        self.timestring = (
            format_short_date(now_mountain())
            + f" at {format_time_12hr(now_mountain())} MT"
        )


class myClass:
    """Encapsulates the DailyUpdate with arbitrary class"""

    def __init__(self, glacier: DailyUpdate):
        """
        Initialize myClass with a DailyUpdate instance.

        :param glacier: An instance of DailyUpdate.
        """
        self.daily_update = glacier


class Subscriber:
    """Name of the subscriber"""

    email = "for-web"


def web_version(
    data: dict[str, object],
    file_name: str = "server/today.html",
    template_path: str = "email_template.html",
) -> str:
    """
    Generate the web version of the daily update and save it as an HTML file.

    :param data: dictionary containing the daily update data.
    :param file_name: The name of the file to save the HTML content.
    :param template_path: The path to the HTML template.
    :return: The name of the file where the HTML content is saved.
    """
    env = Environment(loader=FileSystemLoader("email_html/"))  # noqa: S701
    template = env.get_template(template_path)

    # Wrap 'my' in the double object so it uses the template the same way as Drip.
    content = template.render(my=myClass(DailyUpdate(data)), subscriber=Subscriber())

    with open(file_name, "w", encoding="utf-8") as email:
        email.write(content)

    return file_name


if __name__ == "__main__":  # pragma: no cover
    from datetime import datetime

    from shared.data_types import (
        AlertBullet,
        CampgroundsResult,
        Event,
        EventsResult,
        HikerBikerResult,
        NoticesResult,
        RoadsResult,
        TrailsResult,
        WeatherResult,
    )

    data: dict[str, object] = {
        "date": "2024-05-01",
        "today": "May 1, 2024",
        "events": EventsResult(
            events=[
                Event(
                    start_time="8:30 am",
                    end_time="10 am",
                    name="Creekside Stroll",
                    location="Apgar VC",
                    link="http://www.nps.gov/planyourvisit/event-details.htm?id=1",
                    sortable=datetime(2024, 5, 1, 8, 30),
                ),
            ]
        ),
        "weather": WeatherResult(
            daylight_message="Today, sunrise is at 6:14am and sunset is at 8:51pm. There will be 14 hours and 36 minutes of daylight.",
            forecasts=[("West Glacier", 75, 30, "Partly cloudy")],
            season="summer",
            aqi_value=45,
            aqi_category="good.",
            aurora_quality="3.2 Kp (not visible)",
            aurora_message="",
            sunset_quality="good",
            sunset_message="Sunset color forecast: good.",
            cloud_cover_pct=30,
            alerts=[
                AlertBullet(
                    headline="Winter Storm Warning",
                    bullets=["What: Heavy snow", "Where: East Glacier"],
                )
            ],
        ),
        "weather_image": "https://glacier.org/daily/weather/5_1_2024_today_park_map.png",
        "trails": TrailsResult(
            closures=[
                "Grinnell Glacier: closed due to hazard snow - Josephine Lake to Glacier Overlook",
                "Highline: Use caution: Snow and ice still present - Logan Pass - Granite Park Chalet",
            ]
        ),
        "campgrounds": CampgroundsResult(
            statuses=[
                "Closed for the season: Avalanche Creek, Bowman Lake, Cut Bank, Fish Creek, Kintla Lake, Logging Creek, Many Glacier, Quartz Creek, Rising Sun, Sprague Creek, Two Medicine Lake",
            ]
        ),
        "roads": RoadsResult(
            closures=[
                "Going-to-the-Sun Road is closed from Lake McDonald Lodge to Rising Sun.",
                "Kintla Road is closed from Doverspike Meadow to the campground.",
                "Two Medicine Road, Bowman Lake Road, and Cut Bank Road are closed in their entirety.",
            ]
        ),
        "hikerbiker": HikerBikerResult(
            closures=[
                "Road Crew Closure: West - The Loop, 13.5 miles from gate at Lake McDonald Lodge.",
                "Avalanche Hazard Closure: West - Road Camp, 16.3 miles from gate at Lake McDonald Lodge.",
            ],
            explanatory_note="Road Crew Closures are in effect during work hours, Avalanche Hazard Closures are in effect at all times.",
        ),
        "notices": NoticesResult(
            notices=[
                'Our next Glacier Book Club (5/29) will feature the book Ranger Confidential with author Andrea Lankford! Register at <a href="https://glacier.org/glacier-book-club/">glacier.org/glacier-book-club</a>.',
            ]
        ),
        "peak": "Blackfoot Mountain - 9574 ft.",
        "peak_image": "https://glacier.org/daily/peak/5_1_2024_peak.jpg",
        "peak_map": "https://www.google.com/maps/place/48.58182N+113.66847W",
        "product_link": "https://shop.glacier.org/hike-medallion-red-bus-12/",
        "product_image": "https://glacier.org/daily/product/5_1_2024_product_otd.jpg",
        "product_title": "Red Bus Hiking Stick Medallion",
        "product_desc": "This hiking stick medallion features Glacier's historic Red Buses, with Clements Mountain in the background.",
        "image_otd": "https://glacier.org/daily/picture/5_1_2024_pic_otd.jpg",
        "image_otd_title": "Logan Pass Star Party 2019",
        "image_otd_link": "https://flickr.com/photos/glaciernps/49964910637",
        "sunrise_vid": "",
        "sunrise_still": "",
        "sunrise_str": "",
    }
    web_version(data, "server/today.html", "email_template.html")
    web_version(data, "server/printable.html", "printable.html")
