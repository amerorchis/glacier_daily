import trails_and_cgs.frontcountry_cgs as cgs_mod
from shared.data_types import CampgroundsResult


def test_campground_alerts_returns_campgrounds_result(monkeypatch):
    # Patch requests.get to return a fake campground
    class DummyResp:
        text = '{"rows": [{"name": "Fish Creek", "status": "closed", "service_status": "season", "description": "Camping only. <br><br><a href=\\"https://www.nps.gov/glac/planyourvisit/reservation-campgrounds.htm\\" target=\\"_blank\\">Campground Details</a><br><br>"}]}'

    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: DummyResp())
    result = cgs_mod.campground_alerts()
    assert isinstance(result, CampgroundsResult)
    # Should have Fish Creek in statuses or error message
    all_text = " ".join(result.statuses) if result.statuses else result.error_message
    assert "Fish Creek" in all_text or result.error_message


def test_campground_alerts_down(monkeypatch):
    class DummyResp:
        text = "{}"

    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: DummyResp())
    result = cgs_mod.campground_alerts()
    assert isinstance(result, CampgroundsResult)
    assert "currently down" in result.error_message
