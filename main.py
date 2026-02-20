#!/home/pi/.local/bin/uv run --python 3.9 python

"""
This script performs the Glacier Daily Update by retrieving subscribers,
generating data, uploading it to a website, and sending emails to subscribers.
"""

import argparse
from time import sleep

from drip.drip_actions import bulk_workflow_trigger, get_subs
from generate_and_upload import serve_api
from shared.config_validation import validate_config
from shared.logging_config import get_logger, setup_logging
from shared.settings import get_settings
from sunrise_timelapse.sleep_to_sunrise import sleep_time as sleep_to_sunrise

logger = get_logger(__name__)


def main(
    tag: str = "Glacier Daily Update", test: bool = False, force: bool = False
) -> None:
    """
    Main function to perform the Glacier Daily Update.

    Args:
        tag (str): Tag to filter subscribers. Defaults to 'Glacier Daily Update'.
        force (bool): Clear cached data and re-fetch everything fresh.
    """
    get_settings()  # Load email.env so ENVIRONMENT is available
    setup_logging()
    validate_config()

    sleep_to_sunrise()  # Sleep until sunrise timelapse is finished.

    # Retrieve subscribers from Drip.
    subscribers: list[str] = get_subs(tag)
    logger.info("Subscribers found")

    # Generated data and upload to website.
    serve_api(force=force)

    # See if this fixes the issue with timelapse not showing.
    sleep(10 if not test else 0)

    # Send the email to each subscriber using Drip API.
    bulk_workflow_trigger(subscribers)


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(description="Run Glacier Daily Update")
    parser.add_argument(
        "--tag",
        type=str,
        default="Glacier Daily Update",
        help="Tag to filter subscribers (default: Glacier Daily Update)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear cached data and re-fetch everything fresh",
    )
    args = parser.parse_args()

    test_mode = args.tag != "Glacier Daily Update"
    main(args.tag, test=test_mode, force=args.force)
