"""
Centralized logging configuration for the Glacier Daily Update system.

This module provides environment-aware logging configuration that:
- Uses console logging for development
- Uses file logging with rotation for production
- Reads environment type from the ENVIRONMENT variable
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging() -> None:
    """
    Initialize logging configuration based on environment.

    Should be called once at application startup.
    """
    environment = os.getenv("ENVIRONMENT", "development")

    # Create logs directory for production
    if environment == "production":
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if environment == "production":
        # Production: Log to rotating file
        file_handler = logging.handlers.RotatingFileHandler(
            filename="logs/glacier_daily.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    else:
        # Development: Log to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Usually __name__ from the calling module

    Returns:
        Logger instance for the module

    Example:
        from shared.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Starting data collection")
    """
    return logging.getLogger(name)
