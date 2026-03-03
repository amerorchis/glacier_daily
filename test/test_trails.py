import json

import trails_and_cgs.trails as trails_mod
from shared.data_types import TrailsResult


def test_remove_duplicate_trails():
    trail_list = [
        {
            "properties": {"name": "Trail A"},
            "geometry": {"coordinates": [[(0, 0), (1, 1), (2, 2)]]},
        },
        {
            "properties": {"name": "Trail A"},
            "geometry": {"coordinates": [[(0, 0), (1, 1)]]},
        },
        {
            "properties": {"name": "Trail B"},
            "geometry": {"coordinates": [[(3, 3), (4, 4), (5, 5)]]},
        },
        {
            "properties": {"name": "Trail B cutoff"},
            "geometry": {"coordinates": [[(3, 3), (4, 4), (5, 5)]]},
        },
    ]
    result = trails_mod.remove_duplicate_trails(trail_list)
    # Only the longest Trail A, Trail B, and not the cutoff
    names = [t["name"] for t in result]
    assert "Trail A" in names and "Trail B" in names
    assert not any("cutoff" in n.lower() for n in names)


def test_closed_trails_returns_trails_result(monkeypatch):
    # Patch requests.get to return a fake closed trail
    class DummyResp:
        text = '{"features": [{"properties": {"name": "Trail X", "trail_status_info": "CLOSED", "location": "Somewhere"}, "geometry": {"coordinates": [[0,0],[1,1],[2,2]]}}]}'

        def raise_for_status(self):
            pass

    monkeypatch.setattr(trails_mod.requests, "get", lambda *a, **k: DummyResp())
    result = trails_mod.closed_trails()
    assert isinstance(result, TrailsResult)
    if result.closures:
        assert any("Trail X" in c for c in result.closures)
    else:
        assert result.no_closures_message or result.error_message


def _make_geojson(features_props: list[dict]) -> str:
    """Helper: build a GeoJSON string from a list of property dicts."""
    features = [
        {
            "properties": props,
            "geometry": {"coordinates": [[0, 0], [1, 1], [2, 2]]},
        }
        for props in features_props
    ]
    return json.dumps({"features": features})


def test_trail_with_status_reason(monkeypatch):
    """Trail using status_reason (instead of trail_status_info) should appear in closures."""

    class DummyResp:
        text = _make_geojson(
            [
                {
                    "name": "Highline",
                    "status_reason": "CLOSED for snow",
                    "location": "Logan Pass",
                }
            ]
        )

        def raise_for_status(self):
            pass

    monkeypatch.setattr(trails_mod.requests, "get", lambda *a, **k: DummyResp())
    result = trails_mod.closed_trails()
    assert isinstance(result, TrailsResult)
    assert result.closures
    assert any("Highline" in c for c in result.closures)
    # status_reason should have CLOSED lowercased
    assert any("closed for snow" in c for c in result.closures)


def test_trail_with_neither_reason_field(monkeypatch):
    """Trail with neither status_reason nor trail_status_info should not raise UnboundLocalError."""

    class DummyResp:
        text = _make_geojson([{"name": "Mystery Trail", "location": "Somewhere"}])

        def raise_for_status(self):
            pass

    monkeypatch.setattr(trails_mod.requests, "get", lambda *a, **k: DummyResp())
    # Before the A1 fix this would raise UnboundLocalError
    result = trails_mod.closed_trails()
    assert isinstance(result, TrailsResult)
    # The closure should exist with an empty reason
    if result.closures:
        assert any("Mystery Trail" in c for c in result.closures)


def test_trail_with_empty_location(monkeypatch):
    """When location is empty, msg should be '{name}: {reason}' without ' - ' suffix."""

    class DummyResp:
        text = _make_geojson(
            [
                {
                    "name": "Grinnell Glacier",
                    "status_reason": "CLOSED for safety",
                    "location": "",
                }
            ]
        )

        def raise_for_status(self):
            pass

    monkeypatch.setattr(trails_mod.requests, "get", lambda *a, **k: DummyResp())
    result = trails_mod.closed_trails()
    assert isinstance(result, TrailsResult)
    assert result.closures
    closure = next(c for c in result.closures if "Grinnell Glacier" in c)
    assert closure == "Grinnell Glacier: closed for safety"
    # Should NOT contain the " - " location separator
    assert " - " not in closure


def test_fetch_trail_data_returns_none(monkeypatch):
    """When _fetch_trail_data returns None, closed_trails should return a TrailsResult with error_message."""
    monkeypatch.setattr(trails_mod, "_fetch_trail_data", lambda: None)
    result = trails_mod.closed_trails()
    assert isinstance(result, TrailsResult)
    assert result.error_message
    assert not result.closures


def test_reasons_to_ignore_filtering(monkeypatch):
    """Closures matching reasons_to_ignore should be filtered out."""

    class DummyResp:
        text = _make_geojson(
            [
                {
                    "name": "Swiftcurrent Pass",
                    "status_reason": "Closed Due To Bear Activity",
                    "location": "",
                },
                {
                    "name": "Avalanche Lake",
                    "status_reason": "CLOSED for hazard trees",
                    "location": "Trail of the Cedars",
                },
            ]
        )

        def raise_for_status(self):
            pass

    monkeypatch.setattr(trails_mod.requests, "get", lambda *a, **k: DummyResp())
    result = trails_mod.closed_trails()
    assert isinstance(result, TrailsResult)
    # Swiftcurrent Pass bear activity closure should be filtered out
    assert not any("Swiftcurrent Pass" in c for c in result.closures)
    # Avalanche Lake should still be present
    assert any("Avalanche Lake" in c for c in result.closures)


def test_get_closed_trails_catches_exceptions(monkeypatch):
    """get_closed_trails should catch KeyError and return an empty TrailsResult."""
    monkeypatch.setattr(
        trails_mod, "closed_trails", lambda: (_ for _ in ()).throw(KeyError("boom"))
    )
    result = trails_mod.get_closed_trails()
    assert isinstance(result, TrailsResult)
    assert not result.closures
    assert not result.error_message
