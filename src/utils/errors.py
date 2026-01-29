"""Error handling utilities for the multi-agent pipeline.

This module provides a comprehensive error hierarchy for classifying and handling
errors in the agent system, with support for retry decisions and user-friendly messaging.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Categories of errors for classification and handling decisions."""

    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    PARSE = "parse"
    SPACE_UNAVAILABLE = "space_unavailable"
    NETWORK = "network"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


# Categories that are safe to retry
RETRYABLE_CATEGORIES: set[ErrorCategory] = {
    ErrorCategory.TIMEOUT,
    ErrorCategory.RATE_LIMIT,
    ErrorCategory.NETWORK,
    ErrorCategory.SPACE_UNAVAILABLE,
}


# User-friendly messages for each error category
_USER_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.TIMEOUT: "The request timed out. Please try again or simplify your query.",
    ErrorCategory.RATE_LIMIT: "Too many requests. Please wait a moment and try again.",
    ErrorCategory.AUTH: "Authentication failed. Please check your credentials and permissions.",
    ErrorCategory.PARSE: "Failed to parse the response. The data format may be unexpected.",
    ErrorCategory.SPACE_UNAVAILABLE: "The data source is temporarily unavailable. Please try again later.",
    ErrorCategory.NETWORK: "Network error occurred. Please check your connection and try again.",
    ErrorCategory.VALIDATION: "Invalid request parameters. Please check your input.",
    ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again or contact support.",
}


class AgentError(Exception):
    """Base exception for all agent-related errors.

    Provides structured error information including category, retryability,
    the original exception, and contextual information.

    Attributes:
        category: The error category for classification
        original_error: The original exception that caused this error
        context: Additional context about when/where the error occurred
        message: Human-readable error message
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize an AgentError.

        Args:
            message: Human-readable error message
            category: Error category for classification
            original_error: The original exception that was caught
            context: Additional contextual information
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.original_error = original_error
        self.context: dict[str, Any] = context or {}

    @property
    def retryable(self) -> bool:
        """Check if this error is safe to retry.

        Returns:
            True if the error category is in RETRYABLE_CATEGORIES
        """
        return self.category in RETRYABLE_CATEGORIES

    def to_user_message(self) -> str:
        """Get a user-friendly message for this error.

        Returns:
            A user-friendly message appropriate for display
        """
        base_message = _USER_MESSAGES.get(self.category, _USER_MESSAGES[ErrorCategory.UNKNOWN])

        # Add context hints if available
        if self.context.get("space_name"):
            return f"{base_message} (Space: {self.context['space_name']})"

        return base_message

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, category={self.category}, retryable={self.retryable})"
        )


class AgentTimeoutError(AgentError):
    """Error raised when an operation times out."""

    def __init__(
        self,
        message: str = "Operation timed out",
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            original_error=original_error,
            context=context,
        )


class RateLimitError(AgentError):
    """Error raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            original_error=original_error,
            context=context,
        )


class AuthenticationError(AgentError):
    """Error raised for authentication or authorization failures."""

    def __init__(
        self,
        message: str = "Authentication failed",
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTH,
            original_error=original_error,
            context=context,
        )


class ParseError(AgentError):
    """Error raised when parsing responses fails."""

    def __init__(
        self,
        message: str = "Failed to parse response",
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.PARSE,
            original_error=original_error,
            context=context,
        )


class SpaceUnavailableError(AgentError):
    """Error raised when a Genie Space is unavailable."""

    def __init__(
        self,
        message: str = "Genie Space unavailable",
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SPACE_UNAVAILABLE,
            original_error=original_error,
            context=context,
        )


class NetworkError(AgentError):
    """Error raised for network-related failures."""

    def __init__(
        self,
        message: str = "Network error",
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            original_error=original_error,
            context=context,
        )


class ValidationError(AgentError):
    """Error raised for validation failures."""

    def __init__(
        self,
        message: str = "Validation failed",
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            original_error=original_error,
            context=context,
        )


def classify_error(
    error: Exception,
    context: dict[str, Any] | None = None,
) -> AgentError:
    """Classify an exception into an appropriate AgentError subclass.

    Inspects the exception message and type to determine the most
    appropriate error category.

    Args:
        error: The exception to classify
        context: Optional context to attach to the error

    Returns:
        An AgentError instance with the appropriate category
    """
    # If already an AgentError, add context and return
    if isinstance(error, AgentError):
        if context:
            error.context.update(context)
        return error

    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Timeout detection
    if any(keyword in error_str for keyword in ["timeout", "timed out", "deadline exceeded"]):
        return AgentTimeoutError(
            message=str(error),
            original_error=error,
            context=context,
        )

    # Rate limit detection (HTTP 429 or rate limit messages)
    if any(keyword in error_str for keyword in ["429", "rate limit", "too many requests", "throttl"]):
        return RateLimitError(
            message=str(error),
            original_error=error,
            context=context,
        )

    # Authentication/Authorization detection (HTTP 401, 403)
    if any(
        keyword in error_str
        for keyword in ["401", "403", "unauthorized", "forbidden", "authentication", "permission denied"]
    ):
        return AuthenticationError(
            message=str(error),
            original_error=error,
            context=context,
        )

    # Network error detection
    if any(
        keyword in error_str
        for keyword in [
            "connection",
            "network",
            "socket",
            "dns",
            "resolve",
            "unreachable",
            "refused",
            "reset",
            "broken pipe",
        ]
    ) or any(keyword in error_type for keyword in ["connection", "socket", "network"]):
        return NetworkError(
            message=str(error),
            original_error=error,
            context=context,
        )

    # Space unavailable detection (HTTP 503, 502, 504, circuit open)
    if any(
        keyword in error_str
        for keyword in [
            "503",
            "502",
            "504",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
            "space not found",
            "space unavailable",
            "circuit open",
            "circuit is open",
        ]
    ):
        return SpaceUnavailableError(
            message=str(error),
            original_error=error,
            context=context,
        )

    # Parse error detection
    if any(keyword in error_str for keyword in ["parse", "json", "decode", "unexpected token", "malformed"]) or any(
        keyword in error_type for keyword in ["json", "parse", "decode"]
    ):
        return ParseError(
            message=str(error),
            original_error=error,
            context=context,
        )

    # Validation error detection
    if (
        any(keyword in error_str for keyword in ["validation", "invalid", "required", "missing"])
        or "validation" in error_type
    ):
        return ValidationError(
            message=str(error),
            original_error=error,
            context=context,
        )

    # Default to unknown
    return AgentError(
        message=str(error),
        category=ErrorCategory.UNKNOWN,
        original_error=error,
        context=context,
    )
