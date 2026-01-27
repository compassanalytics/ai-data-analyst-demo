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
from typing import Optional

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
    """

    databricks_host: str = field(default="")
    databricks_token: Optional[str] = field(default=None, repr=False)
    genie_space_id: str = field(default="")
    warehouse_id: str = field(default="")
    model_endpoint: str = field(default="databricks-meta-llama-3-3-70b-instruct")
    mock_mode: bool = field(default=False)
    vector_search_endpoint: Optional[str] = field(default=None)
    vector_search_index: Optional[str] = field(default=None)

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
        )

    @classmethod
    def from_databricks_secrets(
        cls,
        scope: str = "ai-data-analyst",
        host: Optional[str] = None,
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
        )

    def validate(self) -> list[str]:
        """Validate the configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.mock_mode:
            if not self.genie_space_id:
                errors.append("GENIE_SPACE_ID is required when not in mock mode")
            if not self.databricks_host:
                errors.append("DATABRICKS_HOST is required when not in mock mode")

        return errors

    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return len(self.validate()) == 0


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
