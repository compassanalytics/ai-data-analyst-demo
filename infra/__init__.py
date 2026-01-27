"""Infrastructure-as-Code module for Databricks Genie Space management.

This module provides tools for managing Genie Spaces via the Databricks REST API,
enabling infrastructure-as-code workflows for AI/BI configuration.
"""

from infra.genie_space_manager import (
    GenieSpaceConfig,
    GenieSpaceManager,
    JoinSpec,
    SampleQuestion,
    TableSource,
    ExampleSQL,
)

__all__ = [
    "GenieSpaceConfig",
    "GenieSpaceManager",
    "JoinSpec",
    "SampleQuestion",
    "TableSource",
    "ExampleSQL",
]
