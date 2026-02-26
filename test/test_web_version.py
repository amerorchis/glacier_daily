import os
import tempfile
from datetime import datetime

import pytest

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
from web_version import DailyUpdate, Subscriber, myClass, web_version


@pytest.fixture
def sample_data():
    return {
        "date": "2025-05-28",
        "today": "May 28, 2025",
        "events": EventsResult(
            events=[
                Event(
                    start_time="8:30 am",
                    end_time="10 am",
                    name="Creekside Stroll",
                    location="Apgar VC",
                    link="http://www.nps.gov/planyourvisit/event-details.htm?id=1",
                    sortable=datetime(2025, 5, 28, 8, 30),
                ),
            ]
        ),
        "weather": WeatherResult(
            daylight_message="Today, sunrise is at 6:14am and sunset is at 8:51pm.",
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
                    headline="Winter Storm Warning", bullets=["What: Heavy snow"]
                )
            ],
        ),
        "weather_image": "https://example.com/weather.png",
        "trails": TrailsResult(
            closures=[
                "Grinnell Glacier: closed due to hazard snow",
            ]
        ),
        "campgrounds": CampgroundsResult(
            statuses=[
                "Fish Creek CG: currently closed.",
            ]
        ),
        "roads": RoadsResult(
            closures=[
                "Going-to-the-Sun Road is closed from Lake McDonald Lodge to Rising Sun.",
            ]
        ),
        "hikerbiker": HikerBikerResult(
            closures=["Road Crew Closure: West - The Loop, 13.5 miles from gate."],
            explanatory_note="Road Crew Closures are in effect during work hours.",
        ),
        "notices": NoticesResult(
            notices=[
                'Book Club on 5/29 featuring <a href="https://glacier.org/glacier-book-club/">Ranger Confidential</a>.',
            ]
        ),
        "peak": "Blackfoot Mountain - 9574 ft.",
        "peak_image": "https://example.com/peak.jpg",
        "peak_map": "https://example.com/peak_map",
        "product_link": "https://example.com/product",
        "product_image": "https://example.com/product.jpg",
        "product_title": "Red Bus Hiking Stick Medallion",
        "product_desc": "This hiking stick medallion features Glacier's historic Red Buses.",
        "image_otd": "https://example.com/image.jpg",
        "image_otd_title": "Logan Pass Star Party 2019",
        "image_otd_link": "https://example.com/image_link",
        "sunrise_vid": "",
        "sunrise_still": "",
        "sunrise_str": "",
    }


def test_daily_update_timestring(sample_data):
    du = DailyUpdate(sample_data)
    assert hasattr(du, "timestring")
    assert du.today == "May 28, 2025"


def test_myClass_wraps_daily_update(sample_data):
    du = DailyUpdate(sample_data)
    my = myClass(du)
    assert my.daily_update is du


def test_subscriber_email():
    assert Subscriber.email == "for-web"


