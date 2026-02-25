"""Canary mailbox verification for end-to-end email delivery confirmation.

After the Drip bulk workflow trigger, this module connects to a Gmail
mailbox via IMAP to verify that the canary subscriber actually received
the email. This provides proof of delivery beyond Drip's HTTP 201
"events accepted" response.

If CANARY_EMAIL or CANARY_IMAP_PASSWORD are not configured, the check
is silently skipped (graceful degradation).
"""

from __future__ import annotations

import contextlib
import email as email_lib
import email.utils
import imaplib
import time
from dataclasses import dataclass
from datetime import datetime

from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger
from shared.settings import get_settings

logger = get_logger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
DEFAULT_WAIT_SECONDS = 150  # 2.5 minutes for Drip to process and deliver
MAX_POLL_ATTEMPTS = 6
POLL_INTERVAL_SECONDS = 30
EXPECTED_SENDER = "glacier"  # substring match on From header


@dataclass
class CanaryResult:
    """Result of a canary mailbox check."""

    verified: bool
    message: str
    elapsed_seconds: float = 0.0


def is_configured() -> bool:
    """Return True if canary credentials are set."""
    settings = get_settings()
    return bool(settings.CANARY_EMAIL and settings.CANARY_IMAP_PASSWORD)


def check_canary_delivery(
    wait_seconds: int = DEFAULT_WAIT_SECONDS,
    max_attempts: int = MAX_POLL_ATTEMPTS,
    poll_interval: int = POLL_INTERVAL_SECONDS,
) -> CanaryResult:
    """Check the canary Gmail mailbox for today's delivery.

    1. Wait initial ``wait_seconds`` for Drip to process and deliver.
    2. Connect to Gmail IMAP and search for today's email.
    3. If not found, poll up to ``max_attempts`` times.
    4. On match, delete the message and return verified=True.

    Returns:
        CanaryResult with verified status and descriptive message.
    """
    settings = get_settings()
    if not is_configured():
        return CanaryResult(
            verified=False,
            message="Canary check skipped: credentials not configured",
        )

    start = time.monotonic()

    logger.info(
        "Canary: waiting %ds for Drip to deliver before checking mailbox",
        wait_seconds,
    )
    time.sleep(wait_seconds)

    canary_email = settings.CANARY_EMAIL
    canary_password = settings.CANARY_IMAP_PASSWORD
    today = now_mountain()
    imap_date = today.strftime("%d-%b-%Y")

    for attempt in range(1, max_attempts + 1):
        logger.info("Canary: IMAP check attempt %d/%d", attempt, max_attempts)
        try:
            found = _search_mailbox(canary_email, canary_password, imap_date, today)
            if found:
                elapsed = time.monotonic() - start
                logger.info(
                    "Canary: email verified in %.1fs (attempt %d)", elapsed, attempt
                )
                return CanaryResult(
                    verified=True,
                    message=f"Canary email received (attempt {attempt})",
                    elapsed_seconds=round(elapsed, 2),
                )
        except Exception:
            logger.warning("Canary: IMAP error on attempt %d", attempt, exc_info=True)

        if attempt < max_attempts:
            logger.info("Canary: waiting %ds before retry", poll_interval)
            time.sleep(poll_interval)

    elapsed = time.monotonic() - start
    logger.warning(
        "Canary: email NOT found after %d attempts (%.1fs)", max_attempts, elapsed
    )
    return CanaryResult(
        verified=False,
        message=f"Canary email not received after {max_attempts} attempts",
        elapsed_seconds=round(elapsed, 2),
    )


def _search_mailbox(
    email_addr: str,
    password: str,
    imap_date: str,
    today: datetime,
) -> bool:
    """Connect to Gmail IMAP and search for today's canary email.

    Returns True if a matching message was found (and deleted).
    """
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        conn.login(email_addr, password)
        conn.select("INBOX")

        # IMAP SINCE is inclusive of the given date
        status, data = conn.search(None, f'(SINCE "{imap_date}")')
        if status != "OK" or not data[0]:
            return False

        msg_ids = data[0].split()
        # Check messages in reverse order (newest first)
        for msg_id in reversed(msg_ids):
            status, msg_data = conn.fetch(msg_id, "(RFC822.HEADER)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw_header: bytes = msg_data[0][1]  # type: ignore[index]
            msg = email_lib.message_from_bytes(raw_header)
            from_header = (msg.get("From") or "").lower()

            if EXPECTED_SENDER in from_header and _is_today(
                msg.get("Date") or "", today
            ):
                # Delete the canary email to avoid inbox buildup
                conn.store(msg_id, "+FLAGS", "\\Deleted")
                conn.expunge()
                logger.debug("Canary: deleted message %s after verification", msg_id)
                return True

        return False
    finally:
        with contextlib.suppress(Exception):
            conn.logout()


def _is_today(date_str: str, today: datetime) -> bool:
    """Check if an email Date header corresponds to today (Mountain Time)."""
    try:
        parsed = email_lib.utils.parsedate_to_datetime(date_str)
        mountain_date = parsed.astimezone(today.tzinfo).date()
        return mountain_date == today.date()
    except Exception:
        return False
