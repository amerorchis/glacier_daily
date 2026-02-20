"""
Startup configuration validation for the Glacier Daily Update system.

Checks that all required environment variables are set before the application
attempts to use them, providing clear error messages at startup rather than
cryptic failures mid-execution.
"""

import os
import sys

from shared.logging_config import get_logger

logger = get_logger(__name__)

REQUIRED_VARS = [
    "NPS",
    "DRIP_TOKEN",
    "DRIP_ACCOUNT",
    "FTP_USERNAME",
    "FTP_PASSWORD",
    "MAPBOX_TOKEN",
]

OPTIONAL_VARS = [
    "CACHE_PURGE",
    "ZONE_ID",
]


def validate_config() -> None:
    """
    Validate that all required environment variables are set.

    Logs warnings for optional variables that are missing.
    Exits with an error if any required variables are missing.
    """
    missing_required = []
    for var in REQUIRED_VARS:
        if not os.environ.get(var):
            missing_required.append(var)

    for var in OPTIONAL_VARS:
        if not os.environ.get(var):
            logger.warning(f"Optional environment variable {var} is not set.")

    if missing_required:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_required)}"
        )
        sys.exit(1)

    logger.info("Configuration validation passed.")
