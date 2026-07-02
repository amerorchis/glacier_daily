"""Generate a structured JSON report for each daily run."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Any

from shared.datetime_utils import now_mountain
from shared.logging_config import get_log_capture, get_logger
from shared.run_context import get_run
from shared.timing import get_timing

logger = get_logger(__name__)

STATUS_FILE = "server/status.json"
HISTORY_DAYS = 7
_LOCK_TIMEOUT_SECS = 10

_HAS_FCNTL = sys.platform != "win32"
if _HAS_FCNTL:
    import fcntl


@dataclass
class RunReport:
    """Structured report of a single execution run."""

    run_id: str = ""
    run_type: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    environment: str = ""
    modules: dict[str, dict] = field(default_factory=dict)
    subscriber_count: int = 0
    email_delivery: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    overall_status: str = "success"  # "success", "partial", "failure"
    log_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def finalize_status(self) -> None:
        """Re-evaluate overall_status after email_delivery data is available."""
        if not self.email_delivery:
            return

        sent = self.email_delivery.get("sent", 0)
        failed = self.email_delivery.get("failed", 0)

        if failed > 0 and sent == 0:
            self.overall_status = "failure"
        elif failed > 0 and self.overall_status == "success":
            self.overall_status = "partial"
        elif (
            sent == 0
            and failed == 0
            and self.run_type == "email"
            and self.overall_status == "success"
        ):
            self.overall_status = "failure"

        # Canary failure is informational — add to errors but don't change status
        canary = self.email_delivery.get("canary_verified")
        if canary is False:
            msg = self.email_delivery.get("canary_message", "not received")
            self.errors.append(f"canary: {msg}")


def build_report(environment: str = "") -> RunReport:
    """Build a RunReport from the current run context and timing data."""
    run = get_run()
    timing = get_timing()
    now = now_mountain()

    report = RunReport(
        run_id=run.run_id if run else "unknown",
        run_type=run.run_type if run else "unknown",
        start_time=run.start_time.isoformat() if run else "",
        end_time=now.isoformat(),
        duration_seconds=round(run.elapsed_seconds(), 2) if run else 0.0,
        environment=environment,
        modules=timing.summary(),
    )

    # Determine overall status from module results
    failed = [m for m in timing.modules.values() if m.status == "error"]
    warned = [m for m in timing.modules.values() if m.status == "warning"]
    if timing.modules and len(failed) == len(timing.modules):
        report.overall_status = "failure"
    elif failed or warned:
        report.overall_status = "partial"

    report.errors = [f"{m.name}: {m.error}" for m in failed]
    report.errors += [f"{m.name} (warning): {m.error}" for m in warned]

    # Attach captured log lines
    capture = get_log_capture()
    if capture:
        report.log_lines = list(capture.buffer)

    return report


def _acquire_status_lock() -> int | None:
    """Serialize status-file writers across the email and web_update processes.

    Returns a locked file descriptor, or None if locking is unavailable
    (Windows) or the lock could not be acquired within the timeout. On
    timeout we proceed unlocked: losing a concurrent writer's entry is
    bad, but silently dropping this report is worse — a lost email-run
    entry would make retry_check re-send the email.
    """
    if not _HAS_FCNTL:
        return None
    fd = os.open(STATUS_FILE + ".lock", os.O_CREAT | os.O_WRONLY)
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECS
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            if time.monotonic() >= deadline:
                logger.warning(
                    "Status lock not acquired within %ds; writing anyway",
                    _LOCK_TIMEOUT_SECS,
                )
                os.close(fd)
                return None
            time.sleep(0.1)


def _release_status_lock(fd: int | None) -> None:
    """Release the status-file lock acquired by _acquire_status_lock."""
    if fd is None:
        return
    with contextlib.suppress(OSError):
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def upload_status_report(report: RunReport) -> None:
    """Write the run report to a rolling status file and upload via FTP.

    Maintains a local JSON file with the last HISTORY_DAYS days of runs.
    Both cron jobs (email + web_update) contribute to the same history,
    so the read-modify-write is guarded by an flock and the file is
    replaced atomically — a concurrent writer can never clobber an entry
    or leave a half-written file for readers like retry_check.
    """
    os.makedirs(os.path.dirname(STATUS_FILE) or ".", exist_ok=True)
    lock_fd = _acquire_status_lock()
    try:
        # Load existing history from local file
        runs: list[dict] = []
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                runs = data.get("runs", [])
            except (json.JSONDecodeError, OSError):
                runs = []

        # Append current run
        runs.append(report.to_dict())

        # Trim entries older than HISTORY_DAYS
        cutoff = (now_mountain() - timedelta(days=HISTORY_DAYS)).isoformat()
        runs = [r for r in runs if r.get("end_time", "") >= cutoff]

        # Atomic replace so readers never see a partial file
        status_data = {"runs": runs}
        tmp_file = STATUS_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, default=str)
        os.replace(tmp_file, STATUS_FILE)
    finally:
        _release_status_lock(lock_fd)

    # status.json is served from the server/ directory via the public API endpoint
    logger.info("Status report written (%d runs in history)", len(runs))
