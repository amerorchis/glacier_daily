from time import sleep

def retry(times: int, exceptions: tuple, default: str = '', backoff: int = 15):
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
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    print(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func, attempt + 1, times)
                    )
                    attempt += 1
                    sleep(backoff)

            return default
        return newfn
    return decorator

