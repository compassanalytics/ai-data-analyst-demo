"""Utility package for error handling and resilience patterns.

This package provides:
- Error classification and handling utilities
- Retry policies using tenacity
- Circuit breaker implementation for graceful degradation
- Query result caching with TTL and LRU eviction
"""

from .cache import (
    CacheConfig,
    CacheEntry,
    CacheStats,
    QueryCache,
    clear_query_cache,
    get_query_cache,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitBreakerStats,
    CircuitOpenError,
    CircuitState,
)
from .errors import (
    RETRYABLE_CATEGORIES,
    AgentError,
    AgentTimeoutError,
    AuthenticationError,
    ErrorCategory,
    NetworkError,
    ParseError,
    RateLimitError,
    SpaceUnavailableError,
    ValidationError,
    classify_error,
)
from .retry_policies import (
    RetryContext,
    create_genie_retry_policy,
    genie_retry_policy,
    is_retryable_exception,
    retry_with_config,
)

__all__ = [
    # Query cache
    "CacheConfig",
    "CacheEntry",
    "CacheStats",
    "QueryCache",
    "clear_query_cache",
    "get_query_cache",
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
