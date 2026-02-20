import json
from datetime import datetime
from unittest.mock import patch

import requests

import trails_and_cgs.frontcountry_cgs as cgs_mod


def _make_cg_response(rows):
    """Create a mock response with given campground rows."""

    class DummyResp:
        def __init__(self, data):
            self.text = json.dumps({"rows": data})

    return DummyResp(rows)


def _make_campground(name, status="open", service_status="", description=""):
    """Create a single campground row dict."""
    return {
        "name": name,
        "status": status,
        "service_status": service_status,
        "description": description,
    }


def test_campground_alerts_html(monkeypatch):
    # Patch requests.get to return a fake campground
    class DummyResp:
        text = '{"rows": [{"name": "Fish Creek", "status": "closed", "service_status": "season", "description": "Camping only. <br><br><a href=\\"https://www.nps.gov/glac/planyourvisit/reservation-campgrounds.htm\\" target=\\"_blank\\">Campground Details</a><br><br>"}]}'

    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: DummyResp())
    html = cgs_mod.campground_alerts()
    assert "Fish Creek" in html or "campgrounds page" in html


def test_campground_alerts_down(monkeypatch):
    class DummyResp:
        text = "{}"

    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: DummyResp())
    html = cgs_mod.campground_alerts()
    assert "currently down" in html


def test_campground_seasonal_closure_after_august(monkeypatch):
    """Seasonal closures after August should say 'Closed for the season'."""
    rows = [_make_campground("Sprague Creek", status="closed", service_status="season")]
    monkeypatch.setattr(
        cgs_mod.requests, "get", lambda *a, **k: _make_cg_response(rows)
    )
    monkeypatch.setattr(cgs_mod, "now_mountain", lambda: datetime(2024, 9, 15))
    html = cgs_mod.campground_alerts()
    assert "Closed for the season" in html
    assert "Sprague Creek" in html


def test_campground_seasonal_closure_before_august(monkeypatch):
    """Seasonal closures before August should say 'Not yet open'."""
    rows = [_make_campground("Sprague Creek", status="closed", service_status="season")]
    monkeypatch.setattr(
        cgs_mod.requests, "get", lambda *a, **k: _make_cg_response(rows)
    )
    with patch.object(cgs_mod, "now_mountain", return_value=datetime(2024, 5, 15)):
        html = cgs_mod.campground_alerts()
    assert "Not yet open" in html


def test_campground_non_seasonal_closure(monkeypatch):
    """Non-seasonal closures should say 'currently closed'."""
    rows = [_make_campground("Many Glacier", status="closed", service_status="other")]
    monkeypatch.setattr(
        cgs_mod.requests, "get", lambda *a, **k: _make_cg_response(rows)
    )
    html = cgs_mod.campground_alerts()
    assert "currently closed" in html
    assert "Many Glacier" in html


def test_campground_camping_only_notice(monkeypatch):
    """Campgrounds with 'camping only' notice should include it."""
    rows = [
        _make_campground(
            "Fish Creek",
            status="open",
            description="Camping only. No generators.",
        )
    ]
    monkeypatch.setattr(
        cgs_mod.requests, "get", lambda *a, **k: _make_cg_response(rows)
    )
    html = cgs_mod.campground_alerts()
    assert "Fish Creek" in html
    assert "Camping only" in html


def test_campground_no_statuses(monkeypatch):
    """All campgrounds open with no notices should return empty string."""
    rows = [_make_campground("Apgar", status="open", description="")]
    monkeypatch.setattr(
        cgs_mod.requests, "get", lambda *a, **k: _make_cg_response(rows)
    )
    html = cgs_mod.campground_alerts()
    assert html == ""


def test_campground_missing_rows_key(monkeypatch):
    """Missing 'rows' key returns 'currently down' message."""

    class DummyResp:
        text = json.dumps({"error": "bad query"})

    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: DummyResp())
    html = cgs_mod.campground_alerts()
    assert "currently down" in html


def test_campground_request_exception(monkeypatch):
    """RequestException should return 'currently down' message."""

    def raise_exc(*a, **k):
        raise requests.exceptions.RequestException("timeout")

    monkeypatch.setattr(cgs_mod.requests, "get", raise_exc)
    html = cgs_mod.campground_alerts()
    assert "currently down" in html


def test_campground_json_decode_error(monkeypatch):
    """Invalid JSON should return 'currently down' message."""

    class DummyResp:
        text = "not valid json {{"

    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: DummyResp())
    html = cgs_mod.campground_alerts()
    assert "currently down" in html


def test_get_campground_status_success(monkeypatch):
    """Wrapper returns result from campground_alerts on success."""
    monkeypatch.setattr(cgs_mod, "campground_alerts", lambda: "campground html")
    result = cgs_mod.get_campground_status()
    assert result == "campground html"


def test_get_campground_status_error(monkeypatch):
    """Wrapper catches HTTPError and returns empty string."""

    def raise_http():
        raise requests.exceptions.HTTPError("500")

    monkeypatch.setattr(cgs_mod, "campground_alerts", raise_http)
    result = cgs_mod.get_campground_status()
    assert result == ""
