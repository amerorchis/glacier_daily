"""
Startup configuration validation for the Glacier Daily Update system.

Checks that all required environment variables are set before the application
attempts to use them, providing clear error messages at startup rather than
cryptic failures mid-execution.
"""

import sys

from shared.logging_config import get_logger
from shared.settings import ConfigError, get_settings

logger = get_logger(__name__)

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
    try:
        settings = get_settings()
    except ConfigError as exc:
        logger.error(str(exc))
        sys.exit(1)

    # Check that required fields are not empty strings
    missing_required = []
    for name in (
        "NPS",
        "DRIP_TOKEN",
        "DRIP_ACCOUNT",
        "FTP_USERNAME",
        "FTP_PASSWORD",
        "MAPBOX_TOKEN",
    ):
        if not getattr(settings, name):
            missing_required.append(name)

    for var in OPTIONAL_VARS:
        if not getattr(settings, var):
            logger.warning("Optional environment variable %s is not set.", var)

    if missing_required:
        logger.error(
            "Missing required environment variables: %s",
            ", ".join(missing_required),
        )
        sys.exit(1)

    logger.info("Configuration validation passed.")
