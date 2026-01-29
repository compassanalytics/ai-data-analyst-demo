"""Configuration management for the AI Data Analyst demo.

Supports loading configuration from:
1. Environment variables
2. Databricks secrets (when running in Databricks)
3. .env file (for local development)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

# Try to load from .env file for local development
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _str_to_bool(value: str | bool | None) -> bool:
    """Convert string to boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return value.lower() in ("true", "1", "yes", "on")


@dataclass
class Config:
    """Configuration settings for the AI Data Analyst demo.

    Attributes:
        databricks_host: Databricks workspace URL
        databricks_token: Personal access token (for local dev only)
        genie_space_id: The Genie Space ID for data analysis
        warehouse_id: SQL Warehouse ID for queries
        model_endpoint: Model serving endpoint for ChatDatabricks
        mock_mode: Enable mock mode for demos without real Genie access
        vector_search_endpoint: Optional Vector Search endpoint
        vector_search_index: Optional Vector Search index name
        embedding_endpoint: Embedding model endpoint for Vector Search (managed embeddings)
        genie_spaces_json: JSON configuration for multiple Genie Spaces
        default_max_retries: Maximum number of retry attempts for operations
        default_retry_base_delay: Base delay between retries (seconds)
        default_retry_max_delay: Maximum delay between retries (seconds)
        default_timeout_seconds: Default timeout for operations (seconds)
        circuit_breaker_enabled: Enable circuit breaker pattern
        circuit_breaker_failure_threshold: Failures before circuit opens
        circuit_breaker_timeout_seconds: Time before circuit transitions to half-open
    """

    databricks_host: str = field(default="")
    databricks_token: str | None = field(default=None, repr=False)
    genie_space_id: str = field(default="")
    warehouse_id: str = field(default="")
    model_endpoint: str = field(default="databricks-meta-llama-3-3-70b-instruct")
    mock_mode: bool = field(default=False)
    vector_search_endpoint: str | None = field(default=None)
    vector_search_index: str | None = field(default=None)
    embedding_endpoint: str = field(default="databricks-bge-large-en")
    genie_spaces_json: str | None = field(default=None)
    # Error handling and retry configuration
    default_max_retries: int = field(default=3)
    default_retry_base_delay: float = field(default=1.0)
    default_retry_max_delay: float = field(default=30.0)
    default_timeout_seconds: int = field(default=120)
    # Circuit breaker configuration
    circuit_breaker_enabled: bool = field(default=False)
    circuit_breaker_failure_threshold: int = field(default=5)
    circuit_breaker_timeout_seconds: float = field(default=60.0)
    # Cache configuration
    cache_enabled: bool = field(default=True)
    cache_ttl_seconds: int = field(default=300)  # 5 minutes default
    demo_mode: str = field(default="normal")  # "normal", "fast", "live"
    cache_max_size: int = field(default=1000)  # Maximum cache entries

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables.

        Environment variables:
            DATABRICKS_HOST: Workspace URL
            DATABRICKS_TOKEN: PAT token (for local dev)
            GENIE_SPACE_ID: Target Genie Space ID
            WAREHOUSE_ID: SQL Warehouse ID
            MODEL_ENDPOINT: Model serving endpoint name
            MOCK_MODE: Enable mock mode (true/false)
            VECTOR_SEARCH_ENDPOINT: VS endpoint (optional)
            VECTOR_SEARCH_INDEX: VS index name (optional)
            EMBEDDING_ENDPOINT: Embedding model endpoint (optional)
            DEFAULT_MAX_RETRIES: Maximum retry attempts (default: 3)
            DEFAULT_RETRY_BASE_DELAY: Base retry delay in seconds (default: 1.0)
            DEFAULT_RETRY_MAX_DELAY: Maximum retry delay in seconds (default: 30.0)
            DEFAULT_TIMEOUT_SECONDS: Default operation timeout (default: 120)
            CIRCUIT_BREAKER_ENABLED: Enable circuit breaker (default: false)
            CIRCUIT_BREAKER_FAILURE_THRESHOLD: Failures before circuit opens (default: 5)
            CIRCUIT_BREAKER_TIMEOUT_SECONDS: Circuit timeout duration (default: 60.0)
        """
        return cls(
            databricks_host=os.getenv("DATABRICKS_HOST", ""),
            databricks_token=os.getenv("DATABRICKS_TOKEN"),
            genie_space_id=os.getenv("GENIE_SPACE_ID", ""),
            warehouse_id=os.getenv("WAREHOUSE_ID", ""),
            model_endpoint=os.getenv("MODEL_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct"),
            mock_mode=_str_to_bool(os.getenv("MOCK_MODE", "false")),
            vector_search_endpoint=os.getenv("VECTOR_SEARCH_ENDPOINT"),
            vector_search_index=os.getenv("VECTOR_SEARCH_INDEX"),
            embedding_endpoint=os.getenv("EMBEDDING_ENDPOINT", "databricks-bge-large-en"),
            genie_spaces_json=os.getenv("GENIE_SPACES"),
            # Error handling configuration
            default_max_retries=int(os.getenv("DEFAULT_MAX_RETRIES", "3")),
            default_retry_base_delay=float(os.getenv("DEFAULT_RETRY_BASE_DELAY", "1.0")),
            default_retry_max_delay=float(os.getenv("DEFAULT_RETRY_MAX_DELAY", "30.0")),
            default_timeout_seconds=int(os.getenv("DEFAULT_TIMEOUT_SECONDS", "120")),
            # Circuit breaker configuration
            circuit_breaker_enabled=_str_to_bool(os.getenv("CIRCUIT_BREAKER_ENABLED", "false")),
            circuit_breaker_failure_threshold=int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")),
            circuit_breaker_timeout_seconds=float(os.getenv("CIRCUIT_BREAKER_TIMEOUT_SECONDS", "60.0")),
            # Cache configuration
            cache_enabled=_str_to_bool(os.getenv("CACHE_ENABLED", "true")),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
            demo_mode=os.getenv("DEMO_MODE", "normal"),
            cache_max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
        )

    @classmethod
    def from_databricks_secrets(
        cls,
        scope: str = "ai-data-analyst",
        host: str | None = None,
    ) -> Config:
        """Load configuration from Databricks secrets.

        Args:
            scope: The Databricks secret scope name
            host: Optional explicit host (uses dbutils context if not provided)

        Returns:
            Config instance with values from secrets
        """
        try:
            # Import dbutils for Databricks environment
            from pyspark.sql import SparkSession

            spark = SparkSession.builder.getOrCreate()
            dbutils = spark._jvm.com.databricks.dbutils_v1.DBUtilsHolder.dbutils()

            def get_secret(key: str, default: str = "") -> str:
                try:
                    return dbutils.secrets().get(scope, key)
                except Exception:
                    return default

            return cls(
                databricks_host=host or os.getenv("DATABRICKS_HOST", ""),
                databricks_token=None,  # Not needed in Databricks
                genie_space_id=get_secret("genie_space_id"),
                warehouse_id=get_secret("warehouse_id"),
                model_endpoint=get_secret("model_endpoint", "databricks-meta-llama-3-3-70b-instruct"),
                mock_mode=_str_to_bool(get_secret("mock_mode", "false")),
                vector_search_endpoint=get_secret("vector_search_endpoint") or None,
                vector_search_index=get_secret("vector_search_index") or None,
                embedding_endpoint=get_secret("embedding_endpoint", "databricks-bge-large-en"),
                # Cache configuration
                cache_enabled=_str_to_bool(get_secret("cache_enabled", "true")),
                cache_ttl_seconds=int(get_secret("cache_ttl_seconds", "300") or "300"),
                demo_mode=get_secret("demo_mode", "normal") or "normal",
                cache_max_size=int(get_secret("cache_max_size", "1000") or "1000"),
            )
        except Exception as e:
            # Fall back to environment variables
            print(f"Could not load from Databricks secrets: {e}. Falling back to env vars.")
            return cls.from_env()

    @classmethod
    def from_notebook_params(cls, params: dict) -> Config:
        """Load configuration from notebook widget parameters.

        Args:
            params: Dictionary of parameters from notebook widgets

        Returns:
            Config instance with values from parameters
        """
        return cls(
            databricks_host=params.get("databricks_host", os.getenv("DATABRICKS_HOST", "")),
            databricks_token=params.get("databricks_token"),
            genie_space_id=params.get("genie_space_id", ""),
            warehouse_id=params.get("warehouse_id", ""),
            model_endpoint=params.get("model_endpoint", "databricks-meta-llama-3-3-70b-instruct"),
            mock_mode=_str_to_bool(params.get("mock_mode", "false")),
            vector_search_endpoint=params.get("vector_search_endpoint"),
            vector_search_index=params.get("vector_search_index"),
            embedding_endpoint=params.get("embedding_endpoint", "databricks-bge-large-en"),
            # Cache configuration
            cache_enabled=_str_to_bool(params.get("cache_enabled", "true")),
            cache_ttl_seconds=int(params.get("cache_ttl_seconds", 300)),
            demo_mode=params.get("demo_mode", "normal"),
            cache_max_size=int(params.get("cache_max_size", 1000)),
        )

    def validate(self) -> list[str]:
        """Validate the configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.mock_mode:
            if not self.genie_space_id and not self.genie_spaces_json:
                errors.append("GENIE_SPACE_ID or GENIE_SPACES is required when not in mock mode")
            if not self.databricks_host:
                errors.append("DATABRICKS_HOST is required when not in mock mode")

        return errors

    def get_genie_space_configs(self) -> list:
        """Parse genie_spaces_json into GenieSpaceConfig objects.

        Returns:
            List of GenieSpaceConfig objects parsed from the JSON configuration
        """
        if not self.genie_spaces_json:
            return []

        import json

        from src.agents.multi_genie_orchestrator import GenieSpaceConfig

        try:
            spaces_data = json.loads(self.genie_spaces_json)
            return [
                GenieSpaceConfig(
                    space_id=s["space_id"],
                    name=s["name"],
                    domain=s.get("domain", ""),
                    timeout_seconds=s.get("timeout_seconds", 120),
                    retry_count=s.get("retry_count", 2),
                    retry_delay=s.get("retry_delay", 1.0),
                )
                for s in spaces_data
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to parse GENIE_SPACES: {e}")
            return []

    def validate_rag(self) -> list[str]:
        """Validate RAG-specific configuration.

        Returns:
            List of validation error messages for RAG features (empty if valid)
        """
        errors = []

        if not self.mock_mode:
            if not self.vector_search_endpoint:
                errors.append("VECTOR_SEARCH_ENDPOINT is required for RAG in non-mock mode")
            if not self.vector_search_index:
                errors.append("VECTOR_SEARCH_INDEX is required for RAG in non-mock mode")

        return errors

    def is_rag_configured(self) -> bool:
        """Check if RAG (Vector Search) is properly configured."""
        return bool(self.vector_search_endpoint and self.vector_search_index)

    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return len(self.validate()) == 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Note: databricks_token is intentionally excluded for security.
        The token must be re-set from environment after restoration.

        Returns:
            Dictionary representation of config (excluding sensitive data)
        """
        return {
            "databricks_host": self.databricks_host,
            # databricks_token intentionally excluded for security
            "genie_space_id": self.genie_space_id,
            "warehouse_id": self.warehouse_id,
            "model_endpoint": self.model_endpoint,
            "mock_mode": self.mock_mode,
            "vector_search_endpoint": self.vector_search_endpoint,
            "vector_search_index": self.vector_search_index,
            "embedding_endpoint": self.embedding_endpoint,
            "genie_spaces_json": self.genie_spaces_json,
            "default_max_retries": self.default_max_retries,
            "default_retry_base_delay": self.default_retry_base_delay,
            "default_retry_max_delay": self.default_retry_max_delay,
            "default_timeout_seconds": self.default_timeout_seconds,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "circuit_breaker_failure_threshold": self.circuit_breaker_failure_threshold,
            "circuit_breaker_timeout_seconds": self.circuit_breaker_timeout_seconds,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "demo_mode": self.demo_mode,
            "cache_max_size": self.cache_max_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        """Create Config from dictionary.

        Note: databricks_token is set to None and must be re-set from
        environment after restoration for security reasons.

        Args:
            data: Dictionary from to_dict()

        Returns:
            Config instance with restored values (token=None)
        """
        return cls(
            databricks_host=data.get("databricks_host", ""),
            databricks_token=None,  # Must be re-set from environment
            genie_space_id=data.get("genie_space_id", ""),
            warehouse_id=data.get("warehouse_id", ""),
            model_endpoint=data.get("model_endpoint", "databricks-meta-llama-3-3-70b-instruct"),
            mock_mode=data.get("mock_mode", False),
            vector_search_endpoint=data.get("vector_search_endpoint"),
            vector_search_index=data.get("vector_search_index"),
            embedding_endpoint=data.get("embedding_endpoint", "databricks-bge-large-en"),
            genie_spaces_json=data.get("genie_spaces_json"),
            default_max_retries=data.get("default_max_retries", 3),
            default_retry_base_delay=data.get("default_retry_base_delay", 1.0),
            default_retry_max_delay=data.get("default_retry_max_delay", 30.0),
            default_timeout_seconds=data.get("default_timeout_seconds", 120),
            circuit_breaker_enabled=data.get("circuit_breaker_enabled", False),
            circuit_breaker_failure_threshold=data.get("circuit_breaker_failure_threshold", 5),
            circuit_breaker_timeout_seconds=data.get("circuit_breaker_timeout_seconds", 60.0),
            cache_enabled=data.get("cache_enabled", True),
            cache_ttl_seconds=data.get("cache_ttl_seconds", 300),
            demo_mode=data.get("demo_mode", "normal"),
            cache_max_size=data.get("cache_max_size", 1000),
        )


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get the singleton configuration instance.

    Attempts to load from:
    1. Databricks secrets (if in Databricks environment)
    2. Environment variables (fallback)

    Returns:
        Config instance
    """
    # Check if we're in Databricks
    if os.getenv("DATABRICKS_RUNTIME_VERSION"):
        return Config.from_databricks_secrets()
    return Config.from_env()


def clear_config_cache() -> None:
    """Clear the configuration cache (useful for testing)."""
    get_config.cache_clear()
