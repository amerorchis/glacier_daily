"""
Utility for loading environment variables with test-safe defaults.
"""

import os

from dotenv import load_dotenv


def load_env():
    """
    Load environment variables from the appropriate file.

    Uses TEMPLATE.env during testing to ensure no real API keys are used,
    and email.env during normal operation.
    """
    # Check if we're running tests
    is_testing = "PYTEST_CURRENT_TEST" in os.environ

    env_file = "TEMPLATE.env" if is_testing else "email.env"

    # Clear existing environment variables that might be loaded from shell
    # so we use only what's in our env file during testing
    if is_testing:
        env_vars_to_clear = [
            "NPS",
            "DRIP_TOKEN",
            "DRIP_ACCOUNT",
            "FTP_PASSWORD",
            "FTP_USERNAME",
            "FTP_SERVER",
            "ALERTS_PWD",
            "BC_TOKEN",
            "BC_STORE_HASH",
            "flickr_key",
            "flickr_secret",
            "glaciernps_uid",
            "webcam_ftp_user",
            "webcam_ftp_pword",
            "timelapse_server",
            "MAPBOX_TOKEN",
            "MAPBOX_ACCOUNT",
            "MAPBOX_STYLE",
            "SUNSETHUE_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "NOTICES_SPREADSHEET_ID",
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    load_dotenv(env_file, override=True)

    # Optional: Uncomment for debugging
    # print(f"[ENV_LOADER] Loaded {env_file} (testing={is_testing})")

    return env_file
