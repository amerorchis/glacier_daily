import json
from datetime import datetime
from unittest.mock import patch

import trails_and_cgs.frontcountry_cgs as cgs_mod
from shared.data_types import CampgroundsResult


def _make_response(rows):
    """Build a fake requests.Response with the given campground rows."""

    class DummyResp:
        text = json.dumps({"rows": rows})

    return DummyResp()


def _cg(name, status="closed", service_status="", description=""):
    return {
        "name": name,
        "status": status,
        "service_status": service_status,
        "description": description,
    }


def _mock_month(month):
    """Return a patcher that pins now_mountain() to the given month."""
    fake = datetime(2026, month, 15, 10, 0, 0)
    return patch.object(cgs_mod, "now_mountain", return_value=fake)


# --- Seasonal detection ---


def test_hard_floor_january_groups_all_non_year_round(monkeypatch):
    """Jan-Apr: all non-year-round closures are seasonal, regardless of service_status."""
    rows = [
        _cg("Rising Sun", service_status="Open for the Season"),
        _cg("Many Glacier", service_status="Closed in 2025"),
        _cg("Apgar", service_status="Open for the Season"),
    ]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(1):
        result = cgs_mod.campground_alerts()
    # Rising Sun and Many Glacier are seasonal; Apgar is year-round → individual
    assert any("Apgar CG: currently closed" in s for s in result.statuses)
    # Seasonal line suppressed in Jan (outside display months), so no grouped line
    assert not any("season" in s.lower() for s in result.statuses)


def test_hard_floor_april_displays_seasonal_line(monkeypatch):
    """April is both a hard-floor month AND a display month."""
    rows = [
        _cg("Cut Bank", service_status="Open for the Season"),
        _cg("Fish Creek", service_status="Open for the Season"),
    ]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(4):
        result = cgs_mod.campground_alerts()
    assert any("Not yet open for the season" in s for s in result.statuses)
    assert "Cut Bank" in result.statuses[-1]
    assert "Fish Creek" in result.statuses[-1]


def test_case_insensitive_season_match_in_summer(monkeypatch):
    """May-Dec: case-insensitive 'season' check catches 'Season' in service_status."""
    rows = [
        _cg("Sprague Creek", service_status="Closed for the season"),
        _cg("Rising Sun", service_status="Open for the Season"),
    ]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(5):
        result = cgs_mod.campground_alerts()
    seasonal_line = [s for s in result.statuses if "season" in s.lower()]
    assert len(seasonal_line) == 1
    assert "Sprague Creek" in seasonal_line[0]
    assert "Rising Sun" in seasonal_line[0]


def test_specific_closure_not_grouped_in_summer(monkeypatch):
    """May-Dec: closure without 'season' in service_status stays individual."""
    rows = [
        _cg("Fish Creek", service_status="Posted for Bear Frequenting"),
    ]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(7):
        result = cgs_mod.campground_alerts()
    assert any("Fish Creek CG: currently closed" in s for s in result.statuses)
    assert not any("season" in s.lower() for s in result.statuses)


def test_year_round_cg_always_individual(monkeypatch):
    """Year-round campgrounds show individually even without 'season' text."""
    rows = [_cg("St Mary", service_status="some reason")]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(2):
        result = cgs_mod.campground_alerts()
    assert any("St Mary CG: currently closed" in s for s in result.statuses)


# --- Display months ---


def test_seasonal_line_hidden_in_december(monkeypatch):
    """Dec-Mar: seasonal closures detected but not displayed."""
    rows = [_cg("Bowman Lake", service_status="Closed for the season")]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(12):
        result = cgs_mod.campground_alerts()
    assert result.statuses == []


def test_seasonal_line_shown_in_november(monkeypatch):
    """November: seasonal closures displayed with 'Closed for the season' phrasing."""
    rows = [_cg("Bowman Lake", service_status="Closed for the season")]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(11):
        result = cgs_mod.campground_alerts()
    assert any("Closed for the season: Bowman Lake" in s for s in result.statuses)


def test_phrasing_not_yet_open_before_august(monkeypatch):
    """Apr-Jul: uses 'Not yet open for the season' phrasing."""
    rows = [_cg("Avalanche Creek", service_status="Closed for the season")]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(6):
        result = cgs_mod.campground_alerts()
    assert any("Not yet open for the season" in s for s in result.statuses)


def test_phrasing_closed_for_season_aug_onward(monkeypatch):
    """Aug+: uses 'Closed for the season' phrasing."""
    rows = [_cg("Avalanche Creek", service_status="Closed for the season")]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(9):
        result = cgs_mod.campground_alerts()
    assert any("Closed for the season" in s for s in result.statuses)


# --- Error handling ---


def test_campground_alerts_down(monkeypatch):
    class DummyResp:
        text = "{}"

    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: DummyResp())
    result = cgs_mod.campground_alerts()
    assert isinstance(result, CampgroundsResult)
    assert "currently down" in result.error_message


# --- Notice extraction ---


def test_notice_extraction(monkeypatch):
    rows = [
        _cg(
            "Fish Creek",
            status="open",
            service_status="Open for the Season",
            description=(
                "Camping only. "
                '<br><br><a href="https://www.nps.gov/glac/planyourvisit/'
                'reservation-campgrounds.htm" target="_blank">'
                "Campground Details</a><br><br>Some extra info."
            ),
        ),
    ]
    monkeypatch.setattr(cgs_mod.requests, "get", lambda *a, **k: _make_response(rows))
    with _mock_month(7):
        result = cgs_mod.campground_alerts()
    assert any("Fish Creek CG:" in s for s in result.statuses)
