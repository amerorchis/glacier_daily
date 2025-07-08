import builtins
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generate_and_upload as gau


def make_fake_weather():
    class FakeWeather:
        message1 = "Weather1"
        message2 = "Weather2"
        season = "summer"
        results = [1, 2, 3]

    return FakeWeather()


def test_gen_data(monkeypatch):
    # Patch all the data sources to return simple values
    monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
    monkeypatch.setattr(gau, "get_closed_trails", lambda: "trails")
    monkeypatch.setattr(gau, "get_campground_status", lambda: "campgrounds")
    monkeypatch.setattr(gau, "get_road_status", lambda: "roads")
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: "hikerbiker")
    monkeypatch.setattr(gau, "events_today", lambda: "events")
    monkeypatch.setattr(gau, "get_image_otd", lambda: ("img", "img_title", "img_link"))
    monkeypatch.setattr(gau, "peak", lambda: ("peak", "peak_img", "peak_map"))
    monkeypatch.setattr(gau, "process_video", lambda: ("vid", "still"))
    monkeypatch.setattr(
        gau, "get_product", lambda: ("prod_title", "prod_img", "prod_link", "prod_desc")
    )
    monkeypatch.setattr(gau, "get_notices", lambda: "notices")
    monkeypatch.setattr(gau, "html_safe", lambda x: x)
    monkeypatch.setattr(gau, "weather_image", lambda x: "weather_img")

    data = gau.gen_data()
    # Check that all expected keys are present
    for key in [
        "date",
        "today",
        "events",
        "weather1",
        "weather_image",
        "weather2",
        "season",
        "trails",
        "campgrounds",
        "roads",
        "hikerbiker",
        "notices",
        "peak",
        "peak_image",
        "peak_map",
        "product_link",
        "product_image",
        "product_title",
        "product_desc",
        "image_otd",
        "image_otd_title",
        "image_otd_link",
        "sunrise_vid",
        "sunrise_still",
    ]:
        assert key in data


def test_write_data_to_json(tmp_path, monkeypatch):
    # Patch get_gnpc_events to avoid network
    monkeypatch.setattr(gau, "get_gnpc_events", lambda: "gnpc_events")
    fake_data = {"foo": "bar", "baz": "qux"}
    out = gau.write_data_to_json(fake_data, "test.json")
    assert out.endswith("test.json")
    # Check file contents
    with open(out, "r", encoding="utf-8") as f:
        content = f.read()
        assert "foo" in content and "baz" in content and "gnpc-events" in content


def test_send_to_server(monkeypatch):
    called = {}
    monkeypatch.setattr(
        gau,
        "upload_file",
        lambda d, f, p: called.update({"dir": d, "file": f, "path": p}),
    )
    gau.send_to_server("/tmp/test.json", "api")
    assert called["dir"] == "api"
    assert called["file"] == "test.json"
    assert called["path"] == "/tmp/test.json"


def test_serve_api(monkeypatch, tmp_path):
    # Patch everything to avoid side effects
    monkeypatch.setattr(gau, "gen_data", lambda: {"foo": "bar"})
    monkeypatch.setattr(gau, "web_version", lambda data, *a, **k: "webfile")
    monkeypatch.setattr(
        gau, "write_data_to_json", lambda data, doctype: str(tmp_path / "email.json")
    )
    monkeypatch.setattr(gau, "send_to_server", lambda file, directory: None)
    # Should not raise
    gau.serve_api()
