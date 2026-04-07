#!/home/pi/.local/bin/uv run python

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
from shared.logging_config import get_log_capture, get_logger, setup_logging
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

    subscribers: list[str] = []
    try:
        batch_result = None
        canary_result: CanaryResult | None = None
        run_error: str | None = None
        api_complete = False
        try:
            sleep_to_sunrise()  # Sleep until sunrise timelapse is finished.

            # Retrieve subscribers from Drip.
            subscribers = get_subs(tag)
            logger.info("Subscribers found: %d", len(subscribers))

            if not subscribers:
                raise RuntimeError("No subscribers retrieved — Drip API may be down")

            # Generate data and upload to website.
            serve_api(force=force)
            api_complete = True

            # Allow time for FTP-uploaded timelapse assets to propagate.
            _TIMELAPSE_PROPAGATION_WAIT = 0 if test else 10
            sleep(_TIMELAPSE_PROPAGATION_WAIT)

            # Send the email to each subscriber using Drip API.
            batch_result = bulk_workflow_trigger(subscribers)

            # Canary verification: check actual delivery if Drip accepted
            if batch_result and batch_result.sent > 0:
                canary_result = check_canary_delivery()
        except Exception:
            phase = "data generation/upload" if not api_complete else "email delivery"
            logger.exception("%s failed", phase)
            run_error = f"{phase} raised an exception (see logs)"
        finally:
            report = build_report(environment=settings.ENVIRONMENT)
            report.subscriber_count = len(subscribers)
            if batch_result:
                report.email_delivery = {
                    "sent": batch_result.sent,
                    "failed": batch_result.failed,
                }
            if run_error:
                report.errors.append(run_error)
                if not batch_result:
                    report.email_delivery = {"sent": 0, "failed": 0}
                report.overall_status = "failure"
            if canary_result is not None:
                report.email_delivery["canary_verified"] = canary_result.verified
                report.email_delivery["canary_message"] = canary_result.message
                report.email_delivery["canary_elapsed_seconds"] = (
                    canary_result.elapsed_seconds
                )
            report.finalize_status()
            # Log status before building the report so it's captured in log_lines
            logger.info("Run complete: %s", report.overall_status)
            # Re-snapshot log buffer to include the status line and any error tracebacks
            capture = get_log_capture()
            if capture:
                report.log_lines = list(capture.buffer)
            if settings.ENVIRONMENT == "production":
                try:
                    upload_status_report(report)
                except Exception:
                    logger.exception("Failed to upload status report")
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
