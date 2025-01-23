import sys
import os
from unittest.mock import patch, Mock
import pytest
import requests
import json

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pragma: no cover

from roads.hiker_biker import get_hiker_biker_status, hiker_biker
from roads.HikerBiker import HikerBiker
from roads.Road import Road
from typing import Dict, Optional


@pytest.fixture
def mock_gtsr():
    """Mock GTSR road object"""
    road = Road("Going-to-the-Sun Road")
    road.west = (-113.87562, 48.61694)  # Lake McDonald Lodge coordinates
    road.east = (-113.44056, 48.74784)  # St. Mary Visitor Center coordinates
    road.coords_set = True
    return road


@pytest.fixture
def mock_closure_data():
    """Mock closure data"""
    return {
        "features": [
            {
                "properties": {"name": "Road Crew Closure", "status": "active"},
                "geometry": {
                    "coordinates": [-113.80047, 48.75494]  # The Loop coordinates
                },
            },
            {
                "properties": {"name": "Avalanche Hazard Closure", "status": "active"},
                "geometry": {
                    "coordinates": [
                        -113.74776,
                        48.73928,
                    ]  # Bird Woman Falls coordinates
                },
            },
        ]
    }


def test_hiker_biker_init(mock_gtsr):
    """Test HikerBiker class initialization"""
    hb = HikerBiker("Test Closure", (-113.80047, 48.75494), mock_gtsr)
    assert isinstance(hb, HikerBiker)
    assert hb.name == "Test Closure"
    assert hb.north == (-113.80047, 48.75494)


def test_get_side_west(mock_gtsr):
    """Test west side detection"""
    hb = HikerBiker("Test West", (-113.80047, 48.75494), mock_gtsr)
    assert hb.get_side() == "west"


def test_get_side_east(mock_gtsr):
    """Test east side detection"""
    hb = HikerBiker("Test East", (-113.65335, 48.67815), mock_gtsr)
    assert hb.get_side() == "east"


def test_get_side_logan(mock_gtsr):
    """Test Logan Pass area detection"""
    hb = HikerBiker("Test Logan", (-113.71800, 48.69659), mock_gtsr)
    assert hb.get_side() == "logan"


def test_closure_distance_calculation_west(mock_gtsr):
    """Test distance calculation from west entrance"""
    hb = HikerBiker("Test West", (-113.80047, 48.75494), mock_gtsr)
    closure_str = hb.closure_dist("west", mock_gtsr)
    assert "miles from gate" in closure_str
    assert "Lake McDonald Lodge" in closure_str


def test_closure_distance_calculation_east(mock_gtsr):
    """Test distance calculation from east entrance"""
    hb = HikerBiker("Test East", (-113.65335, 48.67815), mock_gtsr)
    closure_str = hb.closure_dist("east", mock_gtsr)
    assert "miles from gate" in closure_str


def test_closure_distance_logan(mock_gtsr):
    """Test distance calculation at Logan Pass"""
    hb = HikerBiker("Test Logan", (-113.71800, 48.69659), mock_gtsr)
    closure_str = hb.closure_dist("logan", mock_gtsr)
    assert "32 miles up" in closure_str


@patch("requests.get")
def test_hiker_biker_status_success(mock_get, mock_closure_data, mock_gtsr):
    """Test successful status retrieval"""

    def mock_closed_roads() -> Dict[str, Optional[Road]]:
        mock_gtsr.west_loc = ("Lake McDonald Lodge", 10.7)
        mock_gtsr.east_loc = ("Rising Sun", 43.4)
        return {"Going-to-the-Sun Road": mock_gtsr}

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps(mock_closure_data)
    mock_get.return_value = mock_response

    with patch("roads.hiker_biker.closed_roads", side_effect=mock_closed_roads):
        result = get_hiker_biker_status()
        print(result)
        assert isinstance(result, str)
        assert "Road Crew Closure" in result
        assert "Avalanche Hazard Closure" in result
        assert "Road Crew Closures are in effect during work hours" in result
        assert "miles from gate at Lake McDonald Lodge" in result


@patch("requests.get")
def test_hiker_biker_status_no_closures(mock_get, mock_gtsr):
    """Test when no closures are present"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"features": []})
    mock_get.return_value = mock_response

    def mock_closed_roads() -> Dict[str, Optional[Road]]:
        mock_gtsr.west_loc = ("Lake McDonald Lodge", 10.7)
        mock_gtsr.east_loc = ("Rising Sun", 43.4)
        return {"Going-to-the-Sun Road": mock_gtsr}

    with patch("roads.hiker_biker.closed_roads", side_effect=mock_closed_roads):
        result = get_hiker_biker_status()
        assert result == ""


@patch("requests.get")
def test_hiker_biker_status_error_handling(mock_get):
    """Test error handling"""
    mock_get.side_effect = requests.exceptions.HTTPError("Test error")
    result = get_hiker_biker_status()
    assert result == ""


def test_hiker_biker_string_representation(mock_gtsr):
    """Test string representation of HikerBiker object"""
    hb = HikerBiker("Test Closure", (-113.80047, 48.75494), mock_gtsr)
    string_rep = str(hb)
    assert isinstance(string_rep, str)
    assert "miles from gate" in string_rep

    """Test behavior when GTSR info is not available"""
    import urllib3

    urllib3.disable_warnings()
    result = hiker_biker()
    assert result == ""


def test_closure_location_names(mock_gtsr):
    """Test that closure locations are correctly named"""
    hb = HikerBiker("Test Closure", (-113.80047, 48.75494), mock_gtsr)
    hb.closure_loc()
    assert "The Loop" in hb.closure_str


def test_multiple_closures_sorting(mock_gtsr):
    """Test that multiple closures are properly sorted"""
    closures = [
        HikerBiker("East Closure", (-113.65335, 48.67815), mock_gtsr),
        HikerBiker("West Closure", (-113.80047, 48.75494), mock_gtsr),
    ]
    closure_strings = [str(c) for c in closures]
    assert all("East - " in c or "West - " in c for c in closure_strings)


def test_invalid_coordinates(mock_gtsr):
    """Test handling of invalid coordinates"""
    hb = HikerBiker("Invalid Test", (0, 0), mock_gtsr)
    str_ = str(hb)
    assert "name of location not found" in str_
