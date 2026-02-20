from unittest.mock import MagicMock, patch

import pytest

import generate_and_upload as gau


def make_fake_weather():
    class FakeWeather:
        message1 = "Weather1"
        message2 = "Weather2"
        season = "summer"
        results = [1, 2, 3]

    return FakeWeather()


@pytest.fixture
def mock_all_data_sources(monkeypatch):
    """Fixture to mock all data sources used by gen_data()."""
    monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
    monkeypatch.setattr(gau, "get_closed_trails", lambda: "trails")
    monkeypatch.setattr(gau, "get_campground_status", lambda: "campgrounds")
    monkeypatch.setattr(gau, "get_road_status", lambda: "roads")
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: "hikerbiker")
    monkeypatch.setattr(gau, "events_today", lambda: "events")
    monkeypatch.setattr(gau, "get_image_otd", lambda: ("img", "img_title", "img_link"))
    monkeypatch.setattr(gau, "peak", lambda: ("peak", "peak_img", "peak_map"))
    monkeypatch.setattr(gau, "process_video", lambda: ("vid", "still", "descriptor"))
    monkeypatch.setattr(
        gau, "get_product", lambda: ("prod_title", "prod_img", "prod_link", "prod_desc")
    )
    monkeypatch.setattr(gau, "get_notices", lambda: "notices")
    monkeypatch.setattr(gau, "html_safe", lambda x: x)
    monkeypatch.setattr(gau, "weather_image", lambda x: "weather_img")


def test_gen_data_keys_present(mock_all_data_sources):
    """Verify all expected keys are present in gen_data output."""
    data = gau.gen_data()

    expected_keys = [
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
        "sunrise_str",
    ]

    for key in expected_keys:
        assert key in data, f"Expected key '{key}' not found in gen_data output"


def test_gen_data_string_fields_are_strings(mock_all_data_sources):
    """Verify string fields return str type (empty string is valid)."""
    data = gau.gen_data()

    # These fields should always be strings (possibly empty)
    string_fields = [
        "date",
        "today",
        "events",
        "weather1",
        "weather2",
        "season",
        "trails",
        "campgrounds",
        "roads",
        "hikerbiker",
        "notices",
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
        assert isinstance(
            value, str
        ), f"Field '{key}' should be str, got {type(value).__name__}"


def test_gen_data_nullable_image_fields(mock_all_data_sources):
    """Verify image fields can be str or None."""
    data = gau.gen_data()

    # These fields may be None or str (URL or empty string)
    nullable_fields = [
        "peak_image",
        "product_image",
    ]

    for key in nullable_fields:
        value = data.get(key)
        assert value is None or isinstance(
            value, str
        ), f"Field '{key}' should be str or None, got {type(value).__name__}"


def test_gen_data_returns_dict(mock_all_data_sources):
    """Verify gen_data returns a dictionary."""
    data = gau.gen_data()
    assert isinstance(
        data, dict
    ), f"gen_data should return dict, got {type(data).__name__}"


def test_gen_data_with_empty_returns(monkeypatch):
    """Verify gen_data handles modules that return empty values gracefully."""
    # Simulate graceful degradation - some modules return empty
    monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
    monkeypatch.setattr(gau, "get_closed_trails", lambda: "")  # Empty
    monkeypatch.setattr(gau, "get_campground_status", lambda: "")  # Empty
    monkeypatch.setattr(gau, "get_road_status", lambda: "")  # Empty
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: "")  # Empty
    monkeypatch.setattr(gau, "events_today", lambda: "")  # Empty
    monkeypatch.setattr(gau, "get_image_otd", lambda: ("", "", ""))  # Empty tuple
    monkeypatch.setattr(gau, "peak", lambda: ("", None, ""))  # None for image
    monkeypatch.setattr(gau, "process_video", lambda: ("", "", ""))  # Empty
    monkeypatch.setattr(
        gau, "get_product", lambda: ("", None, "", "")
    )  # None for image
    monkeypatch.setattr(gau, "get_notices", lambda: "")  # Empty
    monkeypatch.setattr(gau, "html_safe", lambda x: x)
    monkeypatch.setattr(gau, "weather_image", lambda x: "")  # Empty

    # Should not raise even with empty values
    data = gau.gen_data()
    assert isinstance(data, dict)
    assert "date" in data  # Should still have date


def test_write_data_to_json(tmp_path, monkeypatch):
    # Patch get_gnpc_events to avoid network
    monkeypatch.setattr(gau, "get_gnpc_events", lambda: "gnpc_events")
    fake_data = {"foo": "bar", "baz": "qux"}
    out = gau.write_data_to_json(fake_data, "test.json")
    assert out.endswith("test.json")
    # Check file contents
    with open(out, encoding="utf-8") as f:
        content = f.read()
        assert "foo" in content and "baz" in content and "gnpc-events" in content


