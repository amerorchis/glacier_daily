"""
Integration contract tests.

These tests verify that module interfaces match how they're actually used
in gen_data() and other integration points. This catches interface changes
that would break the system but not individual unit tests.
"""

from unittest.mock import Mock, patch

import pytest

from shared.data_types import (
    EventsResult,
    HikerBikerResult,
    RoadsResult,
    TrailsResult,
    WeatherResult,
)


class TestWeatherResultInterface:
    """Tests that weather_data returns a WeatherResult with expected attributes."""

    @pytest.fixture
    def mock_weather_dependencies(self):
        """Mock all external dependencies of weather_data."""
        with patch.multiple(
            "weather.weather",
            get_forecast=Mock(return_value=(None, "")),
            get_air_quality=Mock(return_value=-1),
            weather_alerts=Mock(return_value=[]),
            get_season=Mock(return_value="summer"),
            get_sunset_hue=Mock(return_value=(0, "unknown", "")),
            aurora_forecast=Mock(return_value=("", "")),
        ):
            yield

    def test_returns_weather_result(self, mock_weather_dependencies):
        """Verify weather_data returns a WeatherResult."""
        from weather.weather import weather_data

        result = weather_data()
        assert isinstance(result, WeatherResult), (
            "weather_data must return WeatherResult"
        )

    def test_has_daylight_message(self, mock_weather_dependencies):
        """Verify WeatherResult has daylight_message attribute."""
        from weather.weather import weather_data

        result = weather_data()
        assert hasattr(result, "daylight_message")
        assert isinstance(result.daylight_message, str)

    def test_has_forecasts(self, mock_weather_dependencies):
        """Verify WeatherResult has forecasts attribute."""
        from weather.weather import weather_data

        result = weather_data()
        assert hasattr(result, "forecasts")
        assert isinstance(result.forecasts, list)

    def test_has_season(self, mock_weather_dependencies):
        """Verify WeatherResult has season attribute."""
        from weather.weather import weather_data

        result = weather_data()
        assert hasattr(result, "season")
        assert result.season is None or isinstance(result.season, str)

    def test_has_alerts(self, mock_weather_dependencies):
        """Verify WeatherResult has alerts attribute."""
        from weather.weather import weather_data

        result = weather_data()
        assert hasattr(result, "alerts")
        assert isinstance(result.alerts, list)


