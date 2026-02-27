#!/home/pi/.local/bin/uv run --python 3.11 python

"""
This script performs the Glacier Daily Update by retrieving subscribers,
generating data, uploading it to a website, and sending emails to subscribers.
"""

import argparse
from time import sleep

from drip.canary_check import CanaryResult, check_canary_delivery
from drip.drip_actions import bulk_workflow_trigger, get_subs
from generate_and_upload import serve_api
from shared.config_validation import validate_config
from shared.lock import acquire_lock, release_lock
from shared.logging_config import get_logger, setup_logging
from shared.run_context import start_run
from shared.run_report import build_report, upload_status_report
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
        test (bool): Whether running in test mode (skips sleep delays).
        force (bool): Clear cached data and re-fetch everything fresh.
    """
    settings = get_settings()  # Load email.env so ENVIRONMENT is available
    run = start_run("email")
    setup_logging()
    logger.info("Starting run %s (type=%s)", run.run_id, run.run_type)
    validate_config()

    lock_fd = acquire_lock()
    if lock_fd is None:
        logger.error("Another instance is already running. Exiting.")
        return

    try:
        sleep_to_sunrise()  # Sleep until sunrise timelapse is finished.

        # Retrieve subscribers from Drip.
        subscribers: list[str] = get_subs(tag)
        logger.info("Subscribers found: %d", len(subscribers))

        batch_result = None
        canary_result: CanaryResult | None = None
        try:
            # Generate data and upload to website.
            serve_api(force=force)

            # Allow time for FTP-uploaded timelapse assets to propagate.
            sleep(10 if not test else 0)

            # Send the email to each subscriber using Drip API.
            batch_result = bulk_workflow_trigger(subscribers)

            # Canary verification: check actual delivery if Drip accepted
            if batch_result and batch_result.sent > 0:
                canary_result = check_canary_delivery()
        finally:
            report = build_report(environment=settings.ENVIRONMENT)
            report.subscriber_count = len(subscribers)
            if batch_result:
                report.email_delivery = {
                    "sent": batch_result.sent,
                    "failed": batch_result.failed,
                }
            if canary_result is not None:
                report.email_delivery["canary_verified"] = canary_result.verified
                report.email_delivery["canary_message"] = canary_result.message
                report.email_delivery["canary_elapsed_seconds"] = (
                    canary_result.elapsed_seconds
                )
            report.finalize_status()
            logger.info("Run complete: %s", report.overall_status)
            logger.info("Run report: %s", report.to_json())
            if settings.ENVIRONMENT == "production":
                try:
                    upload_status_report(report)
                except Exception:
                    logger.error("Failed to upload status report", exc_info=True)
    finally:
        release_lock(lock_fd)


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
