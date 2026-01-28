"""Circuit breaker implementation for graceful degradation.

This module provides a thread-safe circuit breaker pattern implementation
for managing access to potentially failing services.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """States of a circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit tripped, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        timeout_seconds: Time to wait before transitioning to half-open
        success_threshold: Successes needed in half-open to close circuit
        half_open_max_calls: Max concurrent calls allowed in half-open state
    """

    failure_threshold: int = 5
    timeout_seconds: float = 60.0
    success_threshold: int = 2
    half_open_max_calls: int = 1


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker.

    Attributes:
        total_calls: Total number of calls
        successful_calls: Number of successful calls
        failed_calls: Number of failed calls
        rejected_calls: Number of calls rejected due to open circuit
        last_failure_time: Timestamp of last failure
        last_success_time: Timestamp of last success
        current_state: Current circuit state
    """

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED


class CircuitOpenError(Exception):
    """Error raised when circuit is open and call is rejected."""

    def __init__(self, circuit_name: str, remaining_seconds: float):
        self.circuit_name = circuit_name
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"Circuit '{circuit_name}' is open. "
            f"Retry in {remaining_seconds:.1f} seconds."
        )


class CircuitBreaker:
    """Thread-safe circuit breaker for managing service access.

    The circuit breaker monitors failures and prevents cascading failures
    by "opening" the circuit when too many failures occur.

    States:
        - CLOSED: Normal operation, all requests pass through
        - OPEN: Too many failures, requests fail fast
        - HALF_OPEN: Testing recovery, limited requests allowed

    Example:
        >>> cb = CircuitBreaker("genie-space-1", CircuitBreakerConfig())
        >>> if cb.can_execute():
        ...     try:
        ...         result = call_service()
        ...         cb.record_success()
        ...     except Exception as e:
        ...         cb.record_failure()
        ...         raise
        ... else:
        ...     # Handle circuit open
        ...     pass
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize a circuit breaker.

        Args:
            name: Unique identifier for this circuit
            config: Configuration settings (uses defaults if not provided)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0
        self._total_calls = 0
        self._successful_calls = 0
        self._failed_calls = 0
        self._rejected_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state (checking for automatic transitions)."""
        with self._lock:
            return self._get_current_state()

    def _get_current_state(self) -> CircuitState:
        """Get current state, handling automatic transitions.

        Must be called while holding the lock.
        """
        if self._state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self._opened_at is not None:
                elapsed = time.time() - self._opened_at
                if elapsed >= self.config.timeout_seconds:
                    logger.info(
                        "Circuit '%s' transitioning from OPEN to HALF_OPEN "
                        "after %.1fs timeout",
                        self.name,
                        elapsed,
                    )
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0

        return self._state

    def can_execute(self) -> bool:
        """Check if a call can be executed.

        Returns:
            True if the call is allowed, False if circuit is open
        """
        with self._lock:
            state = self._get_current_state()

            if state == CircuitState.CLOSED:
                return True

            if state == CircuitState.OPEN:
                return False

            # HALF_OPEN: allow limited calls
            if self._half_open_calls < self.config.half_open_max_calls:
                return True

            return False

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            current_time = time.time()
            self._last_success_time = current_time
            self._total_calls += 1
            self._successful_calls += 1

            state = self._get_current_state()

            if state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls -= 1

                # Check if we should close the circuit
                if self._success_count >= self.config.success_threshold:
                    logger.info(
                        "Circuit '%s' closing after %d consecutive successes",
                        self.name,
                        self._success_count,
                    )
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0

            elif state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            current_time = time.time()
            self._last_failure_time = current_time
            self._total_calls += 1
            self._failed_calls += 1

            state = self._get_current_state()

            if state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                logger.warning(
                    "Circuit '%s' reopening after failure in HALF_OPEN state",
                    self.name,
                )
                self._state = CircuitState.OPEN
                self._opened_at = current_time
                self._half_open_calls = 0
                self._success_count = 0

            elif state == CircuitState.CLOSED:
                self._failure_count += 1

                # Check if we should open the circuit
                if self._failure_count >= self.config.failure_threshold:
                    logger.warning(
                        "Circuit '%s' opening after %d consecutive failures",
                        self.name,
                        self._failure_count,
                    )
                    self._state = CircuitState.OPEN
                    self._opened_at = current_time

    def record_rejection(self) -> None:
        """Record a rejected call (when circuit is open)."""
        with self._lock:
            self._rejected_calls += 1

    def acquire_half_open_permit(self) -> bool:
        """Try to acquire a permit for a half-open call.

        Returns:
            True if permit acquired, False otherwise
        """
        with self._lock:
            state = self._get_current_state()

            if state != CircuitState.HALF_OPEN:
                return state == CircuitState.CLOSED

            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True

            return False

    def get_remaining_timeout(self) -> float:
        """Get remaining time until circuit transitions to half-open.

        Returns:
            Remaining seconds, or 0 if not in OPEN state
        """
        with self._lock:
            if self._state != CircuitState.OPEN or self._opened_at is None:
                return 0.0

            elapsed = time.time() - self._opened_at
            remaining = self.config.timeout_seconds - elapsed
            return max(0.0, remaining)

    def get_stats(self) -> CircuitBreakerStats:
        """Get current statistics for this circuit breaker.

        Returns:
            CircuitBreakerStats with current metrics
        """
        with self._lock:
            return CircuitBreakerStats(
                total_calls=self._total_calls,
                successful_calls=self._successful_calls,
                failed_calls=self._failed_calls,
                rejected_calls=self._rejected_calls,
                last_failure_time=self._last_failure_time,
                last_success_time=self._last_success_time,
                current_state=self._get_current_state(),
            )

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._last_success_time = None
            self._opened_at = None
            self._half_open_calls = 0
            logger.info("Circuit '%s' reset to CLOSED state", self.name)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    Provides centralized access to circuit breakers by name, with
    automatic creation using default or custom configurations.

    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> cb = registry.get("genie-space-1")
        >>> if cb.can_execute():
        ...     # proceed with call
    """

    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        """Initialize the registry.

        Args:
            default_config: Default configuration for new circuit breakers
        """
        self._default_config = default_config or CircuitBreakerConfig()
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by name.

        Args:
            name: Unique identifier for the circuit breaker
            config: Optional custom configuration (only used on creation)

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config or self._default_config,
                )
            return self._breakers[name]

    def get_all(self) -> dict[str, CircuitBreaker]:
        """Get all registered circuit breakers.

        Returns:
            Dictionary of circuit breakers by name
        """
        with self._lock:
            return dict(self._breakers)

    def get_all_stats(self) -> dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers.

        Returns:
            Dictionary of stats by circuit breaker name
        """
        with self._lock:
            return {name: cb.get_stats() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        with self._lock:
            for cb in self._breakers.values():
                cb.reset()

    def remove(self, name: str) -> bool:
        """Remove a circuit breaker from the registry.

        Args:
            name: Name of the circuit breaker to remove

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                return True
            return False
