"""
Shared pytest fixtures for the test suite.

This module provides common fixtures that can be reused across multiple test files,
reducing code duplication and ensuring consistent test setup.
"""

import dataclasses

import pytest

import shared.lkg_cache as _lkg_module
from shared.lkg_cache import LKGCache
from shared.logging_config import reset_log_capture
from shared.run_context import reset_run
from shared.settings import Settings, reset_settings
from shared.timing import reset_timing

# ============================================================================
# Settings Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    """Reset the settings singleton and seed every Settings field to ``""``
    so that ``load_dotenv(override=False)`` in ``get_settings()`` can never
    inject real values from ``email.env``.  This mirrors how the CI workflow
    sets all env vars to ``""``."""
    reset_settings()
    reset_run()
    reset_timing()
    reset_log_capture()
    LKGCache.reset()
    monkeypatch.setattr(_lkg_module, "DB_PATH", ":memory:")
    for f in dataclasses.fields(Settings):
        monkeypatch.setenv(f.name, "")
    yield
    reset_settings()
    reset_run()
    reset_timing()
    reset_log_capture()
    LKGCache.reset()


@pytest.fixture
def mock_required_settings(monkeypatch):
    """Set the six required env vars so get_settings() succeeds."""
    monkeypatch.setenv("NPS", "test_nps_key")
    monkeypatch.setenv("DRIP_TOKEN", "test_drip_token")
    monkeypatch.setenv("DRIP_ACCOUNT", "test_drip_account")
    monkeypatch.setenv("FTP_USERNAME", "test_ftp_user")
    monkeypatch.setenv("FTP_PASSWORD", "test_ftp_pass")
    monkeypatch.setenv("MAPBOX_TOKEN", "test_mapbox_token")
