"""Tests for the evaluation framework.

This module provides comprehensive unit tests for the Genie Testing and
Evaluation Framework, including models, query generator, evaluator, and reporter.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pytest

from src.evaluation import (
    AccuracyScore,
    ComparisonDetails,
    ComplexityLevel,
    EvaluationFailureType,
    EvaluationReporter,
    EvaluationResult,
    EvaluationSummary,
    FailureCategory,
    GenieEvaluator,
    QueryGenerator,
    QueryType,
    TestQuery,
)
from src.evaluation.evaluator import EvaluationResults
from src.config import Config
from src.utils.errors import AgentError, ErrorCategory


# =============================================================================
# Mock Classes
# =============================================================================


@dataclass
class MockGenieResult:
    """Mock GenieResult for testing."""

    success: bool = True
    data: list[dict[str, Any]] = field(default_factory=list)
    sql: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    columns: list[str] = field(default_factory=list)
    error_details: Optional[AgentError] = None
    from_cache: bool = False


# =============================================================================
# Test Models
# =============================================================================


class TestQueryTypeEnum:
    """Tests for QueryType enum."""

    def test_all_values(self) -> None:
        """Test all query type values are defined."""
        expected = ["aggregation", "filter", "join", "temporal", "ranking", "comparison"]
        actual = [qt.value for qt in QueryType]
        assert set(actual) == set(expected)


class TestComplexityLevelEnum:
    """Tests for ComplexityLevel enum."""

    def test_all_values(self) -> None:
        """Test all complexity levels are defined."""
        expected = ["simple", "moderate", "complex"]
        actual = [cl.value for cl in ComplexityLevel]
        assert set(actual) == set(expected)


class TestFailureCategoryEnum:
    """Tests for FailureCategory enum."""

    def test_all_values(self) -> None:
        """Test all failure categories are defined."""
        expected = [
            "ambiguous_columns",
            "cryptic_codes",
            "business_logic",
            "temporal_confusion",
            "aggregation_ambiguity",
            "join_complexity",
        ]
        actual = [fc.value for fc in FailureCategory]
        assert set(actual) == set(expected)


class TestTestQuery:
    """Tests for TestQuery dataclass."""

    def test_create_test_query(self) -> None:
        """Test creating a TestQuery."""
        query = TestQuery(
            id="test_001",
            question="What is total revenue?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            expected_columns=["revenue", "total"],
            expected_tables=["sales"],
            description="Test revenue aggregation",
            is_adversarial=False,
        )

        assert query.id == "test_001"
        assert query.question == "What is total revenue?"
        assert query.query_type == QueryType.AGGREGATION
        assert query.complexity == ComplexityLevel.SIMPLE
        assert query.failure_category == FailureCategory.AMBIGUOUS_COLUMNS
        assert query.expected_columns == ["revenue", "total"]
        assert query.expected_tables == ["sales"]
        assert query.description == "Test revenue aggregation"
        assert query.is_adversarial is False

    def test_to_dict(self) -> None:
        """Test TestQuery serialization to dict."""
        query = TestQuery(
            id="test_001",
            question="What is total revenue?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
        )

        data = query.to_dict()

        assert data["id"] == "test_001"
        assert data["question"] == "What is total revenue?"
        assert data["query_type"] == "aggregation"
        assert data["complexity"] == "simple"
        assert data["failure_category"] == "ambiguous_columns"

    def test_from_dict(self) -> None:
        """Test TestQuery deserialization from dict."""
        data = {
            "id": "test_002",
            "question": "Show sales by region",
            "query_type": "aggregation",
            "complexity": "moderate",
            "failure_category": "cryptic_codes",
            "expected_columns": ["region", "sales"],
            "expected_tables": ["sales"],
        }

        query = TestQuery.from_dict(data)

        assert query.id == "test_002"
        assert query.query_type == QueryType.AGGREGATION
        assert query.complexity == ComplexityLevel.MODERATE
        assert query.failure_category == FailureCategory.CRYPTIC_CODES

    def test_roundtrip_serialization(self) -> None:
        """Test TestQuery serialization roundtrip."""
        original = TestQuery(
            id="test_003",
            question="Test question",
            query_type=QueryType.JOIN,
            complexity=ComplexityLevel.COMPLEX,
            failure_category=FailureCategory.JOIN_COMPLEXITY,
            expected_columns=["a", "b"],
            expected_tables=["t1", "t2"],
            description="Test",
            is_adversarial=True,
        )

        data = original.to_dict()
        restored = TestQuery.from_dict(data)

        assert restored.id == original.id
        assert restored.question == original.question
        assert restored.query_type == original.query_type
        assert restored.complexity == original.complexity
        assert restored.failure_category == original.failure_category
        assert restored.expected_columns == original.expected_columns
        assert restored.expected_tables == original.expected_tables
        assert restored.is_adversarial == original.is_adversarial


class TestComparisonDetails:
    """Tests for ComparisonDetails dataclass."""

    def test_default_values(self) -> None:
        """Test default values for ComparisonDetails."""
        details = ComparisonDetails()

        assert details.expected_columns == []
        assert details.actual_columns == []
        assert details.missing_columns == []
        assert details.extra_columns == []
        assert details.sql_generated is None
        assert details.comparison_notes == ""

    def test_to_dict(self) -> None:
        """Test ComparisonDetails serialization."""
        details = ComparisonDetails(
            expected_columns=["a", "b"],
            actual_columns=["a", "c"],
            missing_columns=["b"],
            extra_columns=["c"],
            sql_generated="SELECT a, c FROM table",
        )

        data = details.to_dict()

        assert data["expected_columns"] == ["a", "b"]
        assert data["actual_columns"] == ["a", "c"]
        assert data["missing_columns"] == ["b"]
        assert data["sql_generated"] == "SELECT a, c FROM table"


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.test_query = TestQuery(
            id="test_001",
            question="What is total revenue?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
        )

    def test_is_correct_property(self) -> None:
        """Test is_correct property."""
        result = EvaluationResult(
            test_query=self.test_query,
            accuracy=AccuracyScore.CORRECT,
            failure_type=EvaluationFailureType.NONE,
            comparison=ComparisonDetails(),
        )

        assert result.is_correct is True
        assert result.is_partial is False
        assert result.is_wrong is False
        assert result.is_failed is False

    def test_is_partial_property(self) -> None:
        """Test is_partial property."""
        result = EvaluationResult(
            test_query=self.test_query,
            accuracy=AccuracyScore.PARTIAL,
            failure_type=EvaluationFailureType.WRONG_COLUMNS,
            comparison=ComparisonDetails(),
        )

        assert result.is_correct is False
        assert result.is_partial is True
        assert result.is_wrong is False
        assert result.is_failed is False

    def test_is_failed_property(self) -> None:
        """Test is_failed property."""
        result = EvaluationResult(
            test_query=self.test_query,
            accuracy=AccuracyScore.FAILED,
            failure_type=EvaluationFailureType.TIMEOUT,
            comparison=ComparisonDetails(),
            error_message="Timeout error",
        )

        assert result.is_correct is False
        assert result.is_partial is False
        assert result.is_wrong is False
        assert result.is_failed is True

    def test_serialization_roundtrip(self) -> None:
        """Test EvaluationResult serialization roundtrip."""
        original = EvaluationResult(
            test_query=self.test_query,
            accuracy=AccuracyScore.PARTIAL,
            failure_type=EvaluationFailureType.WRONG_COLUMNS,
            comparison=ComparisonDetails(missing_columns=["x"]),
            execution_time_ms=150.5,
            error_message=None,
        )

        data = original.to_dict()
        restored = EvaluationResult.from_dict(data)

        assert restored.accuracy == original.accuracy
        assert restored.failure_type == original.failure_type
        assert restored.execution_time_ms == original.execution_time_ms
        assert restored.comparison.missing_columns == ["x"]


class TestEvaluationSummary:
    """Tests for EvaluationSummary dataclass."""

    def test_overall_accuracy_zero_queries(self) -> None:
        """Test overall accuracy with no queries."""
        summary = EvaluationSummary(total_queries=0)
        assert summary.overall_accuracy == 0.0

    def test_overall_accuracy_calculation(self) -> None:
        """Test overall accuracy calculation."""
        summary = EvaluationSummary(
            total_queries=10,
            correct_count=7,
            partial_count=2,
            wrong_count=1,
            failed_count=0,
        )

        assert summary.overall_accuracy == 70.0

    def test_overall_accuracy_with_partial(self) -> None:
        """Test accuracy calculation with partial counting as 0.5."""
        summary = EvaluationSummary(
            total_queries=10,
            correct_count=6,
            partial_count=2,
            wrong_count=2,
            failed_count=0,
        )

        # 6 + (2 * 0.5) = 7 out of 10 = 70%
        assert summary.overall_accuracy_with_partial == 70.0

    def test_success_rate(self) -> None:
        """Test success rate calculation."""
        summary = EvaluationSummary(
            total_queries=10,
            correct_count=5,
            partial_count=2,
            wrong_count=1,
            failed_count=2,
        )

        # 8 out of 10 didn't fail = 80%
        assert summary.success_rate == 80.0


# =============================================================================
# Test Query Generator
# =============================================================================


class TestQueryGenerator:
    """Tests for QueryGenerator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = QueryGenerator()

    def test_generate_all_queries(self) -> None:
        """Test generating all queries."""
        queries = self.generator.get_all_queries()

        # Should have at least 30 queries (5+ per category * 6 categories)
        assert len(queries) >= 30

        # All queries should be TestQuery instances
        for query in queries:
            assert isinstance(query, TestQuery)

    def test_generate_by_query_type(self) -> None:
        """Test filtering by query type."""
        queries = self.generator.generate_suite(query_types=[QueryType.AGGREGATION])

        assert len(queries) > 0
        for query in queries:
            assert query.query_type == QueryType.AGGREGATION

    def test_generate_by_complexity(self) -> None:
        """Test filtering by complexity."""
        queries = self.generator.generate_suite(complexity_levels=[ComplexityLevel.SIMPLE])

        assert len(queries) > 0
        for query in queries:
            assert query.complexity == ComplexityLevel.SIMPLE

    def test_generate_by_failure_category(self) -> None:
        """Test filtering by failure category."""
        queries = self.generator.generate_suite(
            failure_categories=[FailureCategory.AMBIGUOUS_COLUMNS]
        )

        assert len(queries) >= 5  # Should have at least 5 queries per category
        for query in queries:
            assert query.failure_category == FailureCategory.AMBIGUOUS_COLUMNS

    def test_generate_with_multiple_filters(self) -> None:
        """Test filtering with multiple criteria."""
        queries = self.generator.generate_suite(
            query_types=[QueryType.AGGREGATION, QueryType.FILTER],
            complexity_levels=[ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE],
        )

        for query in queries:
            assert query.query_type in [QueryType.AGGREGATION, QueryType.FILTER]
            assert query.complexity in [ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE]

    def test_generate_adversarial(self) -> None:
        """Test generating adversarial queries."""
        queries = self.generator.generate_suite(adversarial=True)

        assert len(queries) > 0
        for query in queries:
            assert query.is_adversarial is True

    def test_get_queries_by_category(self) -> None:
        """Test getting queries by specific category."""
        queries = self.generator.get_queries_by_category(FailureCategory.CRYPTIC_CODES)

        assert len(queries) >= 5
        for query in queries:
            assert query.failure_category == FailureCategory.CRYPTIC_CODES

    def test_get_queries_by_type(self) -> None:
        """Test getting queries by specific type."""
        queries = self.generator.get_queries_by_type(QueryType.JOIN)

        assert len(queries) > 0
        for query in queries:
            assert query.query_type == QueryType.JOIN

    def test_get_summary(self) -> None:
        """Test getting query summary."""
        summary = self.generator.get_summary()

        assert "total" in summary
        assert "by_category" in summary
        assert "by_type" in summary
        assert "by_complexity" in summary

        assert summary["total"] > 0
        assert len(summary["by_category"]) == 6  # 6 failure categories

    def test_unique_query_ids(self) -> None:
        """Test that all query IDs are unique."""
        queries = self.generator.get_all_queries()
        ids = [q.id for q in queries]

        assert len(ids) == len(set(ids)), "Query IDs are not unique"


