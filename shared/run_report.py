"""Generate a structured JSON report for each daily run."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from shared.datetime_utils import now_mountain
from shared.ftp import upload_file
from shared.logging_config import get_logger
from shared.run_context import get_run
from shared.timing import get_timing

logger = get_logger(__name__)

STATUS_FILE = "server/status.json"
STATUS_HTML = Path(__file__).resolve().parent.parent / "server" / "status.html"
HISTORY_DAYS = 7


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

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


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
    if timing.modules and len(failed) == len(timing.modules):
        report.overall_status = "failure"
    elif failed:
        report.overall_status = "partial"

    report.errors = [f"{m.name}: {m.error}" for m in failed]

    return report


def upload_status_report(report: RunReport) -> None:
    """Write the run report to a rolling status file and upload via FTP.

    Maintains a local JSON file with the last HISTORY_DAYS days of runs.
    Both cron jobs (email + web_update) contribute to the same history.
    """
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

    # Write and upload
    status_data = {"runs": runs}
    os.makedirs(os.path.dirname(STATUS_FILE) or ".", exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, default=str)

    upload_file("api", "status.json", STATUS_FILE)
    if STATUS_HTML.exists():
        upload_file("api", "status.html", str(STATUS_HTML))
    logger.info("Status report uploaded (%d runs in history)", len(runs))
