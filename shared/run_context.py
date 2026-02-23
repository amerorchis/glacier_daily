"""Run context for correlating all log messages in a single daily run."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from shared.datetime_utils import now_mountain


class RunContext:
    """Holds metadata about a single execution run."""

    def __init__(self, run_type: str = "email") -> None:
        self.run_id: str = uuid.uuid4().hex[:8]
        self.start_time: datetime = now_mountain()
        self.run_type: str = run_type

    def elapsed_seconds(self) -> float:
        return (now_mountain() - self.start_time).total_seconds()


_current_run: RunContext | None = None


def start_run(run_type: str = "email") -> RunContext:
    """Start a new run context. Call once at application startup."""
    global _current_run
    _current_run = RunContext(run_type=run_type)
    return _current_run


def get_run() -> RunContext | None:
    """Get the current run context, or None if not started."""
    return _current_run


def reset_run() -> None:
    """Clear the current run context. Used in test teardown."""
    global _current_run
    _current_run = None


class RunIdFilter(logging.Filter):
    """Logging filter that injects run_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_run()
        record.run_id = ctx.run_id if ctx else "no-run"
        return True