# =============================================================================
# Test Evaluator
# =============================================================================


class TestGenieEvaluator:
    """Tests for GenieEvaluator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = Config(genie_space_id="test_space", mock_mode=True)
        self.evaluator = GenieEvaluator(self.config)

    def test_evaluate_single_mock_mode(self) -> None:
        """Test evaluating a single query in mock mode."""
        test_query = TestQuery(
            id="test_001",
            question="What are total sales by region?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            expected_columns=["region", "sales"],
            expected_tables=["sales"],
        )

        result = self.evaluator.evaluate_single(test_query)

        assert isinstance(result, EvaluationResult)
        assert result.test_query.id == "test_001"
        assert result.execution_time_ms >= 0
        assert result.accuracy in list(AccuracyScore)

    def test_evaluate_multiple_queries(self) -> None:
        """Test evaluating multiple queries."""
        generator = QueryGenerator()
        test_queries = generator.generate_suite(
            failure_categories=[FailureCategory.AMBIGUOUS_COLUMNS],
        )[:3]  # Limit to 3 for speed

        results = self.evaluator.evaluate(test_queries)

        assert isinstance(results, EvaluationResults)
        assert len(results.results) == 3
        assert results.summary is not None
        assert results.summary.total_queries == 3

    def test_extract_columns_from_sql(self) -> None:
        """Test SQL column extraction."""
        sql = """
        SELECT
            product_name,
            SUM(revenue) as total_revenue,
            COUNT(*) as count
        FROM sales
        GROUP BY product_name
        """

        columns = self.evaluator._extract_columns_from_sql(sql)

        assert "product_name" in columns
        assert "revenue" in columns
        assert "total_revenue" in columns
        # count might or might not be extracted depending on implementation

    def test_extract_columns_from_sql_with_alias(self) -> None:
        """Test SQL column extraction with table aliases."""
        sql = """
        SELECT
            s.product_name,
            p.category
        FROM sales s
        JOIN products p ON s.product_id = p.id
        """

        columns = self.evaluator._extract_columns_from_sql(sql)

        assert "product_name" in columns
        assert "category" in columns

    def test_extract_tables_from_sql(self) -> None:
        """Test SQL table extraction."""
        sql = """
        SELECT *
        FROM sales
        JOIN products ON sales.product_id = products.id
        LEFT JOIN customers ON sales.customer_id = customers.id
        """

        tables = self.evaluator._extract_tables_from_sql(sql)

        assert "sales" in tables
        assert "products" in tables
        assert "customers" in tables

    def test_extract_tables_from_sql_with_schema(self) -> None:
        """Test SQL table extraction with schema prefix."""
        sql = """
        SELECT *
        FROM analytics.sales s
        JOIN analytics.products p ON s.product_id = p.id
        """

        tables = self.evaluator._extract_tables_from_sql(sql)

        # Should extract just the table name, not the schema
        assert "sales" in tables
        assert "products" in tables

    def test_classify_failure_ambiguous_columns(self) -> None:
        """Test failure classification for ambiguous columns."""
        test_query = TestQuery(
            id="test",
            question="Test",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            expected_columns=["revenue"],
        )

        comparison = ComparisonDetails(
            expected_columns=["revenue"],
            actual_columns=["sales"],
            missing_columns=["revenue"],
        )

        failure_type = self.evaluator._classify_failure(test_query, comparison)

        assert failure_type == EvaluationFailureType.WRONG_COLUMNS

    def test_classify_failure_join_complexity(self) -> None:
        """Test failure classification for join complexity."""
        test_query = TestQuery(
            id="test",
            question="Test",
            query_type=QueryType.JOIN,
            complexity=ComplexityLevel.COMPLEX,
            failure_category=FailureCategory.JOIN_COMPLEXITY,
            expected_tables=["products", "sales"],
        )

        comparison = ComparisonDetails(
            expected_tables=["products", "sales"],
            actual_tables=["sales"],
            missing_tables=["products"],
        )

        failure_type = self.evaluator._classify_failure(test_query, comparison)

        assert failure_type == EvaluationFailureType.WRONG_JOIN

    def test_build_summary(self) -> None:
        """Test building summary from results."""
        test_query = TestQuery(
            id="test",
            question="Test",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
        )

        results = [
            EvaluationResult(
                test_query=test_query,
                accuracy=AccuracyScore.CORRECT,
                failure_type=EvaluationFailureType.NONE,
                comparison=ComparisonDetails(),
                execution_time_ms=100,
            ),
            EvaluationResult(
                test_query=test_query,
                accuracy=AccuracyScore.WRONG,
                failure_type=EvaluationFailureType.WRONG_COLUMNS,
                comparison=ComparisonDetails(),
                execution_time_ms=150,
            ),
        ]

        summary = self.evaluator._build_summary(results)

        assert summary.total_queries == 2
        assert summary.correct_count == 1
        assert summary.wrong_count == 1
        assert summary.total_execution_time_ms == 250
        assert summary.average_execution_time_ms == 125

    def test_handle_sql_none(self) -> None:
        """Test handling when SQL is None in result."""
        test_query = TestQuery(
            id="test",
            question="Test",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            expected_columns=["revenue"],
            expected_tables=["sales"],
        )

        # Create a mock result with sql=None
        mock_result = MockGenieResult(
            success=True,
            sql=None,
            data=[{"answer": "Some text response"}],
        )

        # Test the comparison logic
        accuracy, failure_type, comparison = self.evaluator._compare_results(
            test_query, mock_result
        )

        assert accuracy == AccuracyScore.FAILED
        assert failure_type == EvaluationFailureType.NO_SQL_GENERATED

    def test_results_serialization(self) -> None:
        """Test EvaluationResults serialization roundtrip."""
        generator = QueryGenerator()
        test_queries = generator.generate_suite(
            failure_categories=[FailureCategory.AMBIGUOUS_COLUMNS],
        )[:2]

        results = self.evaluator.evaluate(test_queries)

        # Serialize
        data = results.to_dict()

        # Deserialize
        restored = EvaluationResults.from_dict(data)

        assert len(restored.results) == len(results.results)
        assert restored.summary is not None
        assert restored.summary.total_queries == results.summary.total_queries


# =============================================================================
# Test Reporter
# =============================================================================


class TestEvaluationReporter:
    """Tests for EvaluationReporter class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.reporter = EvaluationReporter()

        # Create sample results
        test_query = TestQuery(
            id="test_001",
            question="What is total revenue?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            expected_columns=["revenue"],
            expected_tables=["sales"],
        )

        result = EvaluationResult(
            test_query=test_query,
            accuracy=AccuracyScore.CORRECT,
            failure_type=EvaluationFailureType.NONE,
            comparison=ComparisonDetails(
                sql_generated="SELECT SUM(revenue) FROM sales",
            ),
            execution_time_ms=100,
        )

        summary = EvaluationSummary(
            total_queries=1,
            correct_count=1,
            partial_count=0,
            wrong_count=0,
            failed_count=0,
            accuracy_by_query_type={"aggregation": {"correct": 1, "total": 1}},
            accuracy_by_complexity={"simple": {"correct": 1, "total": 1}},
            accuracy_by_failure_category={"ambiguous_columns": {"correct": 1, "total": 1}},
            total_execution_time_ms=100,
            average_execution_time_ms=100,
        )

        self.results = EvaluationResults(results=[result], summary=summary)

    def test_format_percent_filter(self) -> None:
        """Test format_percent filter."""
        assert self.reporter._format_percent(75.5) == "75.5%"
        assert self.reporter._format_percent(100) == "100.0%"
        assert self.reporter._format_percent(0) == "0.0%"

    def test_format_number_filter(self) -> None:
        """Test format_number filter."""
        assert self.reporter._format_number(1000) == "1,000"
        assert self.reporter._format_number(1234567) == "1,234,567"
        assert self.reporter._format_number(100.5, decimals=2) == "100.50"

    def test_format_duration_filter(self) -> None:
        """Test format_duration filter."""
        assert self.reporter._format_duration(500) == "500ms"
        assert self.reporter._format_duration(1500) == "1.50s"
        assert self.reporter._format_duration(2500) == "2.50s"

    def test_generate_markdown(self) -> None:
        """Test markdown report generation."""
        markdown = self.reporter.generate_markdown(self.results, title="Test Report")

        assert "# Test Report" in markdown
        assert "Total Queries" in markdown
        assert "Correct" in markdown
        assert "1" in markdown  # correct count

    def test_generate_html(self) -> None:
        """Test HTML report generation."""
        html = self.reporter.generate_html(self.results, title="Test Dashboard")

        assert "<html" in html
        assert "Test Dashboard" in html
        assert "Total Queries" in html
        assert "tailwindcss" in html.lower() or "tailwind" in html.lower()

    def test_generate_json(self) -> None:
        """Test JSON report generation."""
        json_str = self.reporter.generate_json(self.results)

        data = json.loads(json_str)

        assert "results" in data
        assert "summary" in data
        assert "generated_at" in data
        assert data["summary"]["total_queries"] == 1

    def test_generate_json_pretty(self) -> None:
        """Test JSON report generation with pretty printing."""
        json_str = self.reporter.generate_json(self.results, pretty=True)

        # Pretty printed JSON should have newlines
        assert "\n" in json_str

        # Should still be valid JSON
        data = json.loads(json_str)
        assert data["summary"]["total_queries"] == 1

    def test_save_reports(self) -> None:
        """Test saving reports to files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = self.reporter.save_reports(
                self.results,
                tmpdir,
                formats=["md", "html", "json"],
                title="Test Report",
            )

            assert "md" in saved
            assert "html" in saved
            assert "json" in saved

            # Check files exist
            assert saved["md"].exists()
            assert saved["html"].exists()
            assert saved["json"].exists()

            # Check file contents
            md_content = saved["md"].read_text()
            assert "# Test Report" in md_content

            html_content = saved["html"].read_text()
            assert "<html" in html_content

            json_content = saved["json"].read_text()
            data = json.loads(json_content)
            assert data["summary"]["total_queries"] == 1

    def test_save_reports_selective_formats(self) -> None:
        """Test saving only selected formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = self.reporter.save_reports(
                self.results,
                tmpdir,
                formats=["json"],  # Only JSON
            )

            assert "json" in saved
            assert "md" not in saved
            assert "html" not in saved

    def test_html_autoescape(self) -> None:
        """Test that HTML template has autoescape enabled."""
        # Create a result with potential XSS in the question
        test_query = TestQuery(
            id="xss_test",
            question="<script>alert('xss')</script>What is revenue?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
        )

        result = EvaluationResult(
            test_query=test_query,
            accuracy=AccuracyScore.CORRECT,
            failure_type=EvaluationFailureType.NONE,
            comparison=ComparisonDetails(),
        )

        results = EvaluationResults(
            results=[result],
            summary=EvaluationSummary(total_queries=1),
        )

        html = self.reporter.generate_html(results)

        # The script tag should be escaped
        assert "<script>" not in html
        assert "&lt;script&gt;" in html or "script" not in html.lower().replace("tailwindcss", "")
