import json

import requests

import trails_and_cgs.trails as trails_mod


def _make_trail_response(trails):
    """Create a mock response with given trail features."""

    class DummyResp:
        def __init__(self, features):
            self.text = json.dumps({"features": features})

    return DummyResp(trails)


def _make_trail(
    name, status_reason=None, trail_status_info=None, location="Somewhere", coord_len=5
):
    """Create a single trail feature dict."""
    return {
        "properties": {
            "name": name,
            "status_reason": status_reason,
            "trail_status_info": trail_status_info,
            "location": location,
        },
        "geometry": {
            "coordinates": [[(i, i) for i in range(coord_len)]],
        },
    }


def test_remove_duplicate_trails():
    trail_list = [
        {
            "properties": {"name": "Trail A"},
            "geometry": {"coordinates": [[(0, 0), (1, 1), (2, 2)]]},
        },
        {
            "properties": {"name": "Trail A"},
            "geometry": {"coordinates": [[(0, 0), (1, 1), (2, 2), (3, 3)]]},
        },
        {
            "properties": {"name": "Trail B"},
            "geometry": {"coordinates": [[(0, 0), (1, 1), (2, 2), (3, 3)]]},
        },
        {
            "properties": {"name": "Trail Cutoff"},
            "geometry": {"coordinates": [[(0, 0), (1, 1), (2, 2), (3, 3)]]},
        },
    ]
    result = trails_mod.remove_duplicate_trails(trail_list)
    # Only the longest Trail A, Trail B, and not the cutoff
    names = [t["name"] for t in result]
    assert "Trail A" in names and "Trail B" in names
    assert not any("cutoff" in n.lower() for n in names)


def test_remove_duplicate_trails_short_trail():
    """Trail with 2 or fewer coordinates should be excluded."""
    trail_list = [
        {
            "properties": {"name": "Tiny Trail"},
            "geometry": {"coordinates": [[(0, 0), (1, 1)]]},
        },
    ]
    result = trails_mod.remove_duplicate_trails(trail_list)
    assert len(result) == 0


def test_closed_trails_with_status_reason(monkeypatch):
    """Trails with status_reason should use that field."""
    trails = [
        _make_trail("Trail X", status_reason="CLOSED for bears"),
        _make_trail("Trail Y", status_reason="CLOSED for construction"),
    ]
    monkeypatch.setattr(
        trails_mod.requests, "get", lambda *a, **k: _make_trail_response(trails)
    )
    html = trails_mod.closed_trails()
    # closures.pop() removes last one, so Trail X should remain
    assert "Trail X" in html
    assert "closed for bears" in html  # CLOSED -> closed


def test_closed_trails_with_trail_status_info(monkeypatch):
    """Trails without status_reason should fall back to trail_status_info."""
    trails = [
        _make_trail("Trail A", trail_status_info="CLOSED due to snow"),
        _make_trail("Trail B", trail_status_info="CLOSED for maintenance"),
    ]
    monkeypatch.setattr(
        trails_mod.requests, "get", lambda *a, **k: _make_trail_response(trails)
    )
    html = trails_mod.closed_trails()
    assert "Trail A" in html


def test_closed_trails_no_closures(monkeypatch):
    """Empty features list returns 'no trail closures' message."""
    monkeypatch.setattr(
        trails_mod.requests, "get", lambda *a, **k: _make_trail_response([])
    )
    html = trails_mod.closed_trails()
    assert "no trail closures" in html.lower()


def test_closed_trails_request_exception(monkeypatch):
    """RequestException should return a 'currently down' message."""

    def raise_exc(*a, **k):
        raise requests.exceptions.RequestException("timeout")

    monkeypatch.setattr(trails_mod.requests, "get", raise_exc)
    html = trails_mod.closed_trails()
    assert "currently down" in html


def test_closed_trails_missing_features_key(monkeypatch):
    """Missing 'features' key in JSON should return 'currently down'."""

    class DummyResp:
        text = json.dumps({"error": "bad query"})

    monkeypatch.setattr(trails_mod.requests, "get", lambda *a, **k: DummyResp())
    html = trails_mod.closed_trails()
    assert "currently down" in html


def test_closed_trails_filters_ignored_reasons(monkeypatch):
    """Closures matching ignored reasons should be filtered out."""
    trails = [
        _make_trail("Good Trail", status_reason="CLOSED for fire"),
        _make_trail("Swiftcurrent Pass", status_reason="Closed Due To Bear Activity"),
        _make_trail("Filler Trail", status_reason="CLOSED for safety"),
    ]
    monkeypatch.setattr(
        trails_mod.requests, "get", lambda *a, **k: _make_trail_response(trails)
    )
    html = trails_mod.closed_trails()
    assert "Good Trail" in html
    assert "Swiftcurrent Pass" not in html


def test_closed_trails_html_format(monkeypatch):
    """Verify HTML list format when closures exist."""
    trails = [
        _make_trail("Alpine Trail", status_reason="CLOSED for snow"),
        _make_trail("Boulder Trail", status_reason="CLOSED for rocks"),
        _make_trail("Cedar Trail", status_reason="CLOSED for mud"),
    ]
    monkeypatch.setattr(
        trails_mod.requests, "get", lambda *a, **k: _make_trail_response(trails)
    )
    html = trails_mod.closed_trails()
    assert "<ul" in html
    assert "<li>" in html


def test_get_closed_trails_catches_http_error(monkeypatch):
    """get_closed_trails wrapper catches HTTPError from closed_trails."""

    def raise_http():
        raise requests.exceptions.HTTPError("404")

    monkeypatch.setattr(trails_mod, "closed_trails", raise_http)
    result = trails_mod.get_closed_trails()
    assert result == ""


def test_get_closed_trails_catches_json_decode_error(monkeypatch):
    """get_closed_trails wrapper catches JSONDecodeError."""

    def raise_json():
        raise json.decoder.JSONDecodeError("fail", "", 0)

    monkeypatch.setattr(trails_mod, "closed_trails", raise_json)
    result = trails_mod.get_closed_trails()
    assert result == ""


def test_get_closed_trails_success(monkeypatch):
    """get_closed_trails returns result from closed_trails on success."""
    monkeypatch.setattr(trails_mod, "closed_trails", lambda: "trail closures html")
    result = trails_mod.get_closed_trails()
    assert result == "trail closures html"
