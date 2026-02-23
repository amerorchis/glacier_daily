"""Tests for shared.logging_config module."""

import logging
import logging.handlers

import pytest

from shared.logging_config import get_logger, setup_logging


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
    assert len(root.handlers) == 1


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
