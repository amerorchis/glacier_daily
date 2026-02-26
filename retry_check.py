#!/home/pi/.local/bin/uv run --python 3.11 python

"""
Retry checker for Glacier Daily email.

Reads status.json to determine if today has a successful email run.
If not, and no other instance is running, triggers main.py.
Called by cron hourly during the day.

Exit codes:
    0 - No action needed (already successful) or retry launched
    1 - Error reading status / launching retry
    3 - Another instance is already running (lock held)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from shared.datetime_utils import now_mountain
from shared.lock import _HAS_FCNTL
from shared.logging_config import get_logger, setup_logging
from shared.run_context import start_run
from shared.settings import get_settings

logger = get_logger(__name__)

STATUS_FILE = Path("server/status.json")
LOCK_FILE = Path(".glacier_daily.lock")
PROJECT_DIR = Path(__file__).resolve().parent


def has_successful_email_today() -> bool:
    """Check if today has a successful email run in status.json."""
    if not STATUS_FILE.exists():
        return False
    try:
        with open(STATUS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    today = now_mountain().strftime("%Y-%m-%d")
    for run in data.get("runs", []):
        if (
            run.get("run_type") == "email"
            and run.get("overall_status") == "success"
            and run.get("start_time", "").startswith(today)
        ):
            return True
    return False


def is_locked() -> bool:
    """Check if the lock file exists and its PID is still alive."""
    if not _HAS_FCNTL:
        return False
    if not LOCK_FILE.exists():
        return False
    try:
        pid = int(LOCK_FILE.read_text().strip())
        os.kill(pid, 0)  # Signal 0 = check if process exists
        return True
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        # Stale lock file — process is gone
        return False


def retry(tag: str | None = None, dry_run: bool = False) -> int:
    """Run the retry check logic. Returns an exit code."""
    # 1. Check if today already has a successful email run
    if has_successful_email_today():
        logger.info("Today already has a successful email run. No action needed.")
        return 0

    # 2. Check if another instance is currently running
    if is_locked():
        logger.info("Lock file present and PID alive. Another run is in progress.")
        return 3

    # 3. Launch retry
    if dry_run:
        logger.info("DRY RUN: Would launch main.py%s", f" --tag {tag!r}" if tag else "")
        return 0

    cmd = [sys.executable, "main.py"]
    if tag:
        cmd += ["--tag", tag]

    logger.info("No successful email run today. Launching: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, cwd=str(PROJECT_DIR), timeout=30 * 60)
        if result.returncode == 0:
            logger.info("Retry completed successfully (exit code 0)")
        else:
            logger.error("Retry exited with code %d", result.returncode)
        return result.returncode
    except subprocess.TimeoutExpired:
        logger.error("Retry timed out after 30 minutes")
        return 1
    except Exception:
        logger.error("Failed to launch retry", exc_info=True)
        return 1


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(description="Glacier Daily retry checker")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would happen without launching main.py",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Tag to pass through to main.py (e.g. 'Test Glacier Daily Update')",
    )
    args = parser.parse_args()

    get_settings()
    start_run("retry_check")
    setup_logging()

    sys.exit(retry(tag=args.tag, dry_run=args.dry_run))
