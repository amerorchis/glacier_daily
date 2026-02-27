"""
A decorator to retry an operation.
"""

import functools
from collections.abc import Callable
from time import sleep

from shared.logging_config import get_logger

logger = get_logger(__name__)


def retry(
    times: int, exceptions: tuple, default: object = "", backoff: int = 15
) -> Callable:
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    :param Exceptions: Lists of exceptions that trigger a retry attempt
    :type Exceptions: Tuple of Exceptions
    :param Default: Value to return is exception is not resolved in given # of attempts.
    :type Default: Str
    :param backoff: How long to wait between attempts
    :type backoff: Int = 15
    """

    def decorator(func):
        """
        Decorator
        """

        @functools.wraps(func)
        def newfn(*args, **kwargs):
            """
            The new function
            """
            attempt = 0
            last_exception = None
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        "Exception thrown when attempting to run %s, attempt %d of %d",
                        func.__name__,
                        attempt + 1,
                        times,
                    )
                    attempt += 1
                    sleep(backoff)

            logger.error(
                "All %d attempts failed for %s: %s",
                times,
                func.__name__,
                last_exception,
            )
            return default

        return newfn

    return decorator
