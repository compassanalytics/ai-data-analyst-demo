"""Retry policies for agent operations using tenacity.

This module provides configurable retry policies for Genie API calls and other
agent operations, with support for exponential backoff and jitter.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)

from .errors import AgentError, classify_error

if TYPE_CHECKING:
    from src.config import Config

logger = logging.getLogger(__name__)

T = TypeVar("T")


def is_retryable_exception(exception: BaseException | Exception) -> bool:
    """Check if an exception is retryable.

    Args:
        exception: The exception to check

    Returns:
        True if the exception should be retried
    """
    if isinstance(exception, AgentError):
        return exception.retryable

    # Classify the exception to determine retryability
    # Only classify Exception, not BaseException (like KeyboardInterrupt)
    if isinstance(exception, Exception):
        classified = classify_error(exception)
        return classified.retryable
    return False


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log retry attempt information.

    Args:
        retry_state: State of the current retry attempt
    """
    if retry_state.outcome is not None and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        logger.warning(
            "Retry attempt %d failed: %s. Next retry in %.2f seconds.",
            retry_state.attempt_number,
            str(exception),
            retry_state.next_action.sleep if retry_state.next_action else 0,  # type: ignore
        )


def create_genie_retry_policy(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    timeout_seconds: float | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a retry policy decorator for Genie API calls.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        timeout_seconds: Optional total timeout for all attempts

    Returns:
        A retry decorator configured for Genie API calls
    """
    stop_conditions = [stop_after_attempt(max_retries + 1)]  # +1 because first attempt counts

    if timeout_seconds is not None:
        stop_conditions.append(stop_after_delay(timeout_seconds))

    # Combine stop conditions with any (stop on first condition met)
    if len(stop_conditions) > 1:
        from tenacity import stop_any

        stop_condition = stop_any(*stop_conditions)
    else:
        stop_condition = stop_conditions[0]

    return retry(
        retry=retry_if_exception(is_retryable_exception),
        stop=stop_condition,
        wait=wait_exponential_jitter(initial=base_delay, max=max_delay, jitter=base_delay * 0.5),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


# Pre-configured retry policy for standard Genie API calls
genie_retry_policy = create_genie_retry_policy(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
)


def retry_with_config(config: "Config") -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a retry policy using configuration settings.

    Args:
        config: Configuration instance with retry settings

    Returns:
        A retry decorator configured from config settings
    """
    return create_genie_retry_policy(
        max_retries=config.default_max_retries,
        base_delay=config.default_retry_base_delay,
        max_delay=config.default_retry_max_delay,
        timeout_seconds=float(config.default_timeout_seconds),
    )


class RetryContext:
    """Context manager for manual retry logic with remaining time tracking.

    Useful when you need more control over retry behavior, such as
    checking remaining time before each attempt.

    Example:
        >>> ctx = RetryContext(max_retries=3, timeout_seconds=120)
        >>> for attempt in ctx:
        ...     if ctx.remaining_time <= 0:
        ...         break
        ...     try:
        ...         result = do_operation()
        ...         break
        ...     except Exception as e:
        ...         if not ctx.should_retry(e):
        ...             raise
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: float = 120.0,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        """Initialize retry context.

        Args:
            max_retries: Maximum number of retry attempts
            timeout_seconds: Total timeout for all attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
        """
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._start_time: float | None = None
        self._attempt = 0
        self._last_error: Exception | None = None

    @property
    def remaining_time(self) -> float:
        """Get remaining time before timeout.

        Returns:
            Remaining seconds, or timeout_seconds if not started
        """
        if self._start_time is None:
            return self.timeout_seconds

        import time

        elapsed = time.time() - self._start_time
        return max(0, self.timeout_seconds - elapsed)

    @property
    def attempt_number(self) -> int:
        """Get current attempt number (1-indexed)."""
        return self._attempt

    @property
    def last_error(self) -> Exception | None:
        """Get the last error that occurred."""
        return self._last_error

    def should_retry(self, error: Exception) -> bool:
        """Check if the operation should be retried.

        Args:
            error: The exception that occurred

        Returns:
            True if retry is appropriate
        """
        self._last_error = error

        # Check if we've exceeded retries
        if self._attempt >= self.max_retries:
            return False

        # Check if we've exceeded timeout
        if self.remaining_time <= 0:
            return False

        # Check if error is retryable
        return is_retryable_exception(error)

    def get_delay(self) -> float:
        """Get the delay before the next retry attempt.

        Uses exponential backoff with jitter.

        Returns:
            Delay in seconds
        """
        import random

        # Exponential backoff: base * 2^attempt
        delay = min(self.base_delay * (2 ** self._attempt), self.max_delay)

        # Add jitter (up to 50% of delay)
        jitter = random.uniform(0, delay * 0.5)

        # Cap at remaining time
        return min(delay + jitter, self.remaining_time)

    def __iter__(self):
        """Iterate through retry attempts."""
        import time

        self._start_time = time.time()
        self._attempt = 0

        while self._attempt <= self.max_retries and self.remaining_time > 0:
            yield self._attempt
            self._attempt += 1

            # Sleep before next attempt (if not the first)
            if self._attempt <= self.max_retries and self.remaining_time > 0:
                delay = self.get_delay()
                if delay > 0 and delay < self.remaining_time:
                    time.sleep(delay)
