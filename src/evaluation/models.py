"""Data models for the Genie Testing and Evaluation Framework.

This module defines all enums and dataclasses used for evaluating Genie query
performance, including test queries, evaluation results, and summary statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class QueryType(Enum):
    """Types of queries for categorization."""

    AGGREGATION = "aggregation"
    FILTER = "filter"
    JOIN = "join"
    TEMPORAL = "temporal"
    RANKING = "ranking"
    COMPARISON = "comparison"


class ComplexityLevel(Enum):
    """Complexity levels for test queries."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class FailureCategory(Enum):
    """Categories of potential Genie failures.

    Based on failure scenarios from genie_failure_scenarios.py:
    1. Ambiguous column names
    2. Cryptic codes/abbreviations
    3. Undocumented business logic
    4. Temporal confusion
    5. Aggregation ambiguity
    6. Join complexity
    """

    AMBIGUOUS_COLUMNS = "ambiguous_columns"
    CRYPTIC_CODES = "cryptic_codes"
    BUSINESS_LOGIC = "business_logic"
    TEMPORAL_CONFUSION = "temporal_confusion"
    AGGREGATION_AMBIGUITY = "aggregation_ambiguity"
    JOIN_COMPLEXITY = "join_complexity"


class EvaluationFailureType(Enum):
    """Types of evaluation failures."""

    NONE = "none"  # No failure - query succeeded
    WRONG_COLUMNS = "wrong_columns"
    WRONG_TABLES = "wrong_tables"
    WRONG_AGGREGATION = "wrong_aggregation"
    WRONG_FILTER = "wrong_filter"
    WRONG_JOIN = "wrong_join"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    NO_SQL_GENERATED = "no_sql_generated"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


class AccuracyScore(Enum):
    """Accuracy classification for evaluation results."""

    CORRECT = "correct"
    PARTIAL = "partial"
    WRONG = "wrong"
    FAILED = "failed"  # Query didn't execute


class ComparisonMode(Enum):
    """Modes for comparing query results."""

    SQL_ONLY = "sql_only"  # Compare SQL structure only
    TEXT_SEMANTIC = "text_semantic"  # Semantic comparison of text outputs
    COLUMN_PRESENCE = "column_presence"  # Check if expected columns are present


