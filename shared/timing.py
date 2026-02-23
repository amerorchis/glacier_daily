"""Lightweight timing instrumentation for data collection modules."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from shared.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ModuleResult:
    """Result of a single module's execution."""

    name: str
    status: str  # "success" or "error"
    duration_seconds: float
    error: str | None = None


@dataclass
class RunTiming:
    """Collects timing data for all modules in a run."""

    modules: dict[str, ModuleResult] = field(default_factory=dict)

    def record(self, result: ModuleResult) -> None:
        self.modules[result.name] = result

    def summary(self) -> dict[str, dict]:
        return {
            name: {
                "status": r.status,
                "duration_seconds": round(r.duration_seconds, 2),
                "error": r.error,
            }
            for name, r in self.modules.items()
        }


_timing: RunTiming | None = None


def get_timing() -> RunTiming:
    """Get the current RunTiming instance, creating one if needed."""
    global _timing
    if _timing is None:
        _timing = RunTiming()
    return _timing


def reset_timing() -> None:
    """Clear the timing data. Used in test teardown."""
    global _timing
    _timing = None


def timed(name: str) -> Callable:
    """Decorator that times a callable and records the result."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                elapsed = time.monotonic() - start
                logger.info("%s completed in %.2fs", name, elapsed)
                get_timing().record(
                    ModuleResult(
                        name=name,
                        status="success",
                        duration_seconds=elapsed,
                    )
                )
                return result
            except Exception as e:
                elapsed = time.monotonic() - start
                logger.error("%s failed after %.2fs: %s", name, elapsed, e)
                get_timing().record(
                    ModuleResult(
                        name=name,
                        status="error",
                        duration_seconds=elapsed,
                        error=str(e),
                    )
                )
                raise

        return wrapper

    return decorator
