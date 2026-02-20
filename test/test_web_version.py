import os
import tempfile

import pytest

from web_version import DailyUpdate, Subscriber, myClass, web_version


@pytest.fixture
def sample_data():
    return {
        "date": "2025-05-28",
        "today": "May 28, 2025",
        "events": "<ul><li>Event 1</li></ul>",
        "weather1": "Weather info 1",
        "weather_image": "https://example.com/weather.png",
        "weather2": "Weather info 2",
        "season": "summer",
        "trails": "<ul><li>Trail info</li></ul>",
        "campgrounds": "<ul><li>Campground info</li></ul>",
        "roads": "<ul><li>Road info</li></ul>",
        "hikerbiker": "<ul><li>Hiker/Biker info</li></ul>",
        "notices": "<ul><li>Notice info</li></ul>",
        "peak": "Peak info",
        "peak_image": "https://example.com/peak.jpg",
        "peak_map": "https://example.com/peak_map",
        "product_link": "https://example.com/product",
        "product_image": "https://example.com/product.jpg",
        "product_title": "Product Title",
        "product_desc": "Product Description",
        "image_otd": "https://example.com/image.jpg",
        "image_otd_title": "Image Title",
        "image_otd_link": "https://example.com/image_link",
        "sunrise_vid": "",
        "sunrise_still": "",
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
        # Use the default template, which is safe for test
        web_version(
            sample_data, file_name=out_file, template_path="email_template.html"
        )
        assert os.path.exists(out_file)
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        assert "Glacier Daily Update" in content or "Glacier National Park" in content
        assert "May 28, 2025" in content


def test_web_version_printable_removes_styles(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "printable.html")
        web_version(sample_data, file_name=out_file, template_path="printable.html")
        with open(out_file, encoding="utf-8") as f:
            content = f.read()
        # Should not have font-size:12px or line-height:18px in printable
        assert "font-size:12px;" not in content
        assert "line-height:18px;" not in content
        assert "May 28, 2025" in content
