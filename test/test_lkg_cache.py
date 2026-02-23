"""Tests for the LKG (Last Known Good) cache."""

import concurrent.futures

import pytest

from shared.lkg_cache import LKGCache


@pytest.fixture
def lkg_cache(tmp_path):
    """Create a fresh LKGCache using a temp database."""
    LKGCache.reset()
    db_path = str(tmp_path / "test_lkg.db")
    cache = LKGCache(db_path=db_path)
    LKGCache._instance = cache
    yield cache
    LKGCache.reset()


class TestLKGCacheSaveLoad:
    """Test basic save and load operations."""

    def test_save_and_load_round_trip(self, lkg_cache):
        lkg_cache.save("weather", {"weather1": "<b>Sunny</b>", "weather2": "Clear"})
        result = lkg_cache.load("weather", ["weather1", "weather2"])
        assert result == {"weather1": "<b>Sunny</b>", "weather2": "Clear"}

    def test_load_returns_none_for_missing_module(self, lkg_cache):
        result = lkg_cache.load("nonexistent", ["key1"])
        assert result is None

    def test_load_returns_none_if_any_key_missing(self, lkg_cache):
        lkg_cache.save("peak", {"peak": "Mt. Cleveland"})
        result = lkg_cache.load("peak", ["peak", "peak_image"])
        assert result is None

    def test_load_single_key(self, lkg_cache):
        lkg_cache.save("trails", {"trails": "<ul><li>Closed</li></ul>"})
        result = lkg_cache.load("trails", ["trails"])
        assert result == {"trails": "<ul><li>Closed</li></ul>"}

    def test_save_overwrites_existing_data(self, lkg_cache):
        lkg_cache.save("roads", {"roads": "old data"})
        lkg_cache.save("roads", {"roads": "new data"})
        result = lkg_cache.load("roads", ["roads"])
        assert result == {"roads": "new data"}

    def test_save_multiple_modules_independently(self, lkg_cache):
        lkg_cache.save("weather", {"weather1": "Sunny"})
        lkg_cache.save("roads", {"roads": "Open"})

        assert lkg_cache.load("weather", ["weather1"]) == {"weather1": "Sunny"}
        assert lkg_cache.load("roads", ["roads"]) == {"roads": "Open"}

    def test_save_empty_dict_is_noop(self, lkg_cache):
        lkg_cache.save("weather", {})
        result = lkg_cache.load("weather", ["weather1"])
        assert result is None


class TestLKGCacheDayBoundary:
    """Test that cache invalidates at the day boundary."""

    def test_load_returns_none_for_yesterday_data(self, lkg_cache):
        """Data saved 'yesterday' should not be returned."""
        # Save with yesterday's date by directly inserting
        lkg_cache._conn.execute(
            """INSERT OR REPLACE INTO lkg_data
               (module_name, field_key, value, saved_date)
               VALUES (?, ?, ?, ?)""",
            ("weather", "weather1", "old forecast", "2020-01-01"),
        )
        lkg_cache._conn.commit()

        result = lkg_cache.load("weather", ["weather1"])
        assert result is None

    def test_save_today_replaces_yesterday(self, lkg_cache):
        """Saving today overwrites yesterday's data."""
        lkg_cache._conn.execute(
            """INSERT OR REPLACE INTO lkg_data
               (module_name, field_key, value, saved_date)
               VALUES (?, ?, ?, ?)""",
            ("weather", "weather1", "yesterday", "2020-01-01"),
        )
        lkg_cache._conn.commit()

        lkg_cache.save("weather", {"weather1": "today"})
        result = lkg_cache.load("weather", ["weather1"])
        assert result == {"weather1": "today"}

    def test_mixed_dates_returns_none(self, lkg_cache):
        """If some keys are from today and some from yesterday, return None."""
        lkg_cache.save("peak", {"peak": "Mt. Cleveland"})
        # Manually set one key to yesterday
        lkg_cache._conn.execute(
            """INSERT OR REPLACE INTO lkg_data
               (module_name, field_key, value, saved_date)
               VALUES (?, ?, ?, ?)""",
            ("peak", "peak_image", "old_url", "2020-01-01"),
        )
        lkg_cache._conn.commit()

        result = lkg_cache.load("peak", ["peak", "peak_image"])
        assert result is None


class TestLKGCacheClearModules:
    """Test clearing specific modules."""

    def test_clear_removes_module_data(self, lkg_cache):
        lkg_cache.save("peak", {"peak": "Mt. Cleveland"})
        lkg_cache.save("weather", {"weather1": "Sunny"})

        lkg_cache.clear_modules(["peak"])

        assert lkg_cache.load("peak", ["peak"]) is None
        assert lkg_cache.load("weather", ["weather1"]) == {"weather1": "Sunny"}

    def test_clear_multiple_modules(self, lkg_cache):
        lkg_cache.save("peak", {"peak": "data"})
        lkg_cache.save("image_otd", {"image_otd": "data"})
        lkg_cache.save("product", {"product_title": "data"})

        lkg_cache.clear_modules(["peak", "image_otd", "product"])

        assert lkg_cache.load("peak", ["peak"]) is None
        assert lkg_cache.load("image_otd", ["image_otd"]) is None
        assert lkg_cache.load("product", ["product_title"]) is None

    def test_clear_nonexistent_module_is_noop(self, lkg_cache):
        lkg_cache.clear_modules(["nonexistent"])  # Should not raise


class TestLKGCacheThreadSafety:
    """Test that concurrent access works correctly."""

    def test_concurrent_saves(self, lkg_cache):
        """Multiple threads saving different modules simultaneously."""

        def save_module(i):
            lkg_cache.save(f"module_{i}", {f"key_{i}": f"value_{i}"})

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(save_module, range(20)))

        for i in range(20):
            result = lkg_cache.load(f"module_{i}", [f"key_{i}"])
            assert result == {f"key_{i}": f"value_{i}"}

    def test_concurrent_save_and_load(self, lkg_cache):
        """One thread saves while others load."""
        lkg_cache.save("shared", {"key": "initial"})

        def writer():
            for i in range(50):
                lkg_cache.save("shared", {"key": f"value_{i}"})

        def reader():
            for _ in range(50):
                result = lkg_cache.load("shared", ["key"])
                # Result should either be None (wrong date) or a valid dict
                if result is not None:
                    assert "key" in result

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(writer)]
            futures.extend(executor.submit(reader) for _ in range(3))
            for f in concurrent.futures.as_completed(futures):
                f.result()  # Raises if any thread failed


class TestLKGCacheSingleton:
    """Test singleton behavior."""

    def test_get_cache_returns_same_instance(self, lkg_cache):
        a = LKGCache.get_cache()
        b = LKGCache.get_cache()
        assert a is b

    def test_reset_clears_instance(self, lkg_cache):
        LKGCache.get_cache()  # Ensure instance exists
        LKGCache.reset()
        assert LKGCache._instance is None


class TestLKGCacheCorruptDB:
    """Test recovery from corrupt database."""

    def test_recovers_from_corrupt_db(self, tmp_path):
        """If the DB file is corrupt, LKGCache recreates it."""
        db_path = str(tmp_path / "corrupt.db")
        with open(db_path, "w") as f:
            f.write("this is not a valid sqlite database")

        LKGCache.reset()
        cache = LKGCache(db_path=db_path)
        # Should be usable after recovery
        cache.save("test", {"key": "value"})
        assert cache.load("test", ["key"]) == {"key": "value"}
        cache._conn.close()
