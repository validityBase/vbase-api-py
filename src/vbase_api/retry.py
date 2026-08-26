"""Default Tenacity retry policy for the vBase API client."""

import requests
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt
from tenacity.wait import wait_incrementing

DEFAULT_RETRY_STATUS_CODES = (408, 429, 500, 502, 503, 504)


def default_retrying() -> Retrying:
    """Return the default retry controller for retry-safe API operations."""
    return Retrying(
        stop=stop_after_attempt(3),
        wait=wait_incrementing(start=2, increment=2, max=30),
        retry=retry_if_exception_type(
            (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            )
        ),
        reraise=True,
    )
