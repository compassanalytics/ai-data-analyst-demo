"""Genie Testing and Evaluation Framework.

This package provides tools for evaluating Databricks Genie query performance
against test suites based on common failure scenarios.

Main components:
- models: Data models for test queries, results, and summaries
- query_generator: Test query generation based on failure categories
- evaluator: Core evaluation logic
- reporter: Report generation in multiple formats
"""

from __future__ import annotations

from src.evaluation.models import (
    AccuracyScore,
    ComparisonDetails,
    ComparisonMode,
    ComplexityLevel,
    EvaluationFailureType,
    EvaluationResult,
    EvaluationSummary,
    FailureCategory,
    QueryType,
    TestQuery,
)
from src.evaluation.query_generator import QueryGenerator
from src.evaluation.evaluator import EvaluationResults, GenieEvaluator
from src.evaluation.reporter import EvaluationReporter

__all__ = [
    # Enums
    "QueryType",
    "ComplexityLevel",
    "FailureCategory",
    "EvaluationFailureType",
    "AccuracyScore",
    "ComparisonMode",
    # Dataclasses
    "TestQuery",
    "ComparisonDetails",
    "EvaluationResult",
    "EvaluationSummary",
    "EvaluationResults",
    # Classes
    "QueryGenerator",
    "GenieEvaluator",
    "EvaluationReporter",
]
