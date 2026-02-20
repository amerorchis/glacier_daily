"""
Integration contract tests.

These tests verify that module interfaces match how they're actually used
in gen_data() and other integration points. This catches interface changes
that would break the system but not individual unit tests.
"""

from unittest.mock import Mock, patch

import pytest


class TestWeatherContentInterface:
    """Tests that WeatherContent has the attributes expected by gen_data()."""

    @pytest.fixture
    def mock_weather_dependencies(self):
        """Mock all external dependencies of WeatherContent."""
        with patch.multiple(
            "weather.weather",
            get_forecast=Mock(return_value=(None, "")),
            weather_alerts=Mock(return_value=""),
            get_season=Mock(return_value="summer"),
            get_sunset_hue=Mock(return_value=(0, "unknown", "")),
        ):
            yield

    def test_has_message1_attribute(self, mock_weather_dependencies):
        """Verify WeatherContent has message1 attribute as used in gen_data()."""
        from weather.weather import WeatherContent

        weather = WeatherContent()
        assert hasattr(weather, "message1"), (
            "WeatherContent must have 'message1' attribute"
        )
        assert isinstance(weather.message1, str), "message1 should be a string"

    def test_has_message2_attribute(self, mock_weather_dependencies):
        """Verify WeatherContent has message2 attribute as used in gen_data()."""
        from weather.weather import WeatherContent

        weather = WeatherContent()
        assert hasattr(weather, "message2"), (
            "WeatherContent must have 'message2' attribute"
        )
        assert isinstance(weather.message2, str), "message2 should be a string"

    def test_has_season_attribute(self, mock_weather_dependencies):
        """Verify WeatherContent has season attribute as used in gen_data()."""
        from weather.weather import WeatherContent

        weather = WeatherContent()
        assert hasattr(weather, "season"), "WeatherContent must have 'season' attribute"
        # season can be None or string
        assert weather.season is None or isinstance(weather.season, str), (
            "season should be None or string"
        )

    def test_has_results_attribute(self, mock_weather_dependencies):
        """Verify WeatherContent has results attribute as used by weather_image()."""
        from weather.weather import WeatherContent

        weather = WeatherContent()
        assert hasattr(weather, "results"), (
            "WeatherContent must have 'results' attribute"
        )
        # results can be None or list
        assert weather.results is None or isinstance(weather.results, list), (
            "results should be None or list"
        )


class TestModuleReturnTypes:
    """Tests that module return types match gen_data() expectations."""

    def test_get_closed_trails_returns_string(self):
        """Verify get_closed_trails returns a string."""
        with patch("trails_and_cgs.trails.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = '{"features": []}'
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            from trails_and_cgs.trails import get_closed_trails

            result = get_closed_trails()
            assert isinstance(result, str), "get_closed_trails should return str"

    def test_get_road_status_returns_string(self):
        """Verify get_road_status returns a string."""
        # Mock closed_roads to return empty dict (no closures)
        with patch("roads.roads.closed_roads", return_value={}):
            from roads.roads import get_road_status

            result = get_road_status()
            assert isinstance(result, str), "get_road_status should return str"

    def test_get_hiker_biker_status_returns_string(self):
        """Verify get_hiker_biker_status returns a string."""
        with patch("roads.hiker_biker.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_get.return_value = mock_response

            from roads.hiker_biker import get_hiker_biker_status

            result = get_hiker_biker_status()
            assert isinstance(result, str), "get_hiker_biker_status should return str"

    def test_events_today_returns_string(self, mock_required_settings):
        """Verify events_today returns a string."""
        # Mock requests.get to return empty data
        mock_response = Mock()
        mock_response.json.return_value = {"data": [], "total": 0}
        mock_response.raise_for_status = Mock()

        with patch("activities.events.requests.get", return_value=mock_response):
            from activities.events import events_today

            result = events_today()
            assert isinstance(result, str), "events_today should return str"


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
            assert isinstance(result, (tuple, list)), "peak should return tuple or list"
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
    """Tests that html_safe is called correctly with strings."""

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