def test_web_version_creates_file(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_output.html")
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        assert os.path.exists(out_file)
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Glacier Daily Update" in content or "Glacier National Park" in content
        assert "May 28, 2025" in content


def test_email_renders_event_details(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_output.html")
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Creekside Stroll" in content
        assert "8:30 am" in content
        assert "Apgar VC" in content
        # Verify old-style event format: name, location (link)
        assert "(link)</a>" in content
        assert "margin:0 0 25px" in content  # events ul margin


def test_email_renders_weather_fields(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_output.html")
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "sunrise is at 6:14am" in content
        assert "summer" in content  # season in image URLs
        # AQI uses old wording
        assert "The current AQI in West Glacier is 45" in content
        assert "Winter Storm Warning" in content
        # Evening Viewing Forecasts line
        assert "Evening Viewing Forecasts:" in content
        assert "Aurora: 3.2 Kp (not visible)" in content
        assert "Cloud Cover: 30%" in content


def test_email_renders_trail_closures(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_output.html")
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Grinnell Glacier" in content
        assert "Going-to-the-Sun Road is closed" in content
        assert "Road Crew Closure" in content
        assert "Fish Creek CG" in content


def test_email_renders_notices(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_output.html")
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Book Club on 5/29" in content
        assert "Ranger Confidential" in content


def test_email_hides_empty_roads(sample_data):
    sample_data["roads"] = RoadsResult()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_output.html")
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Road Closures</a>" not in content


def test_email_campgrounds_independent_of_hikerbiker(sample_data):
    """Campgrounds should show even when hiker/biker has no closures (old bug fix)."""
    sample_data["hikerbiker"] = HikerBikerResult()  # no closures
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_output.html")
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Hiker/Biker" not in content  # hiker/biker hidden
        assert "Fish Creek CG" in content  # campgrounds still shown


def test_printable_renders_structured_data(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "printable.html")
        web_version(sample_data, file_name=out_file, template_path="printable.html")
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "May 28, 2025" in content
        assert "Creekside Stroll" in content
        assert "Grinnell Glacier" in content
        assert "sunrise is at 6:14am" in content
        assert "Blackfoot Mountain" in content
        assert "Red Bus Hiking Stick Medallion" in content


def test_editorial_renders_structured_data(sample_data):
    """Editorial template renders all structured data sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "editorial.html")
        web_version(
            sample_data,
            file_name=out_file,
            template_path="email_template_editorial.html",
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        # Editorial design markers
        assert "GLACIER NATIONAL PARK CONDITIONS" in content
        assert "May 28, 2025" in content
        # Events
        assert "Creekside Stroll" in content
        assert "8:30 am" in content
        assert "(link)</a>" in content
        # Weather
        assert "sunrise is at 6:14am" in content
        assert "summer" in content  # season in image URLs
        assert "The current AQI in West Glacier is 45" in content
        assert "Evening Viewing Forecasts:" in content
        assert "Winter Storm Warning" in content
        # Conditions
        assert "Grinnell Glacier" in content
        assert "Going-to-the-Sun Road is closed" in content
        assert "Road Crew Closure" in content
        assert "Fish Creek CG" in content
        # Notices
        assert "Book Club on 5/29" in content
        # Peak + Product
        assert "Blackfoot Mountain" in content
        assert "Red Bus Hiking Stick Medallion" in content


def test_editorial_campgrounds_independent_of_hikerbiker(sample_data):
    """Editorial template fixes the campground nesting bug."""
    sample_data["hikerbiker"] = HikerBikerResult()  # no closures
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "editorial.html")
        web_version(
            sample_data,
            file_name=out_file,
            template_path="email_template_editorial.html",
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Hiker/Biker" not in content  # hiker/biker hidden
        assert "Fish Creek CG" in content  # campgrounds still shown


def test_wifi_renders_structured_data(sample_data):
    """WiFi template renders events and weather correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "wifi.html")
        web_version(sample_data, file_name=out_file, template_path="wifi_email.html")
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        # Events
        assert "Creekside Stroll" in content
        assert "8:30 am" in content
        assert "(link)</a>" in content
        # Weather
        assert "sunrise is at 6:14am" in content
        assert "The current AQI in West Glacier is 45" in content
        assert "Evening Viewing Forecasts:" in content
        assert "Winter Storm Warning" in content
        # WiFi should NOT have trails/roads/peak/product
        assert "Grinnell Glacier" not in content
        assert "Blackfoot Mountain" not in content
        assert "Red Bus Hiking Stick Medallion" not in content


def test_printable_editorial_renders_structured_data(sample_data):
    """Printable editorial template renders all sections with editorial design."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "printable_editorial.html")
        web_version(
            sample_data,
            file_name=out_file,
            template_path="printable_editorial.html",
        )
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        # Editorial design markers
        assert "GLACIER NATIONAL PARK CONDITIONS" in content
        assert "May 28, 2025" in content
        # Events
        assert "Creekside Stroll" in content
        # Weather
        assert "sunrise is at 6:14am" in content
        assert "The current AQI in West Glacier is 45" in content
        assert "Evening Viewing Forecasts:" in content
        # Conditions
        assert "Grinnell Glacier" in content
        assert "Going-to-the-Sun Road is closed" in content
        assert "Road Crew Closure" in content
        assert "Fish Creek CG" in content
        # Notices, Peak, Product
        assert "Book Club on 5/29" in content
        assert "Blackfoot Mountain" in content
        assert "Red Bus Hiking Stick Medallion" in content
