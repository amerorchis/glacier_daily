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
    _fetch_open_segments,
    _get_segment_bounds,
    _is_covered_by_open,
    _segments_overlap,
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
        closed_response = Mock()
        closed_response.text = json.dumps(
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
        closed_response.raise_for_status = Mock()

        # Mock empty open segments so the closed segment is not skipped
        open_response = Mock()
        open_response.text = json.dumps({"features": []})
        open_response.raise_for_status = Mock()

        def mock_get(url, **kwargs):
            if "open" in url:
                return open_response
            return closed_response

        with patch("roads.roads.requests.get", side_effect=mock_get):
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

    def test_cut_bank_road_name_variants_normalized(self):
        """Verify Cut Bank Creek Road variants are normalized to match dictionary key."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Cut Bank Creek Road: Boundary to RS",
                            "status": "closed",
                            "reason": "seasonal",
                        },
                        "geometry": {
                            "coordinates": [
                                [-113.36777, 48.610241],  # park boundary
                                [-113.376876, 48.605817],  # ranger station
                            ]
                        },
                    },
                    {
                        "properties": {
                            "rdname": "Cut Bank Creek Road",
                            "status": "closed",
                            "reason": "winter",
                        },
                        "geometry": {
                            "coordinates": [
                                [-113.376868, 48.605844],  # ranger station
                                [-113.383718, 48.601878],  # campground
                            ]
                        },
                    },
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = closed_roads()
            # Both segments should be processed under the same road
            assert "Cut Bank Creek Road" in result
            road = result["Cut Bank Creek Road"]
            road.closure_string()
            # Road should be entirely closed since both endpoints are boundary markers
            assert road.entirely_closed

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


class TestSegmentBounds:
    """Tests for the _get_segment_bounds() helper function."""

    def test_simple_coordinates(self):
        """Verify bounds extracted from simple coordinate list."""
        coords = [[-113.9, 48.6], [-113.5, 48.7], [-113.4, 48.8]]
        west, east = _get_segment_bounds(coords)
        assert west == -113.9
        assert east == -113.4

    def test_nested_coordinates(self):
        """Verify bounds extracted from nested coordinate arrays."""
        coords = [[[-113.9, 48.6], [-113.5, 48.7]], [[-113.4, 48.8]]]
        west, east = _get_segment_bounds(coords)
        assert west == -113.9
        assert east == -113.4

    def test_single_point(self):
        """Verify bounds work with single coordinate."""
        coords = [[-113.5, 48.7]]
        west, east = _get_segment_bounds(coords)
        assert west == -113.5
        assert east == -113.5


class TestSegmentsOverlap:
    """Tests for the _segments_overlap() helper function."""

    def test_overlapping_segments(self):
        """Verify overlap detected when segments intersect."""
        seg1 = (-113.9, -113.5)  # West to mid
        seg2 = (-113.6, -113.4)  # Mid to east
        assert _segments_overlap(seg1, seg2) is True

    def test_non_overlapping_segments(self):
        """Verify no overlap when segments are separate."""
        seg1 = (-113.9, -113.7)  # Western segment
        seg2 = (-113.5, -113.4)  # Eastern segment
        assert _segments_overlap(seg1, seg2) is False

    def test_adjacent_segments(self):
        """Verify segments touching at a single point do NOT overlap."""
        seg1 = (-113.9, -113.6)
        seg2 = (-113.6, -113.4)  # Starts exactly where seg1 ends
        assert _segments_overlap(seg1, seg2) is False

    def test_contained_segment(self):
        """Verify overlap when one segment contains another."""
        seg1 = (-113.9, -113.4)  # Full road
        seg2 = (-113.7, -113.5)  # Smaller section inside
        assert _segments_overlap(seg1, seg2) is True

    def test_identical_segments(self):
        """Verify identical segments overlap."""
        seg1 = (-113.9, -113.5)
        seg2 = (-113.9, -113.5)
        assert _segments_overlap(seg1, seg2) is True


class TestIsCoveredByOpen:
    """Tests for the _is_covered_by_open() helper function."""

    def test_covered_by_open_segment(self):
        """Verify True when closed segment overlaps with open."""
        closed = (-113.9, -113.8)
        open_segments = {(-113.95, -113.75)}
        assert _is_covered_by_open(closed, open_segments) is True

    def test_not_covered_by_open(self):
        """Verify False when no overlap with open segments."""
        closed = (-113.9, -113.8)
        open_segments = {(-113.5, -113.4)}  # Completely separate
        assert _is_covered_by_open(closed, open_segments) is False

    def test_empty_open_segments(self):
        """Verify False when no open segments exist."""
        closed = (-113.9, -113.8)
        open_segments = set()
        assert _is_covered_by_open(closed, open_segments) is False

    def test_multiple_open_segments(self):
        """Verify True when any open segment overlaps."""
        closed = (-113.7, -113.6)
        open_segments = {
            (-113.9, -113.8),  # No overlap
            (-113.65, -113.5),  # Overlaps!
        }
        assert _is_covered_by_open(closed, open_segments) is True


class TestFetchOpenSegments:
    """Tests for the _fetch_open_segments() helper function."""

    def test_successful_fetch(self):
        """Verify open segments are parsed correctly."""
        mock_response = Mock()
        mock_response.text = json.dumps(
            {
                "features": [
                    {"geometry": {"coordinates": [[-113.9, 48.6], [-113.8, 48.65]]}},
                    {"geometry": {"coordinates": [[-113.5, 48.7], [-113.4, 48.75]]}},
                ]
            }
        )
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = _fetch_open_segments("Going-to-the-Sun")
            assert len(result) == 2
            assert (-113.9, -113.8) in result
            assert (-113.5, -113.4) in result

    def test_request_failure_returns_empty(self):
        """Verify empty set returned on request failure."""
        with patch("roads.roads.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Failed")
            result = _fetch_open_segments("Going-to-the-Sun")
            assert result == set()

    def test_empty_features_returns_empty(self):
        """Verify empty set when no open features exist."""
        mock_response = Mock()
        mock_response.text = json.dumps({"features": []})
        mock_response.raise_for_status = Mock()

        with patch("roads.roads.requests.get", return_value=mock_response):
            result = _fetch_open_segments("Going-to-the-Sun")
            assert result == set()


class TestOverlappingSegmentHandling:
    """Tests for the overlapping open/closed segment handling in closed_roads()."""

    def test_closed_segment_skipped_when_overlapping_open(self):
        """Verify closed segments are skipped when they overlap with open segments."""
        # Mock the closed roads response
        closed_response = Mock()
        closed_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Going-to-the-Sun Road",
                            "status": "closed",
                            "reason": "High winds",
                        },
                        "geometry": {
                            "coordinates": [
                                [-113.975, 48.53],  # Foot of Lake McDonald
                                [-113.885, 48.61],  # Lake McDonald Lodge
                            ]
                        },
                    }
                ]
            }
        )
        closed_response.raise_for_status = Mock()

        # Mock the open segments response (same section marked open)
        open_response = Mock()
        open_response.text = json.dumps(
            {
                "features": [
                    {
                        "geometry": {
                            "coordinates": [
                                [-113.977, 48.53],  # Overlapping section
                                [-113.885, 48.61],
                            ]
                        }
                    }
                ]
            }
        )
        open_response.raise_for_status = Mock()

        def mock_get(url, **kwargs):
            if "open" in url:
                return open_response
            return closed_response

        with patch("roads.roads.requests.get", side_effect=mock_get):
            result = closed_roads()
            # GTSR should not be in results since closed segment overlaps with open
            assert "Going-to-the-Sun Road" not in result

    def test_closed_segment_kept_when_no_overlap(self):
        """Verify closed segments are kept when they don't overlap with open."""
        # Mock the closed roads response - segment east of Logan Pass
        closed_response = Mock()
        closed_response.text = json.dumps(
            {
                "features": [
                    {
                        "properties": {
                            "rdname": "Going-to-the-Sun Road",
                            "status": "closed",
                            "reason": "Seasonal",
                        },
                        "geometry": {
                            "coordinates": [
                                [-113.72, 48.70],  # Logan Pass area
                                [-113.52, 48.69],  # Rising Sun area
                            ]
                        },
                    }
                ]
            }
        )
        closed_response.raise_for_status = Mock()

        # Mock the open segments response - different section (west end)
        open_response = Mock()
        open_response.text = json.dumps(
            {
                "features": [
                    {
                        "geometry": {
                            "coordinates": [
                                [-113.99, 48.52],  # Foot of Lake McDonald
                                [-113.88, 48.62],  # Lake McDonald Lodge
                            ]
                        }
                    }
                ]
            }
        )
        open_response.raise_for_status = Mock()

        def mock_get(url, **kwargs):
            if "open" in url:
                return open_response
            return closed_response

        with patch("roads.roads.requests.get", side_effect=mock_get):
            result = closed_roads()
            # GTSR should be in results since closed segment doesn't overlap with open
            assert "Going-to-the-Sun Road" in result

    def test_fetch_open_failure_doesnt_break_closure_detection(self):
        """Verify closed roads still works if fetching open segments fails."""
        # Mock the closed roads response
        closed_response = Mock()
        closed_response.text = json.dumps(
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
        closed_response.raise_for_status = Mock()

        call_count = [0]

        def mock_get(url, **kwargs):
            call_count[0] += 1
            if "open" in url:
                raise requests.RequestException("Failed to fetch open segments")
            return closed_response

        with patch("roads.roads.requests.get", side_effect=mock_get):
            result = closed_roads()
            # Should still report the closure even if open segments fetch failed
            assert "Going-to-the-Sun Road" in result
