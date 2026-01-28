"""Utility package for error handling and resilience patterns.

This package provides:
- Error classification and handling utilities
- Retry policies using tenacity
- Circuit breaker implementation for graceful degradation
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitBreakerStats,
    CircuitOpenError,
    CircuitState,
)
from .errors import (
    AgentError,
    AgentTimeoutError,
    AuthenticationError,
    ErrorCategory,
    NetworkError,
    ParseError,
    RateLimitError,
    RETRYABLE_CATEGORIES,
    SpaceUnavailableError,
    ValidationError,
    classify_error,
)
from .retry_policies import (
    create_genie_retry_policy,
    genie_retry_policy,
    is_retryable_exception,
    retry_with_config,
    RetryContext,
)

__all__ = [
    # Error handling
    "AgentError",
    "AgentTimeoutError",
    "AuthenticationError",
    "ErrorCategory",
    "NetworkError",
    "ParseError",
    "RateLimitError",
    "RETRYABLE_CATEGORIES",
    "SpaceUnavailableError",
    "ValidationError",
    "classify_error",
    # Retry policies
    "create_genie_retry_policy",
    "genie_retry_policy",
    "is_retryable_exception",
    "retry_with_config",
    "RetryContext",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerRegistry",
    "CircuitBreakerStats",
    "CircuitOpenError",
    "CircuitState",
]
