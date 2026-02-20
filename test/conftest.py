"""
Shared pytest fixtures for the test suite.

This module provides common fixtures that can be reused across multiple test files,
reducing code duplication and ensuring consistent test setup.
"""

from unittest.mock import Mock, patch

import pytest

from shared.settings import reset_settings

# ============================================================================
# Settings Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _reset_settings():
    """Reset the settings singleton before each test so monkeypatched
    env vars are picked up by get_settings()."""
    reset_settings()
    yield
    reset_settings()


# ============================================================================
# Environment Variable Fixtures
# ============================================================================


@pytest.fixture
def mock_required_settings(monkeypatch):
    """Set the six required env vars so get_settings() succeeds."""
    monkeypatch.setenv("NPS", "test_nps_key")
    monkeypatch.setenv("DRIP_TOKEN", "test_drip_token")
    monkeypatch.setenv("DRIP_ACCOUNT", "test_drip_account")
    monkeypatch.setenv("FTP_USERNAME", "test_ftp_user")
    monkeypatch.setenv("FTP_PASSWORD", "test_ftp_pass")
    monkeypatch.setenv("MAPBOX_TOKEN", "test_mapbox_token")


@pytest.fixture
def mock_mapbox_env(monkeypatch):
    """Mock Mapbox environment variables used by peak module."""
    monkeypatch.setenv("MAPBOX_TOKEN", "test_mapbox_token")
    monkeypatch.setenv("MAPBOX_ACCOUNT", "test_account")
    monkeypatch.setenv("MAPBOX_STYLE", "test_style")


@pytest.fixture
def mock_bigcommerce_env(monkeypatch):
    """Mock BigCommerce environment variables used by product module."""
    monkeypatch.setenv("BC_TOKEN", "test_bc_token")
    monkeypatch.setenv("BC_STORE_HASH", "test_store")


@pytest.fixture
def mock_flickr_env(monkeypatch):
    """Mock Flickr environment variables used by image_otd module."""
    monkeypatch.setenv("flickr_key", "test_flickr_key")
    monkeypatch.setenv("flickr_secret", "test_flickr_secret")


@pytest.fixture
def mock_google_sheets_env(monkeypatch):
    """Mock Google Sheets environment variables used by notices module."""
    monkeypatch.setenv("GOOGLE_CREDENTIALS", '{"type": "service_account"}')


@pytest.fixture
def mock_drip_env(monkeypatch):
    """Mock Drip environment variables used by drip module."""
    monkeypatch.setenv("DRIP_TOKEN", "test_drip_token")
    monkeypatch.setenv("DRIP_ACCOUNT", "test_account_id")


@pytest.fixture
def mock_cloudflare_env(monkeypatch):
    """Mock Cloudflare environment variables for cache purging."""
    monkeypatch.setenv("CACHE_PURGE", "test_cache_key")
    monkeypatch.setenv("ZONE_ID", "test_zone_id")


@pytest.fixture
def mock_all_env(
    mock_mapbox_env,
    mock_bigcommerce_env,
    mock_flickr_env,
    mock_google_sheets_env,
    mock_drip_env,
    mock_cloudflare_env,
):
    """Convenience fixture that mocks all common environment variables."""
    pass  # All fixtures are applied through dependency injection


# ============================================================================
# HTTP Response Fixtures
# ============================================================================


@pytest.fixture
def mock_successful_response():
    """Create a mock successful HTTP response (200 OK)."""
    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_error_response():
    """Create a mock error HTTP response (500 Internal Server Error)."""
    response = Mock()
    response.status_code = 500
    response.text = "Internal Server Error"
    response.raise_for_status = Mock(side_effect=Exception("HTTP Error"))
    return response


@pytest.fixture
def mock_json_response():
    """Create a mock response with JSON capability."""
    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json = Mock(return_value={})
    return response


# ============================================================================
# Data Fixtures
# ============================================================================


@pytest.fixture
def sample_weather_results():
    """Sample weather results in the format expected by weather modules."""
    return [
        ("West Glacier", 75, 50, "Sunny"),
        ("St. Mary", 72, 48, "Partly Cloudy"),
        ("Logan Pass", 65, 42, "Cloudy"),
        ("Many Glacier", 70, 45, "Sunny"),
        ("Polebridge", 68, 44, "Clear"),
        ("Two Medicine", 71, 47, "Partly Cloudy"),
    ]


@pytest.fixture
def sample_road_closure():
    """Sample road closure data in the format from NPS API."""
    return {
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
                        [-113.5, 48.7],
                        [-113.44056, 48.74784],
                    ]
                },
            }
        ]
    }


@pytest.fixture
def empty_features_response():
    """Sample API response with no features."""
    return {"features": []}


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def temp_image(tmp_path):
    """Create a temporary test image file."""
    from PIL import Image

    img_path = tmp_path / "test_image.jpg"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(img_path, format="JPEG")
    return img_path


@pytest.fixture
def mock_upload_file():
    """Mock the FTP upload_file function."""
    with patch("shared.ftp.upload_file") as mock:
        mock.return_value = ("https://glacier.org/test/image.jpg", [])
        yield mock
