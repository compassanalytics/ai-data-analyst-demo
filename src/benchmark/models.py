"""Data models for the LLM-Powered Benchmark System.

This module defines dataclasses for benchmark queries, runs, and comparisons
used to evaluate Genie Space performance before and after enhancements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from src.evaluation.models import (
    AccuracyScore,
    ComplexityLevel,
    EvaluationResult,
    EvaluationSummary,
    FailureCategory,
    QueryType,
    TestQuery,
)


class GenerationSource(Enum):
    """Source of benchmark query generation."""

    LLM = "llm"
    STATIC = "static"
    HYBRID = "hybrid"


class Severity(Enum):
    """Severity level for expected failures or issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BenchmarkQuery:
    """Extended test query with benchmark-specific metadata.

    Extends the base TestQuery with additional fields for benchmark tracking,
    provenance information, and expected failure scenarios.

    Attributes:
        id: Unique identifier for the benchmark query
        question: Natural language question to ask Genie
        query_type: Type of query (aggregation, filter, etc.)
        complexity: Complexity level
        failure_category: Expected failure category being tested
        expected_columns: Columns expected in the result
        expected_tables: Tables expected in the SQL
        description: Human-readable description of what this tests
        is_adversarial: Whether this is an adversarial test case
        domain: Business domain this query targets (e.g., "sales", "inventory")
        generated_by: How this query was generated
        schema_version: Version of the schema this query was generated against
        expected_failure: Expected failure message or pattern if query should fail
        correct_sql: The correct SQL for validation (if known)
        severity: Severity level of the failure scenario being tested
        model_name: Name of LLM model that generated this query (if LLM-generated)
        temperature: Temperature setting used for generation (if LLM-generated)
        prompt_hash: Hash of the prompt used for generation (for reproducibility)
        generated_at: Timestamp when the query was generated
    """

    # Base TestQuery fields
    id: str
    question: str
    query_type: QueryType
    complexity: ComplexityLevel
    failure_category: FailureCategory
    expected_columns: list[str] = field(default_factory=list)
    expected_tables: list[str] = field(default_factory=list)
    description: str = ""
    is_adversarial: bool = False

    # Benchmark-specific fields
    domain: str = ""
    generated_by: Literal["llm", "static"] = "static"
    schema_version: str = ""
    expected_failure: Optional[str] = None
    correct_sql: Optional[str] = None
    severity: Severity = Severity.MEDIUM

    # Provenance fields (for LLM-generated queries)
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    prompt_hash: Optional[str] = None
    generated_at: Optional[str] = None

    def to_test_query(self) -> TestQuery:
        """Convert to a TestQuery for evaluator compatibility.

        Returns:
            TestQuery instance with base fields only
        """
        return TestQuery(
            id=self.id,
            question=self.question,
            query_type=self.query_type,
            complexity=self.complexity,
            failure_category=self.failure_category,
            expected_columns=self.expected_columns,
            expected_tables=self.expected_tables,
            description=self.description,
            is_adversarial=self.is_adversarial,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the benchmark query
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
            "domain": self.domain,
            "generated_by": self.generated_by,
            "schema_version": self.schema_version,
            "expected_failure": self.expected_failure,
            "correct_sql": self.correct_sql,
            "severity": self.severity.value,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "prompt_hash": self.prompt_hash,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkQuery:
        """Create from dictionary.

        Args:
            data: Dictionary containing benchmark query data

        Returns:
            BenchmarkQuery instance
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
            domain=data.get("domain", ""),
            generated_by=data.get("generated_by", "static"),
            schema_version=data.get("schema_version", ""),
            expected_failure=data.get("expected_failure"),
            correct_sql=data.get("correct_sql"),
            severity=Severity(data.get("severity", "medium")),
            model_name=data.get("model_name"),
            temperature=data.get("temperature"),
            prompt_hash=data.get("prompt_hash"),
            generated_at=data.get("generated_at"),
        )


@dataclass
class BenchmarkRun:
    """Results from a single benchmark execution.

    Captures all information about a benchmark run including the evaluated
    queries, results, summary statistics, and configuration snapshot.

    Attributes:
        run_id: Unique identifier for this benchmark run
        space_id: The Genie Space ID that was evaluated
        run_type: Type of run (baseline before enhancements, or enhanced after)
        queries_evaluated: Number of queries that were evaluated
        results: List of individual evaluation results
        summary: Aggregated summary statistics
        started_at: Timestamp when the run started
        completed_at: Timestamp when the run completed
        config_snapshot: Snapshot of configuration at time of run
        provenance: Additional provenance information (model info, schema hash, etc.)
    """

    run_id: str
    space_id: str
    run_type: Literal["baseline", "enhanced"]
    queries_evaluated: int
    results: list[EvaluationResult] = field(default_factory=list)
    summary: Optional[EvaluationSummary] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the benchmark run
        """
        return {
            "run_id": self.run_id,
            "space_id": self.space_id,
            "run_type": self.run_type,
            "queries_evaluated": self.queries_evaluated,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary.to_dict() if self.summary else None,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "config_snapshot": self.config_snapshot,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkRun:
        """Create from dictionary.

        Args:
            data: Dictionary containing benchmark run data

        Returns:
            BenchmarkRun instance
        """
        return cls(
            run_id=data["run_id"],
            space_id=data["space_id"],
            run_type=data["run_type"],
            queries_evaluated=data["queries_evaluated"],
            results=[EvaluationResult.from_dict(r) for r in data.get("results", [])],
            summary=(
                EvaluationSummary.from_dict(data["summary"])
                if data.get("summary")
                else None
            ),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            config_snapshot=data.get("config_snapshot", {}),
            provenance=data.get("provenance", {}),
        )


@dataclass
class BenchmarkComparison:
    """Before/after comparison of benchmark runs.

    Compares a baseline benchmark run with an enhanced run to measure
    the impact of Genie Space improvements.

    Attributes:
        comparison_id: Unique identifier for this comparison
        baseline: The baseline benchmark run (before enhancements)
        enhanced: The enhanced benchmark run (after enhancements)
        accuracy_delta: Absolute change in accuracy (enhanced - baseline)
        accuracy_delta_percent: Percentage change in accuracy
        category_improvements: Accuracy improvements by failure category
        regressions: Query IDs that got worse in the enhanced run
        improvements: Query IDs that improved in the enhanced run
        unchanged: Query IDs with the same result in both runs
    """

    comparison_id: str
    baseline: BenchmarkRun
    enhanced: BenchmarkRun
    accuracy_delta: float = 0.0
    accuracy_delta_percent: float = 0.0
    category_improvements: dict[str, float] = field(default_factory=dict)
    regressions: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    def calculate_metrics(self) -> None:
        """Calculate all comparison metrics from baseline and enhanced runs.

        Updates accuracy_delta, accuracy_delta_percent, category_improvements,
        regressions, improvements, and unchanged fields based on the results
        in baseline and enhanced runs.
        """
        # Calculate accuracy deltas
        if self.baseline.summary and self.enhanced.summary:
            baseline_accuracy = self.baseline.summary.overall_accuracy
            enhanced_accuracy = self.enhanced.summary.overall_accuracy

            self.accuracy_delta = enhanced_accuracy - baseline_accuracy

            if baseline_accuracy > 0:
                self.accuracy_delta_percent = (
                    (enhanced_accuracy - baseline_accuracy) / baseline_accuracy
                ) * 100
            else:
                self.accuracy_delta_percent = (
                    100.0 if enhanced_accuracy > 0 else 0.0
                )

            # Calculate category improvements
            baseline_by_category = self.baseline.summary.accuracy_by_failure_category
            enhanced_by_category = self.enhanced.summary.accuracy_by_failure_category

            for category in set(baseline_by_category.keys()) | set(
                enhanced_by_category.keys()
            ):
                baseline_cat = baseline_by_category.get(category, {})
                enhanced_cat = enhanced_by_category.get(category, {})

                baseline_correct = baseline_cat.get("correct", 0)
                baseline_total = sum(baseline_cat.values()) if baseline_cat else 0
                enhanced_correct = enhanced_cat.get("correct", 0)
                enhanced_total = sum(enhanced_cat.values()) if enhanced_cat else 0

                baseline_rate = (
                    (baseline_correct / baseline_total * 100) if baseline_total > 0 else 0.0
                )
                enhanced_rate = (
                    (enhanced_correct / enhanced_total * 100) if enhanced_total > 0 else 0.0
                )

                self.category_improvements[category] = enhanced_rate - baseline_rate

        # Build query result maps for comparison
        baseline_results: dict[str, AccuracyScore] = {}
        enhanced_results: dict[str, AccuracyScore] = {}

        for result in self.baseline.results:
            baseline_results[result.test_query.id] = result.accuracy

        for result in self.enhanced.results:
            enhanced_results[result.test_query.id] = result.accuracy

        # Compare individual query results
        self.regressions = []
        self.improvements = []
        self.unchanged = []

        # Define accuracy ordering for comparison (higher is better)
        accuracy_order = {
            AccuracyScore.CORRECT: 3,
            AccuracyScore.PARTIAL: 2,
            AccuracyScore.WRONG: 1,
            AccuracyScore.FAILED: 0,
        }

        all_query_ids = set(baseline_results.keys()) | set(enhanced_results.keys())

        for query_id in all_query_ids:
            baseline_acc = baseline_results.get(query_id)
            enhanced_acc = enhanced_results.get(query_id)

            if baseline_acc is None or enhanced_acc is None:
                # Query only exists in one run - treat as unchanged
                self.unchanged.append(query_id)
                continue

            baseline_score = accuracy_order[baseline_acc]
            enhanced_score = accuracy_order[enhanced_acc]

            if enhanced_score > baseline_score:
                self.improvements.append(query_id)
            elif enhanced_score < baseline_score:
                self.regressions.append(query_id)
            else:
                self.unchanged.append(query_id)

    def has_regressions(self) -> bool:
        """Check if there are any regressions in the enhanced run.

        Returns:
            True if any queries performed worse in the enhanced run
        """
        return len(self.regressions) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the benchmark comparison
        """
        return {
            "comparison_id": self.comparison_id,
            "baseline": self.baseline.to_dict(),
            "enhanced": self.enhanced.to_dict(),
            "accuracy_delta": self.accuracy_delta,
            "accuracy_delta_percent": self.accuracy_delta_percent,
            "category_improvements": self.category_improvements,
            "regressions": self.regressions,
            "improvements": self.improvements,
            "unchanged": self.unchanged,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkComparison:
        """Create from dictionary.

        Args:
            data: Dictionary containing benchmark comparison data

        Returns:
            BenchmarkComparison instance
        """
        return cls(
            comparison_id=data["comparison_id"],
            baseline=BenchmarkRun.from_dict(data["baseline"]),
            enhanced=BenchmarkRun.from_dict(data["enhanced"]),
            accuracy_delta=data.get("accuracy_delta", 0.0),
            accuracy_delta_percent=data.get("accuracy_delta_percent", 0.0),
            category_improvements=data.get("category_improvements", {}),
            regressions=data.get("regressions", []),
            improvements=data.get("improvements", []),
            unchanged=data.get("unchanged", []),
        )
