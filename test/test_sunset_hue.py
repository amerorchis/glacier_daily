"""
Unit tests for weather.sunset_hue module.

Tests the sunset hue forecast fetching and formatting functions.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from weather.sunset_hue import get_sunset_hue


class TestGetSunsetHue:
    """Tests for the get_sunset_hue() function."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variable for API key."""
        monkeypatch.setenv("SUNSETHUE_KEY", "test_api_key")

    def test_timeout_returns_error_tuple(self, mock_env):
        """Verify error tuple returned on timeout."""
        with patch("weather.sunset_hue.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()
            result = get_sunset_hue()
            assert result == (0, "unknown", "")

    def test_non_200_status_returns_error_tuple(self, mock_env):
        """Verify error tuple returned on non-200 status."""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            result = get_sunset_hue()
            assert result == (0, "unknown", "")

    def test_404_status_returns_error_tuple(self, mock_env):
        """Verify error tuple returned on 404 status."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            result = get_sunset_hue()
            assert result == (0, "unknown", "")

    def test_low_quality_returns_empty_message(self, mock_env):
        """Verify empty message when quality below 0.41 threshold."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.3, "quality_text": "poor", "cloud_cover": 0.2}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            cloud_cover, quality_text, msg = get_sunset_hue()
            assert cloud_cover == 0.2
            assert quality_text == "poor"
            assert msg == ""

    def test_high_cloud_cover_returns_empty_message(self, mock_env):
        """Verify empty message when cloud cover above 0.6 threshold."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": "great", "cloud_cover": 0.7}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            cloud_cover, quality_text, msg = get_sunset_hue()
            assert cloud_cover == 0.7
            assert quality_text == "great"
            assert msg == ""

    def test_quality_at_threshold_returns_empty_message(self, mock_env):
        """Verify empty message when quality exactly at 0.41 threshold."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.41, "quality_text": "fair", "cloud_cover": 0.5}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            _, _, msg = get_sunset_hue()
            # 0.41 is NOT less than 0.41, so message should be returned
            assert msg != ""

    def test_cloud_cover_at_threshold_returns_empty_message(self, mock_env):
        """Verify empty message when cloud cover exactly at 0.6 threshold."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": "great", "cloud_cover": 0.6}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            _, _, msg = get_sunset_hue()
            # 0.6 is NOT greater than 0.6, so message should be returned
            assert msg != ""

    def test_good_conditions_returns_message(self, mock_env):
        """Verify message returned when conditions are favorable."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": "great", "cloud_cover": 0.3}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            cloud_cover, quality_text, msg = get_sunset_hue()
            assert cloud_cover == 0.3
            assert quality_text == "great"
            assert "great" in msg
            assert "!" in msg  # Non-good quality gets exclamation

    def test_good_quality_text_ends_with_period(self, mock_env):
        """Verify message ends with period when quality_text is 'good'."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.5, "quality_text": "good", "cloud_cover": 0.3}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            _, _, msg = get_sunset_hue()
            assert "good" in msg
            assert msg.endswith(".")

    def test_empty_quality_text_returns_error_tuple(self, mock_env):
        """Verify error tuple returned when quality_text is empty."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": "", "cloud_cover": 0.3}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            result = get_sunset_hue()
            assert result == (0, "unknown", "")

    def test_none_quality_text_raises_attribute_error(self, mock_env):
        """Verify AttributeError when quality_text is explicitly None.

        Note: This documents current behavior. The code calls .lower() on None
        when quality_text is explicitly None (vs missing). This is an edge case
        that may warrant a fix in the source code.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": None, "cloud_cover": 0.3}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            with pytest.raises(AttributeError):
                get_sunset_hue()

    def test_missing_data_fields_handled(self, mock_env):
        """Verify default values used when data fields are missing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}  # Empty data object

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            result = get_sunset_hue()
            # Should use defaults: quality=0, quality_text="unknown", cloud_cover=0
            # quality_text="unknown" triggers empty string check or threshold check
            assert result == (0, "unknown", "")

    def test_api_key_included_in_request(self, mock_env):
        """Verify API key is included in request headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": "great", "cloud_cover": 0.3}
        }

        with patch(
            "weather.sunset_hue.requests.get", return_value=mock_response
        ) as mock_get:
            get_sunset_hue()
            call_kwargs = mock_get.call_args[1]
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["x-api-key"] == "test_api_key"

    def test_correct_url_constructed(self, mock_env):
        """Verify correct API URL is constructed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": "great", "cloud_cover": 0.3}
        }

        with patch(
            "weather.sunset_hue.requests.get", return_value=mock_response
        ) as mock_get:
            get_sunset_hue()
            call_url = mock_get.call_args[0][0]
            assert "api.sunsethue.com" in call_url
            assert "latitude=48.528556" in call_url
            assert "longitude=-113.991674" in call_url
            assert "type=sunset" in call_url

    def test_test_mode_prints_values(self, mock_env, capsys):
        """Verify test mode prints debug values."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"quality": 0.8, "quality_text": "great", "cloud_cover": 0.3}
        }

        with patch("weather.sunset_hue.requests.get", return_value=mock_response):
            get_sunset_hue(test=True)
            captured = capsys.readouterr()
            assert "0.8" in captured.out
            assert "great" in captured.out
            assert "0.3" in captured.out
