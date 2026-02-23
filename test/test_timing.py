"""Tests for shared.timing module."""

import pytest

from shared.timing import ModuleResult, RunTiming, get_timing, reset_timing, timed


class TestTimed:
    def test_timed_records_success(self):
        @timed("test_module")
        def succeeding():
            return 42

        result = succeeding()
        assert result == 42
        timing = get_timing()
        assert "test_module" in timing.modules
        assert timing.modules["test_module"].status == "success"
        assert timing.modules["test_module"].duration_seconds >= 0
        assert timing.modules["test_module"].error is None

    def test_timed_records_error(self):
        @timed("failing_module")
        def failing():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            failing()

        timing = get_timing()
        assert "failing_module" in timing.modules
        assert timing.modules["failing_module"].status == "error"
        assert timing.modules["failing_module"].error == "test error"
        assert timing.modules["failing_module"].duration_seconds >= 0

    def test_timed_preserves_function_name(self):
        @timed("my_func")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_timed_passes_args_and_kwargs(self):
        @timed("args_test")
        def add(a, b, extra=0):
            return a + b + extra

        assert add(1, 2, extra=3) == 6


class TestRunTiming:
    def test_record_and_summary(self):
        timing = RunTiming()
        timing.record(
            ModuleResult(name="weather", status="success", duration_seconds=1.234)
        )
        timing.record(
            ModuleResult(
                name="trails", status="error", duration_seconds=0.5, error="timeout"
            )
        )

        summary = timing.summary()
        assert summary["weather"]["status"] == "success"
        assert summary["weather"]["duration_seconds"] == 1.23
        assert summary["weather"]["error"] is None
        assert summary["trails"]["status"] == "error"
        assert summary["trails"]["error"] == "timeout"

    def test_empty_summary(self):
        timing = RunTiming()
        assert timing.summary() == {}


class TestGetTiming:
    def test_get_timing_creates_singleton(self):
        t1 = get_timing()
        t2 = get_timing()
        assert t1 is t2

    def test_reset_timing_clears(self):
        t1 = get_timing()
        reset_timing()
        t2 = get_timing()
        assert t1 is not t2
