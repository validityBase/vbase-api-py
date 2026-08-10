"""Retry configuration for the vBase API client."""

from dataclasses import dataclass
from typing import Tuple

DEFAULT_RETRY_STATUS_CODES = (408, 429, 500, 502, 503, 504)


@dataclass(frozen=True)
class RetryConfig:
    """Configure retry attempts and linear backoff for retry-safe API calls."""

    enabled: bool = True
    max_attempts: int = 3
    initial_delay: float = 1.0
    delay_increment: float = 1.0
    max_delay: float = 30.0
    retry_status_codes: Tuple[int, ...] = DEFAULT_RETRY_STATUS_CODES

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay < 0:
            raise ValueError("initial_delay cannot be negative")
        if self.delay_increment < 0:
            raise ValueError("delay_increment cannot be negative")
        if self.max_delay < 0:
            raise ValueError("max_delay cannot be negative")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay cannot be less than initial_delay")
        if any(status < 100 or status > 599 for status in self.retry_status_codes):
            raise ValueError("retry_status_codes must contain valid HTTP status codes")
