"""Integration smoke test for gen_data().

Calls gen_data() with real module code but all network access blocked.
Verifies wiring between modules and the data assembly dict — catches
import errors, signature mismatches, and dataclass field renames that
unit tests with full mocking cannot detect.
"""

import socket
import time

import pytest

from generate_and_upload import gen_data
from shared.lkg_cache import LKGCache

EXPECTED_KEYS = {
    "date",
    "today",
    "events",
    "weather",
    "weather_image",
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
    "sunrise_str",
    "gnpc-events",
}


@pytest.fixture(autouse=True)
def _isolate_lkg_cache():
    """Reset LKG cache so prior test data doesn't leak in."""
    LKGCache.reset()
    yield
    LKGCache.reset()


@pytest.fixture()
def _block_network(monkeypatch):
    """Block all outbound network connections and skip retry sleeps."""

    def _blocked_connect(*args, **kwargs):
        raise ConnectionRefusedError("Network blocked in integration test")

    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked_connect)

    # Patch sleep everywhere it's imported — modules using "from time import sleep"
    # bind the name at import time, so patching time.sleep alone doesn't reach them.
    def _noop(_):
        pass

    monkeypatch.setattr(time, "sleep", _noop)
    monkeypatch.setattr("shared.retry.sleep", _noop)
    monkeypatch.setattr("image_otd.flickr.time.sleep", _noop)
    monkeypatch.setattr("peak.fetch_wikipedia.time.sleep", _noop)
    monkeypatch.setattr("drip.canary_check.time.sleep", _noop)


@pytest.mark.usefixtures("_block_network")
def test_gen_data_smoke():
    """gen_data() produces a valid dict when all APIs are unreachable."""
    data, pending_uploads = gen_data()

    # All expected keys present
    missing = EXPECTED_KEYS - set(data.keys())
    assert not missing, f"Missing keys: {missing}"

    # Date fields are populated (no API needed)
    assert data["date"], "date should be populated"
    assert data["today"], "today should be populated"

    # No None values — all should be empty strings or default dataclass instances
    none_keys = [k for k, v in data.items() if v is None]
    assert not none_keys, f"Keys with None values: {none_keys}"

    # pending_uploads is a list
    assert isinstance(pending_uploads, list)
