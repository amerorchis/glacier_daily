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
from shared.logging_config import get_logger, setup_logging
from shared.run_context import start_run
from shared.run_report import RunReport, complete_run
from shared.settings import get_settings
from sunrise_timelapse.sleep_to_sunrise import sleep_time as sleep_to_sunrise

logger = get_logger(__name__)


def email_content_ok(data: dict) -> bool:
    """Check the generated data has enough real content to be worth emailing.

    Sending a hollow email (every core section empty) is worse than not
    sending — wrong/empty info erodes trust more than a missed day. The
    email is considered sendable if at least one core section (weather,
    roads, trails) has substantive content. LKG fallbacks make an
    all-empty result rare: it means every core module failed with no
    good data from earlier in the day.
    """
    weather = data.get("weather")
    if getattr(weather, "daylight_message", "") or getattr(weather, "forecasts", []):
        return True
    roads = data.get("roads")
    if getattr(roads, "closures", []) or getattr(roads, "no_closures_message", ""):
        return True
    trails = data.get("trails")
    return bool(
        getattr(trails, "closures", []) or getattr(trails, "no_closures_message", "")
    )


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
            data = serve_api(force=force)
            api_complete = True

            if not email_content_ok(data):
                raise RuntimeError(
                    "Email content check failed: weather, roads, and trails "
                    "are all empty — not sending a hollow email"
                )

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

            def _decorate(report: RunReport) -> None:
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
                if canary_result is not None:
                    report.email_delivery["canary_verified"] = canary_result.verified
                    report.email_delivery["canary_message"] = canary_result.message
                    report.email_delivery["canary_elapsed_seconds"] = (
                        canary_result.elapsed_seconds
                    )

            complete_run(
                settings.ENVIRONMENT,
                failed=bool(run_error),
                decorate=_decorate,
            )
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