def test_send_to_server(monkeypatch):
    called = {}
    monkeypatch.setattr(
        gau,
        "upload_file",
        lambda d, f, p: called.update({"dir": d, "file": f, "path": p}),
    )
    gau.send_to_server("/tmp/test.json", "api")
    assert called["dir"] == "api"
    assert called["file"] == "test.json"
    assert called["path"] == "/tmp/test.json"


def test_serve_api(monkeypatch, tmp_path):
    # Patch everything to avoid side effects
    monkeypatch.setattr(gau, "gen_data", lambda: {"foo": "bar"})
    monkeypatch.setattr(gau, "web_version", lambda data, *a, **k: "webfile")
    monkeypatch.setattr(
        gau, "write_data_to_json", lambda data, doctype: str(tmp_path / "email.json")
    )
    monkeypatch.setattr(gau, "send_to_server", lambda file, directory: None)
    monkeypatch.setattr(gau, "purge_cache", lambda: None)
    monkeypatch.setattr(gau, "refresh_cache", lambda: None)
    monkeypatch.setattr(gau, "sleep", lambda _: None)
    # Should not raise
    gau.serve_api()


def test_serve_api_gen_data_raises(monkeypatch):
    """Verify serve_api propagates exceptions from gen_data."""

    def failing_gen_data():
        raise RuntimeError("data fetch failed")

    monkeypatch.setattr(gau, "gen_data", failing_gen_data)
    with pytest.raises(RuntimeError, match="data fetch failed"):
        gau.serve_api()


def test_gen_data_module_exception_handling(monkeypatch):
    """Verify gen_data propagates exceptions from individual data modules."""

    def failing_peak():
        raise ConnectionError("API unreachable")

    monkeypatch.setattr(gau, "weather_data", lambda: make_fake_weather())
    monkeypatch.setattr(gau, "get_closed_trails", lambda: "trails")
    monkeypatch.setattr(gau, "get_campground_status", lambda: "campgrounds")
    monkeypatch.setattr(gau, "get_road_status", lambda: "roads")
    monkeypatch.setattr(gau, "get_hiker_biker_status", lambda: "hikerbiker")
    monkeypatch.setattr(gau, "events_today", lambda: "events")
    monkeypatch.setattr(gau, "get_image_otd", lambda: ("img", "title", "link"))
    monkeypatch.setattr(gau, "peak", failing_peak)
    monkeypatch.setattr(gau, "process_video", lambda: ("vid", "still", "desc"))
    monkeypatch.setattr(gau, "get_product", lambda: ("t", "i", "l", "d"))
    monkeypatch.setattr(gau, "get_notices", lambda: "notices")
    monkeypatch.setattr(gau, "html_safe", lambda x: x)
    monkeypatch.setattr(gau, "weather_image", lambda x: "weather_img")

    with pytest.raises(ConnectionError, match="API unreachable"):
        gau.gen_data()


def test_purge_cache_success(monkeypatch):
    # Mock environment variables
    monkeypatch.setenv("CACHE_PURGE", "test_key")
    monkeypatch.setenv("ZONE_ID", "test_zone")

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch(
        "generate_and_upload.requests.post", return_value=mock_response
    ) as mock_post:
        gau.purge_cache()

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


def test_purge_cache_failure(monkeypatch):
    # Mock environment variables
    monkeypatch.setenv("CACHE_PURGE", "test_key")
    monkeypatch.setenv("ZONE_ID", "test_zone")

    # Mock failed response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    with patch("generate_and_upload.requests.post", return_value=mock_response):
        gau.purge_cache()  # Should not raise, just print error


def test_purge_cache_missing_env_vars(monkeypatch):
    # Ensure environment variables are not set
    monkeypatch.delenv("CACHE_PURGE", raising=False)
    monkeypatch.delenv("ZONE_ID", raising=False)

    # Should return early without making any requests
    with patch("generate_and_upload.requests.post") as mock_post:
        gau.purge_cache()
        mock_post.assert_not_called()


def test_purge_cache_partial_env_vars(monkeypatch):
    # Set only one environment variable
    monkeypatch.setenv("CACHE_PURGE", "test_key")
    monkeypatch.delenv("ZONE_ID", raising=False)

    # Should return early without making any requests
    with patch("generate_and_upload.requests.post") as mock_post:
        gau.purge_cache()
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


def test_purge_cache_request_exception(monkeypatch):
    """Verify purge_cache propagates RequestException (no try/except)."""
    monkeypatch.setenv("CACHE_PURGE", "test_key")
    monkeypatch.setenv("ZONE_ID", "test_zone")

    with (
        patch(
            "generate_and_upload.requests.post",
            side_effect=gau.requests.RequestException("Connection timeout"),
        ),
        pytest.raises(gau.requests.RequestException, match="Connection timeout"),
    ):
        gau.purge_cache()


def test_gen_data_none_values_replaced(mock_all_data_sources, monkeypatch):
    """Verify that None values in gen_data output are replaced with empty strings."""
    monkeypatch.setattr(gau, "peak", lambda: ("peak", None, "peak_map"))
    data = gau.gen_data()
    assert data["peak_image"] == ""
