# Code copied from CPython test.support module licensed under the PSF
import time


def busy_retry(timeout, err_msg=None, /, *, error=True):
    """
    Run the loop body until "break" stops the loop.

    After *timeout* seconds, raise an AssertionError if *error* is true,
    or just stop if *error is false.

    Example:

        for _ in support.busy_retry(support.SHORT_TIMEOUT):
            if check():
                break

    Example of error=False usage:

        for _ in support.busy_retry(support.SHORT_TIMEOUT, error=False):
            if check():
                break
        else:
            raise RuntimeError('my custom error')

    """
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    start_time = time.monotonic()
    deadline = start_time + timeout

    while True:
        yield

        if time.monotonic() >= deadline:
            break

    if error:
        dt = time.monotonic() - start_time
        msg = f"timeout ({dt:.1f} seconds)"
        if err_msg:
            msg = f"{msg}: {err_msg}"
        raise AssertionError(msg)


def sleeping_retry(
        timeout, err_msg=None, /, *, init_delay=0.010, max_delay=1.0, error=True):
    """
    Wait strategy that applies exponential backoff.

    Run the loop body until "break" stops the loop. Sleep at each loop
    iteration, but not at the first iteration. The sleep delay is doubled at
    each iteration (up to *max_delay* seconds).

    See busy_retry() documentation for the parameters usage.

    Example raising an exception after SHORT_TIMEOUT seconds:

        for _ in support.sleeping_retry(support.SHORT_TIMEOUT):
            if check():
                break

    Example of error=False usage:

        for _ in support.sleeping_retry(support.SHORT_TIMEOUT, error=False):
            if check():
                break
        else:
            raise RuntimeError('my custom error')
    """

    delay = init_delay
    for _ in busy_retry(timeout, err_msg, error=error):
        yield

        time.sleep(delay)
        delay = min(delay * 2, max_delay)
