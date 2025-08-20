"""
Module for testing the data generation function.
"""

from unittest.mock import patch

import pytest

from generate_and_upload import gen_data


@pytest.fixture(scope="module")
def generated_data():
    """Fixture to provide generated data for tests."""
    from unittest.mock import Mock

    # Create a mock WeatherContent object
    mock_weather = Mock()
    mock_weather.message1 = "weather1"
    mock_weather.message2 = "weather2"
    mock_weather.season = "season"
    mock_weather.results = []

    # Mock all the external dependencies to avoid real API calls and file access
    with (
        patch("generate_and_upload.events_today", return_value="mocked events"),
        patch("generate_and_upload.get_gnpc_events", return_value=[]),
        patch(
            "generate_and_upload.get_image_otd",
            return_value=("img_url", "title", "link"),
        ),
        patch("generate_and_upload.get_notices", return_value="mocked notices"),
        patch(
            "generate_and_upload.peak",
            return_value=("Peak Name - 8000 ft.", "peak_img", "peak_map"),
        ),
        patch(
            "generate_and_upload.get_product",
            return_value=("Product", "img", "link", "desc"),
        ),
        patch("generate_and_upload.get_hiker_biker_status", return_value=""),
        patch("generate_and_upload.get_road_status", return_value=""),
        patch(
            "generate_and_upload.process_video", return_value=("vid", "still", "str")
        ),
        patch("generate_and_upload.get_campground_status", return_value="campgrounds"),
        patch("generate_and_upload.get_closed_trails", return_value=""),
        patch("generate_and_upload.weather_data", return_value=mock_weather),
        patch("generate_and_upload.weather_image", return_value="weather_img_url"),
        # Mock retrieve_from_json to avoid file access issues
        patch(
            "shared.retrieve_from_json.retrieve_from_json", return_value=(False, None)
        ),
        # Mock file operations that might fail
        patch("shared.ftp.upload_file", return_value=("mocked_url", [])),
    ):
        return gen_data()


@pytest.fixture
def expected_keys():
    """Fixture to provide the set of expected keys."""
    return {
        "date",
        "today",
        "events",
        "weather1",
        "weather_image",
        "weather2",
        "season",
        "trails",
        "campgrounds",
        "roads",
        "hikerbiker",
        "notices",
        "peak",
        "peak_image",
        "peak_map",
        "product_link",
        "product_image",
        "product_title",
        "product_desc",
        "image_otd",
        "image_otd_title",
        "image_otd_link",
        "sunrise_vid",
        "sunrise_still",
    }


@pytest.fixture
def required_truthy_keys():
    """Fixture to provide keys that must have truthy values."""
    return {
        "date",
        "today",
        "weather1",
        "weather_image",
        "weather2",
        "season",
        # "trails",
        "campgrounds",
        # "roads",
        "peak",
        "peak_image",
        "peak_map",
        "product_link",
        "product_image",
        "product_title",
        "product_desc",
        "image_otd",
    }


def test_gen_data_keys(generated_data, expected_keys):
    """Test that the generated data contains all the expected keys."""
    missing_keys = expected_keys - set(generated_data.keys())
    assert not missing_keys, f"Missing required keys: {missing_keys}"


def test_truthy_values(generated_data, required_truthy_keys):
    """Test that specific keys have truthy values."""
    non_truthy_keys = {
        key for key in required_truthy_keys if not generated_data.get(key)
    }
    assert (
        not non_truthy_keys
    ), f"Following keys have non-truthy values: {non_truthy_keys}"
