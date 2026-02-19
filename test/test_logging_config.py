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
