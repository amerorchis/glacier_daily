"""
This module generates a daily update for Glacier National Park and saves it as an HTML file.
The multiple class encapsulations are necessary for the template to work here and in Drip.
"""

from jinja2 import Environment, FileSystemLoader

from shared.datetime_utils import format_short_date, format_time_12hr, now_mountain


class DailyUpdate:
    """An object to encapsulate the information"""

    def __init__(self, data: dict[str, str]):
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
    data: dict[str, str],
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
    env.filters["base64_decode"] = lambda x: x
    template = env.get_template(template_path)

    # You have to wrap 'my' in the double object so it uses the template the same way as Drip.
    # It's kind of hacky, but it works.
    content = template.render(my=myClass(DailyUpdate(data)), subscriber=Subscriber())

    if "printable" in file_name:  # Remove some styling from print version
        content = content.replace("font-size:12px;", "").replace(
            "line-height:18px;", ""
        )

    with open(file_name, "w", encoding="utf-8") as email:
        email.write(content)

    return file_name


if __name__ == "__main__":  # pragma: no cover
    data = {
        "date": "2024-05-01",
        "today": "May 1, 2024",
        "events": "",
        "weather1": "Today, sunrise is at 6:14am and sunset is at 8:51pm. There will be 14 hours and 36 minutes of daylight.\n<br><br>Forecasts Around the Park:",
        "weather_image": "https://glacier.org/daily/weather/5_1_2024_today_park_map.png",
        "weather2": '<p style="font-size:14px; line-height:22px; font-weight:bold; color:#333333; margin:0 0 5px;"><a href="https://weather.gov" style="color:#6c7e44; text-decoration:none;">Alerts from the National Weather Service</a></p><ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n<li>Winter Storm Warning issued May 1 at 2:33PM MDT until May 2 at 12:00PM MDT by NWS Great Falls MT: * WHAT...Heavy snow. Additional snow accumulations between 4 and 10\ninches, with higher amounts above pass level. Winds gusting as\nhigh as 40 mph.\n\n* WHERE...East Glacier Park Region Zone.\n\n* WHEN...Until noon MDT Thursday.\n\n* IMPACTS...Travel could be very difficult and tire chains may be\nrequired for some vehicles. Those in the backcountry should ensure\nthey have appropriate knowledge and gear and may want to consider\nalternate plans. Areas of blowing snow could significantly reduce\nvisibility.\n\n* ADDITIONAL DETAILS...The worst roadway impacts will occur during\nthe overnight and morning hours. The heavy wet snow may cause\nisolated power outages.</li>\n<li>Winter Weather Advisory issued May 1 at 2:33PM MDT until May 2 at 12:00PM MDT by NWS Great Falls MT: * WHAT...Snow. Additional snow accumulations between 2 and 6 inches\non the plains, with an additional 4 to 8 inches in the mountains\nof the Southern Rocky Mountain Front. Winds gusting as high as 45\nmph.\n\n* WHERE...Northern High Plains and Southern Rocky Mountain Front.\n\n* WHEN...Until noon MDT Thursday.\n\n* IMPACTS...Slush and or snow covered roads could cause difficult\ntravel conditions. Areas of blowing snow could significantly\nreduce visibility.\n\n* ADDITIONAL DETAILS...The worst roadway impacts will occur during\nthe overnight and morning hours. The heavy wet snow may cause\nisolated power outages.</li>\n</ul>',
        "season": "summer",
        "trails": '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n<li>Grinnell Glacier: closed due to hazard snow - Josephine Lake to Glacier Overlook</li>\n<li>Highline: Use caution: Snow and ice still present, mostly near haystack saddle. - Logan Pass - Granite Park Chalet</li>\n</ul>',
        "campgrounds": '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">\n<li>Closed for the season: Avalanche Creek, Bowman Lake, Cut Bank, Fish Creek, Kintla Lake, Logging Creek, Many Glacier, Quartz Creek, Rising Sun, Sprague Creek, Two Medicine Lake</li>\n</ul>',
        "roads": '<ul style="margin:0 0 12px; padding-left:20px; padding-top:0px; font-size:12px;line-height:18px; color:#333333;">\n<li>Going-to-the-Sun Road is closed from Lake McDonald Lodge to Rising Sun.</li>\n<li>Kintla Road is closed from Doverspike Meadow to the campground.</li>\n<li>Two Medicine Road, Bowman Lake Road, and Cut Bank Road are closed in their entirety.</li>\n</ul>',
        "hikerbiker": '<ul style="margin:0 0 6px; padding-left:20px; padding-top:0px; font-size:12px;line-height:18px; color:#333333;">\n<li>Road Crew Closure: West - The Loop, 13.5 miles from gate at Lake McDonald Lodge.</li>\n<li>Avalanche Hazard Closure: West - Road Camp, 16.3 miles from gate at Lake McDonald Lodge.</li>\n<li>Road Crew Closure: East - Grizzly Point, 6.0 miles from gate at Rising Sun.</li>\n<li>Avalanche Hazard Closure: East - Jackson Glacier Overlook, 7.0 miles from gate at Rising Sun.</li>\n</ul><p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">Road Crew Closures are in effect during work hours, Avalanche Hazard Closures are in effect at all times.</p>',
        "notices": '<ul style="margin:0 0 35px; padding-left:10px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;"><li>Our next Glacier Book Club (5/29) will feature the book Ranger Confidential with author Andrea Lankford! Register at <a href="https://glacier.org/glacier-book-club/" style="color:#333333;">glacier.org/glacier-book-club</a>.</li>\n</ul>',
        "peak": "Blackfoot Mountain - 9574 ft.",
        "peak_image": "https://glacier.org/daily/peak/5_1_2024_peak.jpg",
        "peak_map": "https://www.google.com/maps/place/48.58182N+113.66847W/@48.6266614,-114.0284462,97701m/data=!3m1!1e3!4m4!3m3!8m2!3d48.8361389!4d-113.6542778?entry=ttu",
        "product_link": "https://shop.glacier.org/hike-medallion-red-bus-12/",
        "product_image": "https://glacier.org/daily/product/5_1_2024_product_otd.jpg",
        "product_title": "Red Bus Hiking Stick Medallion",
        "product_desc": "This hiking stick medallion features Glacier's historic Red Buses, with Clements Mountain in the background.",
        "image_otd": "https://glacier.org/daily/picture/5_1_2024_pic_otd.jpg",
        "image_otd_title": "Logan Pass Star Party 2019",
        "image_otd_link": "https://flickr.com/photos/glaciernps/49964910637",
        "sunrise_vid": "",
        "sunrise_still": "",
    }
    web_version(data, "server/printable.html", "printable.html")
