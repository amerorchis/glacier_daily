from unittest.mock import MagicMock, patch

import pytest

import generate_and_upload as gau
from shared.data_types import (
    CampgroundsResult,
    EventsResult,
    HikerBikerResult,
    NoticesResult,
    RoadsResult,
    TrailsResult,
    WeatherResult,
)
from shared.lkg_cache import LKGCache


def make_fake_weather():
    return WeatherResult(
        daylight_message="Daylight info",
        forecasts=[("West Glacier", 75, 30, "Partly cloudy")],
        season="summer",
        aqi_value=45,
        aqi_category="good.",
        aurora_quality="Good",
        aurora_message="Aurora visible",
        sunset_quality="Good",
        sunset_message="Beautiful sunset",
        cloud_cover_pct=30,
        alerts=[],
    )


class MockFTPSession:
    """Mock FTPSession for testing."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def upload(self, directory, filename, file=None):
        return (f"https://glacier.org/daily/{directory}/{filename}", [])


@pytest.fixture
def mock_all_data_sources(monkeypatch):
    """Fixture to mock all data sources used by gen_data()."""
    monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
    monkeypatch.setattr(
        gau, "get_closed_trails", lambda: TrailsResult(closures=["Trail closure"])
    )
    monkeypatch.setattr(
        gau, "get_campground_status", lambda: CampgroundsResult(statuses=["CG status"])
    )
    monkeypatch.setattr(
        gau, "get_road_status", lambda: RoadsResult(closures=["Road closure"])
    )
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: HikerBikerResult())
    monkeypatch.setattr(gau, "events_today", lambda: EventsResult())
    monkeypatch.setattr(
        gau, "get_image_otd", lambda **kw: ("img", "img_title", "img_link")
    )
    monkeypatch.setattr(gau, "peak", lambda **kw: ("peak", "peak_img", "peak_map"))
    monkeypatch.setattr(gau, "process_video", lambda: ("vid", "still", "descriptor"))
    monkeypatch.setattr(
        gau,
        "get_product",
        lambda **kw: ("prod_title", "prod_img", "prod_link", "prod_desc"),
    )
    monkeypatch.setattr(
        gau, "get_notices", lambda: NoticesResult(notices=["Test notice"])
    )
    monkeypatch.setattr(gau, "weather_image", lambda x, **kw: "weather_img")
    monkeypatch.setattr(gau, "get_gnpc_events", list)


def test_gen_data_keys_present(mock_all_data_sources):
    """Verify all expected keys are present in gen_data output."""
    data, _ = gau.gen_data()

    expected_keys = [
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
    ]

    for key in expected_keys:
        assert key in data, f"Expected key '{key}' not found in gen_data output"


def test_gen_data_structured_types(mock_all_data_sources):
    """Verify structured data fields return correct types."""
    data, _ = gau.gen_data()

    assert isinstance(data["weather"], WeatherResult)
    assert isinstance(data["events"], EventsResult)
    assert isinstance(data["trails"], TrailsResult)
    assert isinstance(data["campgrounds"], CampgroundsResult)
    assert isinstance(data["roads"], RoadsResult)
    assert isinstance(data["hikerbiker"], HikerBikerResult)
    assert isinstance(data["notices"], NoticesResult)


def test_gen_data_string_fields_are_strings(mock_all_data_sources):
    """Verify plain string fields return str type (empty string is valid)."""
    data, _ = gau.gen_data()

    string_fields = [
        "date",
        "today",
        "peak",
        "product_link",
        "product_title",
        "product_desc",
        "image_otd",
        "image_otd_title",
        "image_otd_link",
        "sunrise_vid",
        "sunrise_still",
        "sunrise_str",
        "weather_image",
        "peak_map",
    ]

    for key in string_fields:
        value = data.get(key)
        assert isinstance(value, str), (
            f"Field '{key}' should be str, got {type(value).__name__}"
        )


def test_gen_data_nullable_image_fields(mock_all_data_sources):
    """Verify image fields can be str or None."""
    data, _ = gau.gen_data()

    nullable_fields = [
        "peak_image",
        "product_image",
    ]

    for key in nullable_fields:
        value = data.get(key)
        assert value is None or isinstance(value, str), (
            f"Field '{key}' should be str or None, got {type(value).__name__}"
        )


def test_gen_data_returns_dict(mock_all_data_sources):
    """Verify gen_data returns a (dict, list) tuple."""
    data, pending = gau.gen_data()
    assert isinstance(data, dict), (
        f"gen_data should return dict, got {type(data).__name__}"
    )
    assert isinstance(pending, list)


def test_gen_data_with_empty_returns(monkeypatch):
    """Verify gen_data handles modules that return empty values gracefully."""
    monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
    monkeypatch.setattr(gau, "get_closed_trails", lambda: TrailsResult())
    monkeypatch.setattr(gau, "get_campground_status", lambda: CampgroundsResult())
    monkeypatch.setattr(gau, "get_road_status", lambda: RoadsResult())
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: HikerBikerResult())
    monkeypatch.setattr(gau, "events_today", lambda: EventsResult())
    monkeypatch.setattr(gau, "get_image_otd", lambda **kw: ("", "", ""))
    monkeypatch.setattr(gau, "peak", lambda **kw: ("", None, ""))
    monkeypatch.setattr(gau, "process_video", lambda: ("", "", ""))
    monkeypatch.setattr(gau, "get_product", lambda **kw: ("", None, "", ""))
    monkeypatch.setattr(gau, "get_notices", lambda: NoticesResult())
    monkeypatch.setattr(gau, "weather_image", lambda x, **kw: "")
    monkeypatch.setattr(gau, "get_gnpc_events", list)

    # Should not raise even with empty values
    data, _ = gau.gen_data()
    assert isinstance(data, dict)
    assert "date" in data  # Should still have date


def test_write_data_to_json(tmp_path, monkeypatch):
    fake_data = {"foo": "bar", "baz": "qux", "gnpc-events": []}
    out = gau.write_data_to_json(fake_data, "test.json")
    assert out.endswith("test.json")
    # Check file contents
    with open(out, encoding="utf-8") as f:
        content = f.read()
        assert "foo" in content and "baz" in content and "gnpc-events" in content


def test_write_data_to_json_with_dataclasses(tmp_path, monkeypatch):
    """Verify dataclass values are serialized correctly."""
    import json

    fake_data = {
        "trails": TrailsResult(closures=["Trail A closed"]),
        "roads": RoadsResult(no_closures_message="No closures"),
        "gnpc-events": [],
    }
    out = gau.write_data_to_json(fake_data, "test.json")
    with open(out, encoding="utf-8") as f:
        parsed = json.load(f)
    assert parsed["trails"]["closures"] == ["Trail A closed"]
    assert parsed["roads"]["no_closures_message"] == "No closures"


def test_serve_api(monkeypatch, tmp_path):
    # Patch everything to avoid side effects
    monkeypatch.setattr(gau, "gen_data", lambda: ({"foo": "bar"}, []))
    monkeypatch.setattr(gau, "web_version", lambda data, *a, **k: "server/webfile")
    monkeypatch.setattr(
        gau, "write_data_to_json", lambda data, doctype: str(tmp_path / "email.json")
    )
    monkeypatch.setattr(gau, "FTPSession", MockFTPSession)
    monkeypatch.setattr(gau, "purge_cache", lambda: True)
    monkeypatch.setattr(gau, "refresh_cache", lambda: None)
    monkeypatch.setattr(gau, "sleep", lambda _: None)
    # Should not raise
    gau.serve_api()


def test_serve_api_gen_data_raises(monkeypatch):
    """Verify serve_api propagates exceptions from gen_data."""

    def failing_gen_data():
        raise RuntimeError("data fetch failed")

    monkeypatch.setattr(gau, "gen_data", failing_gen_data)
    monkeypatch.setattr(gau, "FTPSession", MockFTPSession)
    with pytest.raises(RuntimeError, match="data fetch failed"):
        gau.serve_api()


def test_gen_data_module_exception_handling(monkeypatch):
    """Verify gen_data degrades gracefully when a module fails."""

    def failing_peak(**kw):
        raise ConnectionError("API unreachable")

    monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
    monkeypatch.setattr(
        gau, "get_closed_trails", lambda: TrailsResult(closures=["Trail closure"])
    )
    monkeypatch.setattr(
        gau, "get_campground_status", lambda: CampgroundsResult(statuses=["CG status"])
    )
    monkeypatch.setattr(
        gau, "get_road_status", lambda: RoadsResult(closures=["Road closure"])
    )
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: HikerBikerResult())
    monkeypatch.setattr(gau, "events_today", lambda: EventsResult())
    monkeypatch.setattr(gau, "get_image_otd", lambda **kw: ("img", "title", "link"))
    monkeypatch.setattr(gau, "peak", failing_peak)
    monkeypatch.setattr(gau, "process_video", lambda: ("vid", "still", "desc"))
    monkeypatch.setattr(gau, "get_product", lambda **kw: ("t", "i", "l", "d"))
    monkeypatch.setattr(
        gau, "get_notices", lambda: NoticesResult(fallback_message="No notices")
    )
    monkeypatch.setattr(gau, "weather_image", lambda x, **kw: "weather_img")
    monkeypatch.setattr(gau, "get_gnpc_events", list)

    # gen_data should not raise — it should use fallback values
    result, _ = gau.gen_data()
    assert isinstance(result, dict)
    assert result["peak"] == ""
    assert result["peak_map"] == ""
    # Other modules should still have their real data
    assert isinstance(result["trails"], TrailsResult)
    assert isinstance(result["roads"], RoadsResult)


def test_gen_data_multiple_module_failures(monkeypatch):
    """Verify gen_data still produces output when multiple modules fail."""

    def failing(**kw):
        raise ConnectionError("down")

    monkeypatch.setattr(gau, "weather_data", failing)
    monkeypatch.setattr(gau, "get_closed_trails", failing)
    monkeypatch.setattr(gau, "get_campground_status", failing)
    monkeypatch.setattr(
        gau, "get_road_status", lambda: RoadsResult(closures=["Road closure"])
    )
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: HikerBikerResult())
    monkeypatch.setattr(gau, "events_today", lambda: EventsResult())
    monkeypatch.setattr(gau, "get_image_otd", lambda **kw: ("img", "title", "link"))
    monkeypatch.setattr(gau, "peak", lambda **kw: ("peak_name", "peak_img", "map"))
    monkeypatch.setattr(gau, "process_video", lambda: ("vid", "still", "desc"))
    monkeypatch.setattr(gau, "get_product", lambda **kw: ("t", "i", "l", "d"))
    monkeypatch.setattr(
        gau, "get_notices", lambda: NoticesResult(fallback_message="No notices")
    )
    monkeypatch.setattr(gau, "weather_image", lambda x, **kw: "weather_img")
    monkeypatch.setattr(gau, "get_gnpc_events", list)

    result, _ = gau.gen_data()
    assert isinstance(result, dict)
    # Weather fallback: empty WeatherResult
    assert isinstance(result["weather"], WeatherResult)
    # Trails fallback: empty TrailsResult
    assert isinstance(result["trails"], TrailsResult)
    # Working modules still populated
    assert isinstance(result["roads"], RoadsResult)
    assert isinstance(result["events"], EventsResult)


def test_purge_cache_success(monkeypatch, mock_required_settings):
    # Mock environment variables
    monkeypatch.setenv("CACHE_PURGE", "test_key")
    monkeypatch.setenv("ZONE_ID", "test_zone")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch(
        "generate_and_upload.requests.post", return_value=mock_response
    ) as mock_post:
        assert gau.purge_cache() is True

        # Verify the API was called correctly
        mock_post.assert_called_once_with(
            "https://api.cloudflare.com/client/v4/zones/test_zone/purge_cache",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test_key",
            },
            json={"purge_everything": True},
            timeout=30,
        )


def test_purge_cache_failure(monkeypatch, mock_required_settings):
    # Mock environment variables
    monkeypatch.setenv("CACHE_PURGE", "test_key")
    monkeypatch.setenv("ZONE_ID", "test_zone")

    # Mock failed response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    with patch("generate_and_upload.requests.post", return_value=mock_response):
        assert gau.purge_cache() is False


def test_purge_cache_missing_env_vars(monkeypatch, mock_required_settings):
    # CACHE_PURGE and ZONE_ID are "" from conftest seeding — should return early
    with patch("generate_and_upload.requests.post") as mock_post:
        assert gau.purge_cache() is False
        mock_post.assert_not_called()


def test_purge_cache_partial_env_vars(monkeypatch, mock_required_settings):
    # Set only CACHE_PURGE; ZONE_ID stays "" from conftest seeding
    monkeypatch.setenv("CACHE_PURGE", "test_key")

    # Should return early without making any requests
    with patch("generate_and_upload.requests.post") as mock_post:
        assert gau.purge_cache() is False
        mock_post.assert_not_called()


def test_refresh_cache_success():
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch(
        "generate_and_upload.requests.get", return_value=mock_response
    ) as mock_get:
        gau.refresh_cache()

        # Verify the API was called correctly
        mock_get.assert_called_once_with(
            "https://api.glacierconservancy.org/email.json", timeout=30
        )


def test_refresh_cache_failure():
    # Mock failed response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("generate_and_upload.requests.get", return_value=mock_response):
        gau.refresh_cache()  # Should not raise, just print error


def test_refresh_cache_request_exception():
    # Mock request exception
    with patch(
        "generate_and_upload.requests.get",
        side_effect=gau.requests.RequestException("Connection error"),
    ):
        gau.refresh_cache()  # Should not raise, just print error


def test_purge_cache_request_exception(monkeypatch, mock_required_settings):
    """Verify purge_cache catches RequestException and returns False."""
    monkeypatch.setenv("CACHE_PURGE", "test_key")
    monkeypatch.setenv("ZONE_ID", "test_zone")

    with patch(
        "generate_and_upload.requests.post",
        side_effect=gau.requests.RequestException("Connection timeout"),
    ):
        assert gau.purge_cache() is False


def test_gen_data_none_values_replaced(mock_all_data_sources, monkeypatch):
    """Verify that None values in gen_data output are replaced with empty strings."""
    monkeypatch.setattr(gau, "peak", lambda **kw: ("peak", None, "peak_map"))
    data, _ = gau.gen_data()
    assert data["peak_image"] == ""


# ============================================================================
# LKG Cache Integration Tests
# ============================================================================


class TestLKGSave:
    """Verify that successful module data is saved to LKG."""

    def test_successful_modules_saved_to_lkg(self, mock_all_data_sources):
        """gen_data should save successful module outputs to LKG cache."""
        gau.gen_data()
        cache = LKGCache.get_cache()
        # Dynamic modules saved
        assert cache.load("trails", ["trails"]) is not None
        assert cache.load("roads", ["roads"]) is not None
        assert cache.load("events", ["events"]) is not None
        # Date-deterministic modules saved
        peak_data = cache.load("peak", ["peak", "peak_map"])
        assert peak_data is not None
        assert peak_data["peak"] == "peak"

    def test_failed_module_not_saved_to_lkg(self, monkeypatch):
        """Failed modules should not overwrite LKG data with empty strings."""
        # Set up: all modules succeed
        monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
        monkeypatch.setattr(
            gau,
            "get_closed_trails",
            lambda: TrailsResult(closures=["trails_data"]),
        )
        monkeypatch.setattr(
            gau, "get_campground_status", lambda: CampgroundsResult(statuses=["cg"])
        )
        monkeypatch.setattr(
            gau, "get_road_status", lambda: RoadsResult(closures=["roads"])
        )
        monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: HikerBikerResult())
        monkeypatch.setattr(gau, "events_today", lambda: EventsResult())
        monkeypatch.setattr(gau, "get_image_otd", lambda **kw: ("img", "title", "link"))
        monkeypatch.setattr(gau, "peak", lambda **kw: ("pk", "pk_img", "pk_map"))
        monkeypatch.setattr(gau, "process_video", lambda: ("v", "s", "d"))
        monkeypatch.setattr(gau, "get_product", lambda **kw: ("t", "i", "l", "d"))
        monkeypatch.setattr(
            gau, "get_notices", lambda: NoticesResult(fallback_message="No notices")
        )
        monkeypatch.setattr(gau, "weather_image", lambda x, **kw: "weather_img")
        monkeypatch.setattr(gau, "get_gnpc_events", list)

        # First run: everything succeeds, LKG populated
        gau.gen_data()
        cache = LKGCache.get_cache()
        assert cache.load("trails", ["trails"]) is not None

        # Second run: trails fails
        monkeypatch.setattr(
            gau, "get_closed_trails", lambda: (_ for _ in ()).throw(ConnectionError)
        )
        gau.gen_data()
        # LKG for trails should still have the old good data
        assert cache.load("trails", ["trails"]) is not None


class TestLKGFallback:
    """Verify that LKG data is used as fallback when modules fail."""

    def _setup_all_mocks(self, monkeypatch):
        monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
        monkeypatch.setattr(
            gau, "get_closed_trails", lambda: TrailsResult(closures=["trails"])
        )
        monkeypatch.setattr(
            gau, "get_campground_status", lambda: CampgroundsResult(statuses=["cg"])
        )
        monkeypatch.setattr(
            gau, "get_road_status", lambda: RoadsResult(closures=["roads"])
        )
        monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: HikerBikerResult())
        monkeypatch.setattr(gau, "events_today", lambda: EventsResult())
        monkeypatch.setattr(gau, "get_image_otd", lambda **kw: ("img", "title", "link"))
        monkeypatch.setattr(gau, "peak", lambda **kw: ("pk", "pk_img", "map"))
        monkeypatch.setattr(gau, "process_video", lambda: ("v", "s", "d"))
        monkeypatch.setattr(gau, "get_product", lambda **kw: ("t", "i", "l", "d"))
        monkeypatch.setattr(
            gau, "get_notices", lambda: NoticesResult(fallback_message="No notices")
        )
        monkeypatch.setattr(gau, "weather_image", lambda x, **kw: "wi")
        monkeypatch.setattr(gau, "get_gnpc_events", list)

    def test_dynamic_module_uses_lkg_on_failure(self, monkeypatch):
        """When a dynamic module fails, its LKG data is returned."""
        self._setup_all_mocks(monkeypatch)
        gau.gen_data()  # Populate LKG

        # Simulate trails failure
        monkeypatch.setattr(
            gau,
            "get_closed_trails",
            lambda: (_ for _ in ()).throw(ConnectionError("down")),
        )
        result, _ = gau.gen_data()
        # From LKG, not empty default
        assert result["trails"] is not None

    def test_weather_lkg_fallback(self, monkeypatch):
        """Weather LKG fills in weather field when weather module fails."""
        self._setup_all_mocks(monkeypatch)
        gau.gen_data()  # Populate LKG with weather

        # Simulate weather failure
        monkeypatch.setattr(
            gau,
            "weather_data",
            lambda: (_ for _ in ()).throw(ConnectionError("down")),
        )
        result, _ = gau.gen_data()
        assert result["weather"] is not None

    def test_sunrise_lkg_fallback(self, monkeypatch):
        """Sunrise tuple is reconstructed from LKG on failure."""
        self._setup_all_mocks(monkeypatch)
        gau.gen_data()  # Populate LKG

        # Simulate sunrise failure
        monkeypatch.setattr(
            gau,
            "process_video",
            lambda: (_ for _ in ()).throw(ConnectionError("down")),
        )
        result, _ = gau.gen_data()
        assert result["sunrise_vid"] == "v"
        assert result["sunrise_still"] == "s"
        assert result["sunrise_str"] == "d"


class TestLKGDateDeterministic:
    """Verify date-deterministic modules use LKG as primary cache."""

    def _setup_all_mocks(self, monkeypatch):
        monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
        monkeypatch.setattr(
            gau, "get_closed_trails", lambda: TrailsResult(closures=["trails"])
        )
        monkeypatch.setattr(
            gau, "get_campground_status", lambda: CampgroundsResult(statuses=["cg"])
        )
        monkeypatch.setattr(
            gau, "get_road_status", lambda: RoadsResult(closures=["roads"])
        )
        monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: HikerBikerResult())
        monkeypatch.setattr(gau, "events_today", lambda: EventsResult())
        monkeypatch.setattr(gau, "get_image_otd", lambda **kw: ("img", "title", "link"))
        monkeypatch.setattr(gau, "peak", lambda **kw: ("pk", "pk_img", "map"))
        monkeypatch.setattr(gau, "process_video", lambda: ("v", "s", "d"))
        monkeypatch.setattr(gau, "get_product", lambda **kw: ("t", "i", "l", "d"))
        monkeypatch.setattr(
            gau, "get_notices", lambda: NoticesResult(fallback_message="No notices")
        )
        monkeypatch.setattr(gau, "weather_image", lambda x, **kw: "wi")
        monkeypatch.setattr(gau, "get_gnpc_events", list)

    def test_cached_module_skips_api_call(self, monkeypatch):
        """Date-deterministic modules skip API calls when LKG has today's data."""
        self._setup_all_mocks(monkeypatch)
        # Pre-populate LKG with all fields including image URL
        cache = LKGCache.get_cache()
        cache.save(
            "peak", {"peak": "Cached Peak", "peak_image": "cached_url", "peak_map": "m"}
        )

        call_count = 0
        original_peak = gau.peak

        def counting_peak(**kw):
            nonlocal call_count
            call_count += 1
            return original_peak(**kw)

        monkeypatch.setattr(gau, "peak", counting_peak)

        result, pending = gau.gen_data()
        assert call_count == 0  # Peak module was NOT called
        assert result["peak"] == "Cached Peak"
        assert result["peak_image"] == "cached_url"
        # No pending upload for peak_image (it has a URL, not None)
        assert not any(k == "peak_image" for k, _ in pending)

    def test_uncached_module_calls_api(self, monkeypatch):
        """Date-deterministic modules call API when LKG is empty."""
        self._setup_all_mocks(monkeypatch)
        # LKG is empty (fresh :memory: DB)

        result, _ = gau.gen_data()
        assert result["peak"] == "pk"  # From the mocked peak function


class TestClearCache:
    """Verify clear_cache clears date-deterministic LKG modules."""

    def test_clear_cache_removes_deterministic_lkg(self):
        """--force clears date-deterministic LKG data."""
        cache = LKGCache.get_cache()
        cache.save("peak", {"peak": "data"})
        cache.save("image_otd", {"image_otd": "data"})
        cache.save("product", {"product_title": "data"})
        cache.save("weather", {"weather": "data"})  # Dynamic, should survive

        gau.clear_cache()

        assert cache.load("peak", ["peak"]) is None
        assert cache.load("image_otd", ["image_otd"]) is None
        assert cache.load("product", ["product_title"]) is None
        # Dynamic module LKG preserved
        assert cache.load("weather", ["weather"]) == {"weather": "data"}