@dataclass
class TestQuery:
    """A test query for evaluation.

    Attributes:
        id: Unique identifier for the test query
        question: Natural language question to ask Genie
        query_type: Type of query (aggregation, filter, etc.)
        complexity: Complexity level
        failure_category: Expected failure category being tested
        expected_columns: Columns expected in the result
        expected_tables: Tables expected in the SQL
        description: Human-readable description of what this tests
        is_adversarial: Whether this is an adversarial test case
    """

    id: str
    question: str
    query_type: QueryType
    complexity: ComplexityLevel
    failure_category: FailureCategory
    expected_columns: list[str] = field(default_factory=list)
    expected_tables: list[str] = field(default_factory=list)
    description: str = ""
    is_adversarial: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the test query
        """
        return {
            "id": self.id,
            "question": self.question,
            "query_type": self.query_type.value,
            "complexity": self.complexity.value,
            "failure_category": self.failure_category.value,
            "expected_columns": self.expected_columns,
            "expected_tables": self.expected_tables,
            "description": self.description,
            "is_adversarial": self.is_adversarial,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestQuery:
        """Create from dictionary.

        Args:
            data: Dictionary containing test query data

        Returns:
            TestQuery instance
        """
        return cls(
            id=data["id"],
            question=data["question"],
            query_type=QueryType(data["query_type"]),
            complexity=ComplexityLevel(data["complexity"]),
            failure_category=FailureCategory(data["failure_category"]),
            expected_columns=data.get("expected_columns", []),
            expected_tables=data.get("expected_tables", []),
            description=data.get("description", ""),
            is_adversarial=data.get("is_adversarial", False),
        )


@dataclass
class ComparisonDetails:
    """Details of the comparison between expected and actual results.

    Attributes:
        expected_columns: Columns that were expected
        actual_columns: Columns that were found
        missing_columns: Expected columns not found
        extra_columns: Found columns not expected
        expected_tables: Tables that were expected
        actual_tables: Tables that were found
        missing_tables: Expected tables not found
        extra_tables: Found tables not expected
        sql_generated: The SQL that Genie generated
        comparison_notes: Additional notes about the comparison
    """

    expected_columns: list[str] = field(default_factory=list)
    actual_columns: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    expected_tables: list[str] = field(default_factory=list)
    actual_tables: list[str] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)
    extra_tables: list[str] = field(default_factory=list)
    sql_generated: str | None = None
    comparison_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of comparison details
        """
        return {
            "expected_columns": self.expected_columns,
            "actual_columns": self.actual_columns,
            "missing_columns": self.missing_columns,
            "extra_columns": self.extra_columns,
            "expected_tables": self.expected_tables,
            "actual_tables": self.actual_tables,
            "missing_tables": self.missing_tables,
            "extra_tables": self.extra_tables,
            "sql_generated": self.sql_generated,
            "comparison_notes": self.comparison_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComparisonDetails:
        """Create from dictionary.

        Args:
            data: Dictionary containing comparison details data

        Returns:
            ComparisonDetails instance
        """
        return cls(
            expected_columns=data.get("expected_columns", []),
            actual_columns=data.get("actual_columns", []),
            missing_columns=data.get("missing_columns", []),
            extra_columns=data.get("extra_columns", []),
            expected_tables=data.get("expected_tables", []),
            actual_tables=data.get("actual_tables", []),
            missing_tables=data.get("missing_tables", []),
            extra_tables=data.get("extra_tables", []),
            sql_generated=data.get("sql_generated"),
            comparison_notes=data.get("comparison_notes", ""),
        )


@dataclass
class EvaluationResult:
    """Result of evaluating a single test query.

    Attributes:
        test_query: The test query that was evaluated
        accuracy: The accuracy score
        failure_type: Type of failure if any
        comparison: Detailed comparison information
        execution_time_ms: Time taken to execute the query in milliseconds
        genie_response_raw: Raw response from Genie (for debugging)
        error_message: Error message if query failed
        error_category: Error category from AgentError if available
        timestamp: When the evaluation was performed
    """

    test_query: TestQuery
    accuracy: AccuracyScore
    failure_type: EvaluationFailureType
    comparison: ComparisonDetails
    execution_time_ms: float = 0.0
    genie_response_raw: dict[str, Any] | None = None
    error_message: str | None = None
    error_category: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_correct(self) -> bool:
        """Check if the result is correct.

        Returns:
            True if accuracy is CORRECT
        """
        return self.accuracy == AccuracyScore.CORRECT

    @property
    def is_partial(self) -> bool:
        """Check if the result is partially correct.

        Returns:
            True if accuracy is PARTIAL
        """
        return self.accuracy == AccuracyScore.PARTIAL

    @property
    def is_wrong(self) -> bool:
        """Check if the result is wrong.

        Returns:
            True if accuracy is WRONG
        """
        return self.accuracy == AccuracyScore.WRONG

    @property
    def is_failed(self) -> bool:
        """Check if the query failed to execute.

        Returns:
            True if accuracy is FAILED
        """
        return self.accuracy == AccuracyScore.FAILED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of evaluation result
        """
        return {
            "test_query": self.test_query.to_dict(),
            "accuracy": self.accuracy.value,
            "failure_type": self.failure_type.value,
            "comparison": self.comparison.to_dict(),
            "execution_time_ms": self.execution_time_ms,
            "genie_response_raw": self.genie_response_raw,
            "error_message": self.error_message,
            "error_category": self.error_category,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationResult:
        """Create from dictionary.

        Args:
            data: Dictionary containing evaluation result data

        Returns:
            EvaluationResult instance
        """
        return cls(
            test_query=TestQuery.from_dict(data["test_query"]),
            accuracy=AccuracyScore(data["accuracy"]),
            failure_type=EvaluationFailureType(data["failure_type"]),
            comparison=ComparisonDetails.from_dict(data["comparison"]),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            genie_response_raw=data.get("genie_response_raw"),
            error_message=data.get("error_message"),
            error_category=data.get("error_category"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class EvaluationSummary:
    """Summary statistics for an evaluation run.

    Attributes:
        total_queries: Total number of queries evaluated
        correct_count: Number of correct results
        partial_count: Number of partially correct results
        wrong_count: Number of wrong results
        failed_count: Number of failed queries
        accuracy_by_query_type: Accuracy breakdown by query type
        accuracy_by_complexity: Accuracy breakdown by complexity level
        accuracy_by_failure_category: Accuracy breakdown by failure category
        failure_type_counts: Count of each failure type
        total_execution_time_ms: Total execution time in milliseconds
        average_execution_time_ms: Average execution time per query
        started_at: When the evaluation started
        completed_at: When the evaluation completed
        space_id: The Genie Space ID that was evaluated
    """

    total_queries: int = 0
    correct_count: int = 0
    partial_count: int = 0
    wrong_count: int = 0
    failed_count: int = 0
    accuracy_by_query_type: dict[str, dict[str, int]] = field(default_factory=dict)
    accuracy_by_complexity: dict[str, dict[str, int]] = field(default_factory=dict)
    accuracy_by_failure_category: dict[str, dict[str, int]] = field(default_factory=dict)
    failure_type_counts: dict[str, int] = field(default_factory=dict)
    total_execution_time_ms: float = 0.0
    average_execution_time_ms: float = 0.0
    started_at: str = ""
    completed_at: str = ""
    space_id: str = ""

    @property
    def overall_accuracy(self) -> float:
        """Calculate overall accuracy percentage.

        Returns:
            Accuracy percentage (0-100), or 0 if no queries
        """
        if self.total_queries == 0:
            return 0.0
        return (self.correct_count / self.total_queries) * 100

    @property
    def overall_accuracy_with_partial(self) -> float:
        """Calculate accuracy including partial as half-correct.

        Returns:
            Accuracy percentage (0-100) with partial counting as 0.5
        """
        if self.total_queries == 0:
            return 0.0
        score = self.correct_count + (self.partial_count * 0.5)
        return (score / self.total_queries) * 100

    @property
    def success_rate(self) -> float:
        """Calculate the rate of queries that didn't fail.

        Returns:
            Success rate percentage (0-100)
        """
        if self.total_queries == 0:
            return 0.0
        return ((self.total_queries - self.failed_count) / self.total_queries) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of evaluation summary
        """
        return {
            "total_queries": self.total_queries,
            "correct_count": self.correct_count,
            "partial_count": self.partial_count,
            "wrong_count": self.wrong_count,
            "failed_count": self.failed_count,
            "overall_accuracy": self.overall_accuracy,
            "overall_accuracy_with_partial": self.overall_accuracy_with_partial,
            "success_rate": self.success_rate,
            "accuracy_by_query_type": self.accuracy_by_query_type,
            "accuracy_by_complexity": self.accuracy_by_complexity,
            "accuracy_by_failure_category": self.accuracy_by_failure_category,
            "failure_type_counts": self.failure_type_counts,
            "total_execution_time_ms": self.total_execution_time_ms,
            "average_execution_time_ms": self.average_execution_time_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "space_id": self.space_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationSummary:
        """Create from dictionary.

        Args:
            data: Dictionary containing evaluation summary data

        Returns:
            EvaluationSummary instance
        """
        return cls(
            total_queries=data.get("total_queries", 0),
            correct_count=data.get("correct_count", 0),
            partial_count=data.get("partial_count", 0),
            wrong_count=data.get("wrong_count", 0),
            failed_count=data.get("failed_count", 0),
            accuracy_by_query_type=data.get("accuracy_by_query_type", {}),
            accuracy_by_complexity=data.get("accuracy_by_complexity", {}),
            accuracy_by_failure_category=data.get("accuracy_by_failure_category", {}),
            failure_type_counts=data.get("failure_type_counts", {}),
            total_execution_time_ms=data.get("total_execution_time_ms", 0.0),
            average_execution_time_ms=data.get("average_execution_time_ms", 0.0),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            space_id=data.get("space_id", ""),
        )
