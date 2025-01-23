"""
Unit tests for the weather image generator module.
"""

import sys
import os
from unittest.mock import patch, MagicMock
from PIL import Image
import pytest

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pragma: no cover

from weather.weather_img import weather_image, upload_weather, _validate_input


@pytest.fixture
def sample_weather_data():
    """Sample valid weather data for testing."""
    return [("West Glacier", 75, 45, "Sunny"), ("Logan Pass", 65, 35, "Partly Cloudy")]


@pytest.fixture
def mock_image():
    """Create a mock PIL Image."""
    return MagicMock(spec=Image.Image)


def test_validate_input_valid(sample_weather_data):
    """Test input validation with valid data."""
    _validate_input(sample_weather_data)  # Should not raise exception


def test_validate_input_invalid_location():
    """Test input validation with invalid location."""
    invalid_data = [("Invalid Location", 75, 45, "Sunny")]
    with pytest.raises(ValueError, match="Unknown location"):
        _validate_input(invalid_data)


def test_validate_input_invalid_temperature():
    """Test input validation with invalid temperature type."""
    invalid_data = [("West Glacier", "75", 45, "Sunny")]
    with pytest.raises(ValueError, match="Temperatures must be integers"):
        _validate_input(invalid_data)


def test_validate_input_empty_condition():
    """Test input validation with empty condition."""
    invalid_data = [("West Glacier", 75, 45, "")]
    with pytest.raises(ValueError, match="Weather condition cannot be empty"):
        _validate_input(invalid_data)


@patch("weather.weather_img.Image.open")
@patch("weather.weather_img.ImageDraw.Draw")
@patch("weather.weather_img.ImageFont.truetype")
@patch("weather.weather_img.upload_weather")
@patch("weather.weather_img.get_season")
def test_weather_image_success(
    mock_season, mock_upload, mock_font, mock_draw, mock_open, sample_weather_data
):
    """Test successful weather image creation and upload."""
    # Setup mocks
    mock_season.return_value = "summer"
    mock_image = MagicMock()
    mock_open.return_value = mock_image
    mock_image.resize.return_value = mock_image
    mock_draw_obj = MagicMock()
    mock_draw.return_value = mock_draw_obj
    mock_draw_obj.textlength.return_value = 50
    mock_upload.return_value = "http://example.com/image.png"
    mock_font.return_value = MagicMock()

    result = weather_image(sample_weather_data)

    assert result == "http://example.com/image.png"
    mock_image.resize.assert_called_once_with((405, 374))
    mock_image.save.assert_called_once()


@patch("weather.weather_img.Image.open")
def test_weather_image_missing_base_map(mock_open):
    """Test behavior when base map image is missing."""
    mock_open.side_effect = FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Base map not found"):
        weather_image([("West Glacier", 75, 45, "Sunny")])


@patch("weather.weather_img.upload_file")
def test_upload_weather(mock_upload):
    """Test weather image upload functionality."""
    mock_upload.return_value = ("http://example.com/image.png", None)
    result = upload_weather()
    assert result == "http://example.com/image.png"
    mock_upload.assert_called_once()


@patch("weather.weather_img.Image.open")
@patch("weather.weather_img.ImageDraw.Draw")
@patch("weather.weather_img.ImageFont.truetype")
@patch("weather.weather_img.upload_weather")
@patch("weather.weather_img.get_season")
def test_weather_image_long_condition(
    mock_season, mock_upload, mock_font, mock_draw, mock_open
):
    """Test handling of long weather conditions."""
    long_condition = "Very long weather condition that needs smaller font"
    test_data = [("West Glacier", 75, 45, long_condition)]

    # Setup mocks
    mock_season.return_value = "summer"
    mock_image = MagicMock()
    mock_open.return_value = mock_image
    mock_image.resize.return_value = mock_image

    # Mock the draw object and its textlength method
    mock_draw_obj = MagicMock()
    mock_draw.return_value = mock_draw_obj
    # Return values for each textlength call:
    # 1. Temperature text width
    # 2. Long condition text (too wide)
    # 3. Long condition text (after resize)
    # 4. Date text width
    mock_draw_obj.textlength.side_effect = [50, 200, 100, 50]

    mock_upload.return_value = "http://example.com/image.png"
    mock_font.return_value = MagicMock()

    result = weather_image(test_data)

    assert result == "http://example.com/image.png"
    # Verify font was recreated with smaller size
    assert mock_font.call_count > 1
    assert mock_image.save.called


def test_empty_results():
    """Test behavior with empty results list."""
    with pytest.raises(ValueError, match="Results list cannot be empty"):
        weather_image([])
