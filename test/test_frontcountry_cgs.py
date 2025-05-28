import pytest

import trails_and_cgs.frontcountry_cgs as cgs_mod


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