class TestModuleReturnTypes:
    """Tests that module return types match gen_data() expectations."""

    def test_get_closed_trails_returns_trails_result(self):
        """Verify get_closed_trails returns a TrailsResult."""
        with patch("trails_and_cgs.trails.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = '{"features": []}'
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            from trails_and_cgs.trails import get_closed_trails

            result = get_closed_trails()
            assert isinstance(result, TrailsResult), (
                "get_closed_trails should return TrailsResult"
            )

    def test_get_road_status_returns_roads_result(self):
        """Verify get_road_status returns a RoadsResult."""
        # Mock closed_roads to return empty dict (no closures)
        with patch("roads.roads.closed_roads", return_value={}):
            from roads.roads import get_road_status

            result = get_road_status()
            assert isinstance(result, RoadsResult), (
                "get_road_status should return RoadsResult"
            )

    def test_get_hiker_biker_status_returns_hiker_biker_result(self):
        """Verify get_hiker_biker_status returns a HikerBikerResult."""
        with patch("roads.hiker_biker.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_get.return_value = mock_response

            from roads.hiker_biker import get_hiker_biker_status

            result = get_hiker_biker_status()
            assert isinstance(result, HikerBikerResult), (
                "get_hiker_biker_status should return HikerBikerResult"
            )

    def test_events_today_returns_events_result(self, mock_required_settings):
        """Verify events_today returns an EventsResult."""
        # Mock requests.get to return empty data
        mock_response = Mock()
        mock_response.json.return_value = {"data": [], "total": 0}
        mock_response.raise_for_status = Mock()

        with patch("activities.events.requests.get", return_value=mock_response):
            from activities.events import events_today

            result = events_today()
            assert isinstance(result, EventsResult), (
                "events_today should return EventsResult"
            )


class TestTupleUnpacking:
    """Tests that tuple-returning functions return correct length tuples."""

    def test_get_image_otd_returns_3_tuple(self):
        """Verify get_image_otd returns a 3-tuple."""
        with patch.multiple(
            "image_otd.image_otd",
            retrieve_from_json=Mock(return_value=(True, ("url", "title", "link"))),
        ):
            from image_otd.image_otd import get_image_otd

            result = get_image_otd()
            assert isinstance(result, tuple), "get_image_otd should return tuple"
            assert len(result) == 3, (
                "get_image_otd should return 3-tuple (url, title, link)"
            )

    def test_peak_returns_3_tuple(self):
        """Verify peak returns a 3-tuple."""
        with patch.multiple(
            "peak.peak",
            retrieve_from_json=Mock(return_value=(True, ["name", "image", "map"])),
        ):
            from peak.peak import peak

            result = peak()
            assert isinstance(result, tuple | list), "peak should return tuple or list"
            assert len(result) == 3, "peak should return 3 elements (name, image, map)"

    def test_get_product_returns_4_tuple(self):
        """Verify get_product returns a 4-tuple."""
        with patch.multiple(
            "product_otd.product",
            retrieve_from_json=Mock(
                return_value=(True, ("title", "img", "link", "desc"))
            ),
        ):
            from product_otd.product import get_product

            result = get_product()
            assert isinstance(result, tuple), "get_product should return tuple"
            assert len(result) == 4, (
                "get_product should return 4-tuple (title, img, link, desc)"
            )

    def test_process_video_returns_3_tuple(self):
        """Verify process_video returns a 3-tuple."""
        with patch.multiple(
            "sunrise_timelapse.get_timelapse",
            retrieve_from_json=Mock(return_value=(True, ("vid", "still", "desc"))),
        ):
            from sunrise_timelapse.get_timelapse import process_video

            result = process_video()
            assert isinstance(result, tuple), "process_video should return tuple"
            assert len(result) == 3, (
                "process_video should return 3-tuple (vid, still, desc)"
            )


class TestHtmlSafeIntegration:
    """Tests that html_safe still works (utility function)."""

    def test_html_safe_accepts_string(self):
        """Verify html_safe accepts string input."""
        from drip.html_friendly import html_safe

        result = html_safe("test string with <special> chars & stuff")
        assert isinstance(result, str), "html_safe should return str"

    def test_html_safe_handles_empty_string(self):
        """Verify html_safe handles empty strings."""
        from drip.html_friendly import html_safe

        result = html_safe("")
        assert result == "", "html_safe of empty string should be empty string"


class TestWeatherImageIntegration:
    """Tests that weather_image validates input and returns string."""

    def test_weather_image_rejects_none(self):
        """Verify weather_image raises error for None input."""
        from weather.weather_img import weather_image

        with pytest.raises((ValueError, TypeError, AttributeError)):
            weather_image(None)

    def test_weather_image_rejects_empty_list(self):
        """Verify weather_image raises ValueError for empty list."""
        from weather.weather_img import weather_image

        with pytest.raises(ValueError, match="cannot be empty"):
            weather_image([])

    def test_weather_image_validates_location_format(self):
        """Verify weather_image validates location names."""
        from weather.weather_img import weather_image

        with pytest.raises(ValueError, match="Unknown location"):
            weather_image([("Invalid Location", 70, 45, "Sunny")])

    def test_weather_image_returns_string_with_valid_input(self):
        """Verify weather_image returns string with properly mocked internals."""
        # Create mock image and draw objects with all needed methods
        mock_image = Mock()
        mock_draw = Mock()
        mock_draw.textlength = Mock(return_value=50.0)  # Mock text width

        with (
            patch("weather.weather_img._validate_input"),
            patch("weather.weather_img._get_base_image", return_value=mock_image),
            patch("weather.weather_img.ImageDraw.Draw", return_value=mock_draw),
            patch("weather.weather_img._get_font", return_value=Mock()),
            patch(
                "weather.weather_img.upload_weather",
                return_value="https://example.com/img.png",
            ),
        ):
            from weather.weather_img import weather_image

            result = weather_image([("West Glacier", 70, 45, "Sunny")])
            assert isinstance(result, str)
