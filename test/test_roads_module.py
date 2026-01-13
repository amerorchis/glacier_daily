"""
Unit tests for roads.roads module.

Tests the road closure fetching and formatting functions that interface
with the NPS API.
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from roads.Road import Road
from roads.roads import (
    NPSWebsiteError,
    closed_roads,
    format_road_closures,
    get_road_status,
)


class TestClosedRoads:
    """Tests for the closed_roads() function."""

    def test_request_exception_raises_nps_error(self):
        """Verify NPSWebsiteError raised on request failure."""
        with patch("roads.roads.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection failed")
            with pytest.raises(NPSWebsiteError):
                closed_roads()

    def test_empty_features_returns_empty_string(self):
        """Verify empty string returned when no closures exist."""
        mock_response = Mock()
        mock_response.text = json.dumps({"features": []})
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            assert result == ""

    def test_no_features_key_returns_empty_string(self):
        """Verify empty string returned when features key is missing."""
        mock_response = Mock()
        mock_response.text = json.dumps({})
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            assert result == ""

    def test_standard_road_closure_parsed(self):
        """Verify standard road closures are correctly parsed."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Going-to-the-Sun Road",
                            "status": "closed",
                            "reason": "snow",
                        },
                        "geometry": {
                            "coordinates": [
                                [-113.87562, 48.61694],  # West
                                [-113.5, 48.7],
                                [-113.44056, 48.74784],  # East
                            ]
                        },
                    }
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            assert "Going-to-the-Sun Road" in result
            assert isinstance(result, dict)

    def test_inside_north_fork_road_maps_to_kintla(self):
        """Verify Inside North Fork Road maps to Kintla Road when above threshold."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Inside North Fork Road",
                            "status": "closed",
                            "reason": "snow",
                        },
                        "geometry": {
                            "coordinates": [
                                [-114.3, 48.8],  # Above 48.787 threshold
                                [-114.35, 48.9],  # Above threshold
                            ]
                        },
                    }
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            assert "Kintla Road" in result

    def test_inside_north_fork_road_below_threshold_ignored(self):
        """Verify Inside North Fork Road coordinates below threshold are ignored."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Inside North Fork Road",
                            "status": "closed",
                            "reason": "snow",
                        },
                        "geometry": {
                            "coordinates": [
                                [-114.3, 48.5],  # Below 48.787 threshold
                                [-114.35, 48.6],  # Below threshold
                            ]
                        },
                    }
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            # Kintla Road should not have closures_found since coords below threshold
            assert result.get("Kintla Road") is None or not result.get("Kintla Road")

    def test_two_medicine_road_name_fixed(self):
        """Verify Two Medicine Road name is corrected from 'to Running Eagle' variant."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Two Medicine to Running Eagle",
                            "status": "closed",
                            "reason": "maintenance",
                        },
                        "geometry": {"coordinates": [[-113.4, 48.5], [-113.35, 48.55]]},
                    }
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            assert "Two Medicine Road" in result

    def test_nested_coordinates_handled(self):
        """Verify single-element coordinate arrays are unwrapped correctly."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Camas Road",
                            "status": "closed",
                            "reason": "snow",
                        },
                        "geometry": {
                            "coordinates": [
                                [[-113.9, 48.6], [-113.8, 48.65]]
                            ]  # Nested in extra array
                        },
                    }
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            assert "Camas Road" in result


class TestFormatRoadClosures:
    """Tests for the format_road_closures() function."""

    def test_no_closures_returns_no_closures_message(self):
        """Verify appropriate message when no roads are closed."""
        result = format_road_closures({})
        assert "no closures on major roads" in result.lower()

    def test_single_road_entirely_closed(self):
        """Verify formatting when one road is entirely closed."""
        road = Road("Camas Road")
        road.west_loc = "the beginning*"
        road.east_loc = "the end*"
        road.closures_found = True

        result = format_road_closures({"Camas Road": road})
        assert "in its entirety" in result.lower()

    def test_multiple_roads_entirely_closed(self):
        """Verify formatting when multiple roads are entirely closed."""
        road1 = Road("Camas Road")
        road1.west_loc = "start*"
        road1.east_loc = "end*"
        road1.closures_found = True

        road2 = Road("Two Medicine Road")
        road2.west_loc = "start*"
        road2.east_loc = "end*"
        road2.closures_found = True

        result = format_road_closures({"Camas Road": road1, "Two Medicine Road": road2})
        assert "and" in result  # Should join multiple with "and"
        assert "in their entirety" in result.lower()

    def test_partial_closure_formatted(self):
        """Verify partial closures are formatted correctly."""
        road = Road("Going-to-the-Sun Road")
        road.west_loc = "Lake McDonald Lodge"
        road.east_loc = "Rising Sun"
        road.closures_found = True

        result = format_road_closures({"Going-to-the-Sun Road": road})
        assert "closed from" in result.lower()
        assert "<ul" in result  # Should be formatted as list

    def test_same_location_closure_excluded(self):
        """Verify closures with same start/end location are excluded."""
        road = Road("Going-to-the-Sun Road")
        road.west_loc = "Lake McDonald Lodge"
        road.east_loc = "Lake McDonald Lodge"  # Same as west
        road.closures_found = True

        result = format_road_closures({"Going-to-the-Sun Road": road})
        # Should not include this closure since start == end
        assert "Lake McDonald Lodge" not in result or "no closures" in result.lower()


class TestGetRoadStatus:
    """Tests for the get_road_status() wrapper function."""

    def test_http_error_returns_empty_string(self):
        """Verify empty string returned on HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_response.text = '{"features": []}'

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = get_road_status()
            assert result == ""

    def test_nps_website_error_returns_down_message(self):
        """Verify website down message on NPS error."""
        with patch("roads.roads.closed_roads") as mock_closed:
            mock_closed.side_effect = NPSWebsiteError()
            result = get_road_status()
            assert "currently down" in result

    def test_success_returns_formatted_closures(self):
        """Verify successful path returns formatted road closures."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Going-to-the-Sun Road",
                            "status": "closed",
                            "reason": "snow",
                        },
                        "geometry": {
                            "coordinates": [
                                [-113.87562, 48.61694],
                                [-113.44056, 48.74784],
                            ]
                        },
                    }
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = get_road_status()
            assert isinstance(result, str)
            # Should return either formatted HTML or no closures message
            assert "<" in result or "no closures" in result.lower()
