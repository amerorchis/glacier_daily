"""ThreadPoolExecutor subclass that propagates contextvars to child threads."""

from __future__ import annotations

import concurrent.futures
import contextvars
from collections.abc import Callable
from typing import Any


class ContextAwareExecutor(concurrent.futures.ThreadPoolExecutor):
    """ThreadPoolExecutor that copies the caller's context to each child thread.

    Python 3.11's ThreadPoolExecutor does not propagate contextvars.
    This subclass wraps each submitted callable in ``copy_context().run()``
    so that child threads inherit the parent's ContextVar values — notably
    the ``_active_capture`` used by ``@timed`` for error attribution.
    """

    def submit(
        self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any
    ) -> concurrent.futures.Future:
        ctx = contextvars.copy_context()
        return super().submit(ctx.run, fn, *args, **kwargs)
