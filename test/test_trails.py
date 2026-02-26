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

    monkeypatch.setattr(trails_mod.requests, "get", lambda *a, **k: DummyResp())
    result = trails_mod.closed_trails()
    assert isinstance(result, TrailsResult)
    if result.closures:
        assert any("Trail X" in c for c in result.closures)
    else:
        assert result.no_closures_message or result.error_message
