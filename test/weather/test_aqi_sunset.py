import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from weather.sunset_hue import get_sunset_hue
from weather.weather_aqi import get_air_quality


# Test suite for sunset_hue.py
@pytest.fixture
def mock_sunset_response():
    return {"data": {"quality": 0.75, "quality_text": "excellent", "cloud_cover": 0.2}}


@pytest.fixture
def mock_sunset_response_poor():
    return {"data": {"quality": 0.3, "quality_text": "poor", "cloud_cover": 0.8}}


def test_get_sunset_hue_success(mock_sunset_response):
    """Test successful sunset hue prediction with good conditions"""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_sunset_response

        cloud_cover, quality_text, msg = get_sunset_hue()

        assert cloud_cover == 0.2
        assert quality_text == "excellent"
        assert "excellent" in msg.lower()
        assert isinstance(msg, str)


def test_get_sunset_hue_poor_conditions(mock_sunset_response_poor):
    """Test sunset hue prediction with poor conditions"""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_sunset_response_poor

        cloud_cover, quality_text, msg = get_sunset_hue()

        assert cloud_cover == 0.8
        assert quality_text == "poor"
        assert msg == ""  # Message should be empty for poor conditions


def test_get_sunset_hue_api_error():
    """Test handling of API errors"""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500

        cloud_cover, quality_text, msg = get_sunset_hue()

        assert cloud_cover == 0
        assert quality_text == "unknown"
        assert msg == ""


def test_get_sunset_hue_timeout():
    """Test handling of request timeouts"""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout()

        cloud_cover, quality_text, msg = get_sunset_hue()

        assert cloud_cover == 0
        assert quality_text == "unknown"
        assert msg == ""


# Test suite for weather_aqi.py
@pytest.fixture
def mock_aqi_response():
    return {
        "locations": [
            {
                "name": "West Glacier",
                "particulatesPA": {"nowCastPM": {"currentAQIVal": 42}},
            }
        ]
    }


def test_get_air_quality_success(mock_aqi_response):
    """Test successful AQI retrieval"""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_aqi_response

        aqi = get_air_quality()

        assert aqi == 42
        assert isinstance(aqi, int)


def test_get_air_quality_invalid_value():
    """Test handling of invalid AQI value"""
    mock_response = {
        "locations": [
            {
                "name": "West Glacier",
                "particulatesPA": {"nowCastPM": {"currentAQIVal": -99}},
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response

        aqi = get_air_quality()

        assert aqi == ""


def test_get_air_quality_no_data():
    """Test handling of missing West Glacier data"""
    mock_response = {
        "locations": [
            {
                "name": "Other Location",
                "particulatesPA": {"nowCastPM": {"currentAQIVal": 42}},
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response

        aqi = get_air_quality()

        assert aqi == ""


def test_get_air_quality_json_error():
    """Test handling of JSON decoding error"""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.side_effect = requests.exceptions.JSONDecodeError(
            "Invalid JSON", "", 0
        )

        aqi = get_air_quality()

        assert aqi == ""


def test_get_air_quality_request_error():
    """Test handling of request error"""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException()

        aqi = get_air_quality()

        assert aqi == ""


def test_get_air_quality_timeout():
    """Test handling of request timeout"""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout()

        aqi = get_air_quality()

        assert aqi == ""
