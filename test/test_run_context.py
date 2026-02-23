"""Tests for shared.run_context module."""

import logging

from shared.run_context import RunContext, RunIdFilter, get_run, reset_run, start_run


class TestRunContext:
    def test_run_context_generates_unique_ids(self):
        ctx1 = RunContext()
        ctx2 = RunContext()
        assert ctx1.run_id != ctx2.run_id

    def test_run_context_id_length(self):
        ctx = RunContext()
        assert len(ctx.run_id) == 8

    def test_run_context_stores_run_type(self):
        ctx = RunContext(run_type="web_update")
        assert ctx.run_type == "web_update"

    def test_run_context_default_run_type(self):
        ctx = RunContext()
        assert ctx.run_type == "email"

    def test_run_context_elapsed_seconds(self):
        ctx = RunContext()
        elapsed = ctx.elapsed_seconds()
        assert elapsed >= 0


class TestStartRun:
    def test_start_run_creates_context(self):
        run = start_run("email")
        assert run is not None
        assert run.run_type == "email"

    def test_start_run_sets_global(self):
        run = start_run("web_update")
        assert get_run() is run

    def test_start_run_replaces_previous(self):
        run1 = start_run("email")
        run2 = start_run("web_update")
        assert get_run() is run2
        assert run1.run_id != run2.run_id


class TestResetRun:
    def test_reset_clears_context(self):
        start_run("email")
        reset_run()
        assert get_run() is None


class TestRunIdFilter:
    def test_filter_injects_run_id(self):
        start_run("email")
        filt = RunIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        result = filt.filter(record)
        assert result is True
        assert hasattr(record, "run_id")
        assert record.run_id == get_run().run_id

    def test_filter_without_run_context(self):
        reset_run()
        filt = RunIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert record.run_id == "no-run"
