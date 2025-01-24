"""
Module for testing the data generation function.
"""

import pytest

from generate_and_upload import gen_data


@pytest.fixture(scope="module")
def generated_data():
    """Fixture to provide generated data for tests."""
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
        "trails",
        "campgrounds",
        "roads",
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
