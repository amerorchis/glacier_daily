"""Tests for shared.logging_config module."""

import logging
import logging.handlers

import pytest

from shared.logging_config import (
    MAX_LOG_LINES,
    RunLogCapture,
    get_log_capture,
    get_logger,
    reset_log_capture,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_root_logger():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.level = original_level


def test_setup_logging_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    setup_logging()
    root = logging.getLogger()
    assert root.level == logging.INFO
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_setup_logging_production(monkeypatch, tmp_path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.chdir(tmp_path)
    setup_logging()
    root = logging.getLogger()
    assert any(
        isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers
    )
    # Production also adds a stderr handler at ERROR level for cron alerting
    stderr_handlers = [
        h
        for h in root.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(stderr_handlers) == 1
    assert stderr_handlers[0].level == logging.ERROR


def test_setup_logging_clears_existing_handlers(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())
    root.addHandler(logging.StreamHandler())
    setup_logging()
    # Console handler + RunLogCapture handler
    assert len(root.handlers) == 2


def test_get_logger_returns_logger():
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_run_id_filter_on_handlers(monkeypatch):
    """RunIdFilter must be on each handler so child loggers get run_id injected."""
    from shared.run_context import RunIdFilter

    monkeypatch.setenv("ENVIRONMENT", "development")
    setup_logging()
    root = logging.getLogger()
    for handler in root.handlers:
        assert any(isinstance(f, RunIdFilter) for f in handler.filters)


def test_child_logger_formats_run_id(monkeypatch):
    """A child logger's record must include run_id when formatted by root's handler."""
    from shared.run_context import start_run

    monkeypatch.setenv("ENVIRONMENT", "development")
    start_run("email")
    setup_logging()

    child = logging.getLogger("test.child.logger")
    handler = logging.getLogger().handlers[0]

    record = child.makeRecord(
        "test.child.logger", logging.INFO, "", 0, "hello", (), None
    )
    # The handler's filter should inject run_id
    handler.filter(record)
    assert hasattr(record, "run_id")
    assert record.run_id != "no-run"
    # Formatting should not raise
    formatted = handler.format(record)
    assert "[" in formatted
    assert "test.child.logger" in formatted


class TestRunLogCapture:
    def test_capture_handler_created_by_setup(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        setup_logging()
        capture = get_log_capture()
        assert capture is not None
        assert isinstance(capture, RunLogCapture)

    def test_capture_records_info_lines(self, monkeypatch):
        from shared.run_context import start_run

        monkeypatch.setenv("ENVIRONMENT", "development")
        start_run("email")
        setup_logging()
        logger = logging.getLogger("test.capture")
        logger.info("test message")
        capture = get_log_capture()
        assert any("test message" in line for line in capture.buffer)

    def test_capture_ignores_debug(self, monkeypatch):
        from shared.run_context import start_run

        monkeypatch.setenv("ENVIRONMENT", "development")
        start_run("email")
        setup_logging()
        logger = logging.getLogger("test.capture.debug")
        logger.debug("should not appear")
        capture = get_log_capture()
        assert not any("should not appear" in line for line in capture.buffer)

    def test_capture_truncates_at_max(self, monkeypatch):
        from shared.run_context import start_run

        monkeypatch.setenv("ENVIRONMENT", "development")
        start_run("email")
        setup_logging()
        logger = logging.getLogger("test.capture.max")
        for i in range(MAX_LOG_LINES + 50):
            logger.info("line %d", i)
        capture = get_log_capture()
        assert len(capture.buffer) == MAX_LOG_LINES + 1  # +1 for truncation sentinel
        assert "truncated" in capture.buffer[-1]

    def test_reset_log_capture(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        setup_logging()
        assert get_log_capture() is not None
        reset_log_capture()
        assert get_log_capture() is None

    def test_capture_active_in_production(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.chdir(tmp_path)
        setup_logging()
        assert get_log_capture() is not None
        assert isinstance(get_log_capture(), RunLogCapture)
