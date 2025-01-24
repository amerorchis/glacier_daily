import io
import json
import os
from datetime import date, datetime
from pathlib import Path
from unittest.mock import ANY, Mock, patch

import numpy as np
import pytest
import requests
from PIL import Image

from peak.peak import peak
from peak.sat import peak_sat, upload_peak


@pytest.fixture
def mock_env_vars():
    """Mock Mapbox environment variables"""
    with patch.dict(
        "os.environ",
        {
            "MAPBOX_TOKEN": "test_token",
            "MAPBOX_ACCOUNT": "test_account",
            "MAPBOX_STYLE": "test_style",
        },
    ):
        yield


@pytest.fixture
def sample_peak_data():
    """Sample peak data for testing"""
    return {
        "name": "Test Peak",
        "elevation": "8000",
        "lat": "48.99815",
        "lon": "-114.21147",
    }


@pytest.fixture
def sample_image():
    """Create a sample image buffer"""
    img = Image.new("RGB", (100, 100), color="red")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="JPEG")
    img_buffer.seek(0)
    return img_buffer


def test_peak_selection(mock_env_vars):
    """Test random peak selection"""
    with patch("random.seed") as mock_seed:
        result = peak(test=True)

        # Check that random seed was set with today's date
        mock_seed.assert_called_once_with(date.today().strftime("%Y%m%d"))

        # Verify result format
        peak_name, peak_img, peak_map = result
        print(peak_name, peak_img, peak_map, sep="\n")
        assert isinstance(peak_name, str)
        assert "ft." in peak_name
        assert peak_map.startswith("https://www.google.com/maps/place/")
        assert peak_img is None  # Should be None in test mode


def test_peak_selection_with_cached_data():
    """Test peak selection when data is already cached"""
    mock_cache = {
        "peak": "Cached Peak - 8000 ft.",
        "peak_image": "cached_image.jpg",
        "peak_map": "cached_map_url",
    }

    with patch(
        "peak.peak.retrieve_from_json", return_value=(True, list(mock_cache.values()))
    ):
        result = peak(test=False)
        assert result == list(mock_cache.values())


def test_peak_sat_image_generation(mock_env_vars, sample_peak_data):
    """Test satellite image generation for a peak"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test_image_content"

    with patch("requests.get", return_value=mock_response), patch(
        "PIL.Image.open"
    ) as mock_open, patch(
        "peak.sat.upload_peak", return_value="https://example.com/peak.jpg"
    ):

        result = peak_sat(sample_peak_data)

        # Verify Mapbox API was called correctly
        requests.get.assert_called_once()
        assert "api.mapbox.com" in requests.get.call_args[0][0]
        assert "test_token" in requests.get.call_args[0][0]

        # Verify image was processed and uploaded
        mock_open.assert_called_once()
        assert result == "https://example.com/peak.jpg"


def test_peak_sat_api_error(mock_env_vars, sample_peak_data):
    """Test handling of Mapbox API errors"""
    with patch("requests.get", side_effect=requests.RequestException("API Error")):
        result = peak_sat(sample_peak_data)
        print(result)
        assert result == "https://glacier.org/daily/summer/peak.jpg"


def test_peak_sat_image_processing_error(mock_env_vars, sample_peak_data):
    """Test handling of image processing errors"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"invalid_image_data"

    with patch("requests.get", return_value=mock_response):
        result = peak_sat(sample_peak_data)
        assert result == "https://glacier.org/daily/summer/peak.jpg"


def test_upload_peak(mock_env_vars):
    """Test peak image upload functionality"""
    today = datetime.now()
    expected_filename = f"{today.month}_{today.day}_{today.year}_peak.jpg"

    with patch(
        "peak.sat.upload_file", return_value=("https://example.com/peak.jpg", [])
    ) as upload_file:
        result = upload_peak()

        # Verify upload_file was called with correct parameters
        upload_file.assert_called_once_with(
            "peak", expected_filename, "email_images/today/peak.jpg"
        )
        assert result == "https://example.com/peak.jpg"


def test_peak_with_invalid_coordinates(mock_env_vars):
    """Test handling of invalid peak coordinates"""
    invalid_peak = {
        "name": "Invalid Peak",
        "elevation": "8000",
        "lat": "invalid",
        "lon": "invalid",
    }

    result = peak_sat(invalid_peak)
    assert result == "https://glacier.org/daily/summer/peak.jpg"


def test_peak_csv_read():
    """Test reading of peaks from CSV"""
    with patch("random.seed"), patch(
        "peak.peak.retrieve_from_json", return_value=(False, None)
    ):
        result = peak(test=True)

        # Verify basic peak data format
        peak_name, _, peak_map = result
        assert " - " in peak_name  # Should contain name and elevation
        assert "ft." in peak_name
        assert "@" in peak_map  # Should contain coordinates
