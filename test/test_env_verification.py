"""
Test to verify that pytest uses TEMPLATE.env instead of email.env
"""

import os

import pytest


def test_env_loader_uses_template_env():
    """Verify that during testing, empty API keys from TEMPLATE.env are loaded."""
    from shared.env_loader import load_env

    env_file = load_env()

    # Should load TEMPLATE.env during testing
    assert env_file == "TEMPLATE.env"

    # All API keys should be empty strings (from TEMPLATE.env)
    assert os.getenv("DRIP_TOKEN") == ""
    assert os.getenv("flickr_key") == ""
    assert os.getenv("BC_TOKEN") == ""
    assert os.getenv("MAPBOX_TOKEN") == ""
    assert os.getenv("NPS") == ""


def test_pytest_current_test_is_set():
    """Verify that PYTEST_CURRENT_TEST is set during test execution."""
    # This environment variable is automatically set by pytest
    assert "PYTEST_CURRENT_TEST" in os.environ
    assert "test_env_verification.py" in os.environ["PYTEST_CURRENT_TEST"]
