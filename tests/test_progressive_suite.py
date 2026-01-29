"""Tests for the Progressive Difficulty Benchmark Suite.

Tests cover:
- Tier derivation functions
- TieredBenchmarkSuite model
- SuiteGenerator
- SuiteRunner
- ProgressiveReporter
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.benchmark import (
    TIER_COMPLEXITY_MAP,
    TIER_FAILURE_CATEGORIES,
    TIER_NAMES,
    BenchmarkQuery,
    ProgressiveReporter,
    SuiteGenerator,
    SuiteRunner,
    TieredBenchmarkResult,
    TieredBenchmarkSuite,
    TierResult,
    get_tier,
    group_by_tier,
)
from src.config import Config
from src.evaluation.models import (
    ComplexityLevel,
    FailureCategory,
    QueryType,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_config() -> Config:
    """Create a mock config for testing."""
    return Config(
        genie_space_id="test-space-123",
        mock_mode=True,
        databricks_host="https://test.databricks.com",
        databricks_token="test-token",
    )


@pytest.fixture
def sample_queries() -> list[BenchmarkQuery]:
    """Create sample benchmark queries for each tier."""
    queries = []

    # Tier 1 - Simple
    queries.append(
        BenchmarkQuery(
            id="test_simple_001",
            question="How many orders are there?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            expected_columns=["count"],
            expected_tables=["orders"],
            is_adversarial=False,
        )
    )

    # Tier 2 - Moderate
    queries.append(
        BenchmarkQuery(
            id="test_moderate_001",
            question="Show sales by region last month",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.MODERATE,
            failure_category=FailureCategory.TEMPORAL_CONFUSION,
            expected_columns=["region", "sales"],
            expected_tables=["sales", "regions"],
            is_adversarial=False,
        )
    )

    # Tier 3 - Complex
    queries.append(
        BenchmarkQuery(
            id="test_complex_001",
            question="Customers who bought in Q1 but not Q2",
            query_type=QueryType.JOIN,
            complexity=ComplexityLevel.COMPLEX,
            failure_category=FailureCategory.JOIN_COMPLEXITY,
            expected_columns=["customer"],
            expected_tables=["customers", "orders"],
            is_adversarial=False,
        )
    )

    # Tier 4 - Expert
    queries.append(
        BenchmarkQuery(
            id="test_expert_001",
            question="Rank customers by monthly spend with running totals",
            query_type=QueryType.RANKING,
            complexity=ComplexityLevel.EXPERT,
            failure_category=FailureCategory.BUSINESS_LOGIC,
            expected_columns=["customer", "rank", "running_total"],
            expected_tables=["customers", "orders"],
            is_adversarial=False,
        )
    )

    # Tier 5 - Adversarial
    queries.append(
        BenchmarkQuery(
            id="test_adversarial_001",
            question="How did weather affect sales?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.TRICK_QUESTIONS,
            expected_columns=[],
            expected_tables=[],
            is_adversarial=True,
        )
    )

    return queries


@pytest.fixture
def sample_suite(sample_queries: list[BenchmarkQuery]) -> TieredBenchmarkSuite:
    """Create a sample tiered benchmark suite."""
    grouped = group_by_tier(sample_queries)
    return TieredBenchmarkSuite(
        suite_id="test_suite_001",
        domain_name="Test Domain",
        schema_version="abc123",
        tiers=grouped,
        queries_per_tier=1,
    )


@pytest.fixture
def sample_tier_result() -> TierResult:
    """Create a sample tier result."""
    return TierResult(
        tier=1,
        tier_name="Simple",
        queries_count=10,
        correct_count=8,
        partial_count=1,
        wrong_count=1,
        failed_count=0,
    )


@pytest.fixture
def sample_tiered_result() -> TieredBenchmarkResult:
    """Create a sample tiered benchmark result."""
    tier_results = {
        1: TierResult(tier=1, tier_name="Simple", queries_count=10, correct_count=9),
        2: TierResult(tier=2, tier_name="Moderate", queries_count=10, correct_count=7),
        3: TierResult(tier=3, tier_name="Complex", queries_count=10, correct_count=5),
        4: TierResult(tier=4, tier_name="Expert", queries_count=10, correct_count=3),
        5: TierResult(tier=5, tier_name="Adversarial", queries_count=10, correct_count=8),
    }

    result = TieredBenchmarkResult(
        result_id="test_result_001",
        suite_id="test_suite_001",
        space_id="test-space-123",
        run_type="baseline",
        tier_results=tier_results,
    )
    result.calculate_scores()
    return result


# =============================================================================
# TEST TIER DERIVATION
# =============================================================================


class TestTierDerivation:
    """Test tier derivation functions."""

    def test_get_tier_simple(self) -> None:
        """Test tier derivation for simple complexity."""
        query = BenchmarkQuery(
            id="test",
            question="Test",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            is_adversarial=False,
        )
        assert get_tier(query) == 1

    def test_get_tier_moderate(self) -> None:
        """Test tier derivation for moderate complexity."""
        query = BenchmarkQuery(
            id="test",
            question="Test",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.MODERATE,
            failure_category=FailureCategory.TEMPORAL_CONFUSION,
            is_adversarial=False,
        )
        assert get_tier(query) == 2

    def test_get_tier_complex(self) -> None:
        """Test tier derivation for complex complexity."""
        query = BenchmarkQuery(
            id="test",
            question="Test",
            query_type=QueryType.JOIN,
            complexity=ComplexityLevel.COMPLEX,
            failure_category=FailureCategory.JOIN_COMPLEXITY,
            is_adversarial=False,
        )
        assert get_tier(query) == 3

    def test_get_tier_expert(self) -> None:
        """Test tier derivation for expert complexity."""
        query = BenchmarkQuery(
            id="test",
            question="Test",
            query_type=QueryType.RANKING,
            complexity=ComplexityLevel.EXPERT,
            failure_category=FailureCategory.BUSINESS_LOGIC,
            is_adversarial=False,
        )
        assert get_tier(query) == 4

    def test_get_tier_adversarial_by_flag(self) -> None:
        """Test tier derivation for adversarial query by flag."""
        query = BenchmarkQuery(
            id="test",
            question="Test",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            is_adversarial=True,
        )
        assert get_tier(query) == 5

    def test_get_tier_adversarial_by_category(self) -> None:
        """Test tier derivation for adversarial query by category."""
        query = BenchmarkQuery(
            id="test",
            question="Test",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.MODERATE,  # Complexity doesn't matter for trick questions
            failure_category=FailureCategory.TRICK_QUESTIONS,
            is_adversarial=False,  # Even without flag, category determines tier
        )
        assert get_tier(query) == 5

    def test_group_by_tier(self, sample_queries: list[BenchmarkQuery]) -> None:
        """Test grouping queries by tier."""
        grouped = group_by_tier(sample_queries)

        assert len(grouped[1]) == 1
        assert len(grouped[2]) == 1
        assert len(grouped[3]) == 1
        assert len(grouped[4]) == 1
        assert len(grouped[5]) == 1

        # Verify correct assignment
        assert grouped[1][0].id == "test_simple_001"
        assert grouped[2][0].id == "test_moderate_001"
        assert grouped[3][0].id == "test_complex_001"
        assert grouped[4][0].id == "test_expert_001"
        assert grouped[5][0].id == "test_adversarial_001"

    def test_group_by_tier_empty(self) -> None:
        """Test grouping empty query list."""
        grouped = group_by_tier([])
        for tier in range(1, 6):
            assert grouped[tier] == []


# =============================================================================
# TEST TIERED BENCHMARK SUITE MODEL
# =============================================================================


class TestTieredBenchmarkSuite:
    """Test TieredBenchmarkSuite model."""

    def test_suite_creation(self, sample_suite: TieredBenchmarkSuite) -> None:
        """Test suite creation with all tiers."""
        assert sample_suite.suite_id == "test_suite_001"
        assert sample_suite.domain_name == "Test Domain"
        assert sample_suite.total_queries == 5
        assert len(sample_suite.tiers) == 5

    def test_get_all_queries(self, sample_suite: TieredBenchmarkSuite) -> None:
        """Test getting all queries from suite."""
        all_queries = sample_suite.get_all_queries()
        assert len(all_queries) == 5

    def test_get_tier_queries(self, sample_suite: TieredBenchmarkSuite) -> None:
        """Test getting queries for specific tier."""
        tier_1_queries = sample_suite.get_tier_queries(1)
        assert len(tier_1_queries) == 1
        assert tier_1_queries[0].complexity == ComplexityLevel.SIMPLE

    def test_suite_serialization_roundtrip(self, sample_suite: TieredBenchmarkSuite) -> None:
        """Test suite serialization and deserialization."""
        data = sample_suite.to_dict()
        restored = TieredBenchmarkSuite.from_dict(data)

        assert restored.suite_id == sample_suite.suite_id
        assert restored.domain_name == sample_suite.domain_name
        assert restored.total_queries == sample_suite.total_queries
        assert len(restored.get_all_queries()) == len(sample_suite.get_all_queries())

    def test_suite_json_roundtrip(self, sample_suite: TieredBenchmarkSuite) -> None:
        """Test suite JSON save and load."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_suite.to_dict(), f, indent=2)
            temp_path = f.name

        try:
            loaded = SuiteGenerator.load_suite(temp_path)
            assert loaded.suite_id == sample_suite.suite_id
            assert loaded.total_queries == sample_suite.total_queries
        finally:
            Path(temp_path).unlink()


# =============================================================================
# TEST TIER RESULT MODEL
# =============================================================================


class TestTierResult:
    """Test TierResult model."""

    def test_tier_result_accuracy_calculation(self) -> None:
        """Test accuracy is calculated correctly."""
        result = TierResult(
            tier=1,
            tier_name="Simple",
            queries_count=10,
            correct_count=8,
            partial_count=1,
            wrong_count=1,
            failed_count=0,
        )
        assert result.accuracy == 80.0

    def test_tier_result_zero_queries(self) -> None:
        """Test accuracy with zero queries."""
        result = TierResult(
            tier=1,
            tier_name="Simple",
            queries_count=0,
        )
        assert result.accuracy == 0.0

    def test_tier_result_serialization(self, sample_tier_result: TierResult) -> None:
        """Test tier result serialization."""
        data = sample_tier_result.to_dict()
        restored = TierResult.from_dict(data)

        assert restored.tier == sample_tier_result.tier
        assert restored.tier_name == sample_tier_result.tier_name
        assert restored.queries_count == sample_tier_result.queries_count
        assert restored.correct_count == sample_tier_result.correct_count
        assert restored.accuracy == sample_tier_result.accuracy


# =============================================================================
# TEST TIERED BENCHMARK RESULT MODEL
# =============================================================================


class TestTieredBenchmarkResult:
    """Test TieredBenchmarkResult model."""

    def test_result_score_calculation(self, sample_tiered_result: TieredBenchmarkResult) -> None:
        """Test score calculations."""
        # Overall: (9+7+5+3+8)/50 = 32/50 = 64%
        assert sample_tiered_result.overall_accuracy == 64.0

        # Capability: avg of tiers 1-4 = (90+70+50+30)/4 = 60%
        assert sample_tiered_result.capability_score == 60.0

        # Safety: tier 5 = 80%
        assert sample_tiered_result.safety_score == 80.0

    def test_result_serialization_roundtrip(self, sample_tiered_result: TieredBenchmarkResult) -> None:
        """Test result serialization and deserialization."""
        data = sample_tiered_result.to_dict()
        restored = TieredBenchmarkResult.from_dict(data)

        assert restored.result_id == sample_tiered_result.result_id
        assert restored.overall_accuracy == sample_tiered_result.overall_accuracy
        assert restored.capability_score == sample_tiered_result.capability_score
        assert restored.safety_score == sample_tiered_result.safety_score


# =============================================================================
# TEST SUITE GENERATOR (MOCK MODE)
# =============================================================================


class TestSuiteGenerator:
    """Test SuiteGenerator in mock mode."""

    @pytest.fixture
    def temp_schema(self) -> Path:
        """Create a temporary schema file."""
        # Note: SchemaParser expects Genie Space YAML format with 'title' key
        schema_content = """
title: "Test Domain"
description: "Test domain for unit tests"

tables:
  - catalog_name: test_catalog
    schema_name: test_schema
    table_name: orders
    columns:
      - column_name: order_id
        type_text: STRING
        comment: "Order identifier"
      - column_name: amount
        type_text: DOUBLE
        comment: "Order amount"
      - column_name: order_date
        type_text: DATE
        comment: "Order date"

  - catalog_name: test_catalog
    schema_name: test_schema
    table_name: customers
    columns:
      - column_name: customer_id
        type_text: STRING
        comment: "Customer identifier"
      - column_name: name
        type_text: STRING
        comment: "Customer name"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(schema_content)
            return Path(f.name)

    def test_generator_creation(self, mock_config: Config, temp_schema: Path) -> None:
        """Test generator creation."""
        generator = SuiteGenerator(mock_config, temp_schema)
        assert generator.config == mock_config

        # Cleanup
        temp_schema.unlink()

    def test_generate_suite_mock(self, mock_config: Config, temp_schema: Path) -> None:
        """Test suite generation in mock mode."""
        generator = SuiteGenerator(mock_config, temp_schema)
        suite = generator.generate(queries_per_tier=3, tiers=[1, 5])

        assert suite.domain_name == "Test Domain"
        # Mock mode generates from templates, so we get at least some queries
        assert suite.total_queries > 0

        # Cleanup
        temp_schema.unlink()

    def test_save_and_load_suite(self, mock_config: Config, temp_schema: Path) -> None:
        """Test saving and loading suite."""
        generator = SuiteGenerator(mock_config, temp_schema)
        suite = generator.generate(queries_per_tier=2, tiers=[1])

        with tempfile.TemporaryDirectory() as temp_dir:
            saved = generator.save_suite(suite, temp_dir)

            assert "full_suite" in saved
            assert saved["full_suite"].exists()

            # Load and verify
            loaded = SuiteGenerator.load_suite(saved["full_suite"])
            assert loaded.suite_id == suite.suite_id
            assert loaded.domain_name == suite.domain_name

        # Cleanup
        temp_schema.unlink()


# =============================================================================
# TEST SUITE RUNNER (MOCK MODE)
# =============================================================================


class TestSuiteRunner:
    """Test SuiteRunner in mock mode."""

    def test_runner_creation(self, mock_config: Config) -> None:
        """Test runner creation."""
        runner = SuiteRunner(mock_config)
        assert runner.config == mock_config

    def test_run_suite_mock(self, mock_config: Config, sample_suite: TieredBenchmarkSuite) -> None:
        """Test running suite in mock mode."""
        runner = SuiteRunner(mock_config)
        result = runner.run(sample_suite, run_type="baseline")

        assert result.suite_id == sample_suite.suite_id
        assert result.space_id == mock_config.genie_space_id
        assert result.run_type == "baseline"
        assert result.total_queries == sample_suite.total_queries

    def test_run_specific_tiers(self, mock_config: Config, sample_suite: TieredBenchmarkSuite) -> None:
        """Test running specific tiers."""
        runner = SuiteRunner(mock_config)
        result = runner.run(sample_suite, run_type="baseline", tiers=[1, 2])

        # Should only have results for tiers 1 and 2
        assert result.tier_results[1].queries_count == 1
        assert result.tier_results[2].queries_count == 1
        # Other tiers should be empty or zero
        assert result.tier_results[3].queries_count == 0
        assert result.tier_results[4].queries_count == 0
        assert result.tier_results[5].queries_count == 0

    def test_save_and_load_result(self, mock_config: Config, sample_tiered_result: TieredBenchmarkResult) -> None:
        """Test saving and loading results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            SuiteRunner.save_result(sample_tiered_result, temp_path)
            loaded = SuiteRunner.load_result(temp_path)

            assert loaded.result_id == sample_tiered_result.result_id
            assert loaded.overall_accuracy == sample_tiered_result.overall_accuracy
            assert loaded.capability_score == sample_tiered_result.capability_score
            assert loaded.safety_score == sample_tiered_result.safety_score
        finally:
            temp_path.unlink()


# =============================================================================
# TEST PROGRESSIVE REPORTER
# =============================================================================


class TestProgressiveReporter:
    """Test ProgressiveReporter."""

    def test_reporter_creation(self) -> None:
        """Test reporter creation."""
        reporter = ProgressiveReporter()
        assert reporter._md_env is None  # Lazy loaded
        assert reporter._html_env is None

    def test_generate_markdown(self, sample_tiered_result: TieredBenchmarkResult) -> None:
        """Test Markdown report generation."""
        reporter = ProgressiveReporter()
        markdown = reporter.generate_markdown(sample_tiered_result, title="Test Report")

        assert "Test Report" in markdown
        assert "64.0%" in markdown  # Overall accuracy
        assert "60.0%" in markdown  # Capability score
        assert "80.0%" in markdown  # Safety score
        assert "Simple" in markdown
        assert "Expert" in markdown
        assert "Adversarial" in markdown

    def test_generate_html(self, sample_tiered_result: TieredBenchmarkResult) -> None:
        """Test HTML report generation."""
        reporter = ProgressiveReporter()
        html = reporter.generate_html(sample_tiered_result, title="Test Dashboard")

        assert "Test Dashboard" in html
        assert "<!DOCTYPE html>" in html
        assert "Chart.js" in html or "chart.js" in html.lower()
        assert "tierChart" in html
        # Check for Chart.js data encoding with tojson
        assert "tierData" in html

    def test_generate_json(self, sample_tiered_result: TieredBenchmarkResult) -> None:
        """Test JSON report generation."""
        reporter = ProgressiveReporter()
        json_str = reporter.generate_json(sample_tiered_result)

        data = json.loads(json_str)
        assert "summary" in data
        assert data["summary"]["overall_accuracy"] == 64.0
        assert data["summary"]["capability_score"] == 60.0
        assert data["summary"]["safety_score"] == 80.0

    def test_save_reports(self, sample_tiered_result: TieredBenchmarkResult) -> None:
        """Test saving reports to files."""
        reporter = ProgressiveReporter()

        with tempfile.TemporaryDirectory() as temp_dir:
            saved = reporter.save_reports(
                result=sample_tiered_result,
                output_dir=temp_dir,
                formats=["md", "html", "json"],
                title="Test Report",
            )

            assert "md" in saved
            assert "html" in saved
            assert "json" in saved

            for path in saved.values():
                assert path.exists()
                content = path.read_text()
                assert len(content) > 0

    def test_format_filters(self) -> None:
        """Test Jinja2 filters."""
        from src.benchmark.progressive_reporter import ProgressiveReporter

        # Test format_percent
        assert ProgressiveReporter._format_percent(75.5) == "75.5%"
        assert ProgressiveReporter._format_percent(100.0) == "100.0%"

        # Test tier_name
        assert ProgressiveReporter._tier_name(1) == "Simple"
        assert ProgressiveReporter._tier_name(5) == "Adversarial"
        assert ProgressiveReporter._tier_name(99) == "Tier 99"

        # Test accuracy_class
        assert ProgressiveReporter._accuracy_class(90.0) == "accuracy-high"
        assert ProgressiveReporter._accuracy_class(60.0) == "accuracy-medium"
        assert ProgressiveReporter._accuracy_class(30.0) == "accuracy-low"

        # Test progress_bar
        bar = ProgressiveReporter._progress_bar(50.0, width=10)
        assert bar == "[#####-----]"


# =============================================================================
# TEST CONSTANTS
# =============================================================================


class TestConstants:
    """Test module constants."""

    def test_tier_names(self) -> None:
        """Test tier names constant."""
        assert TIER_NAMES[1] == "Simple"
        assert TIER_NAMES[2] == "Moderate"
        assert TIER_NAMES[3] == "Complex"
        assert TIER_NAMES[4] == "Expert"
        assert TIER_NAMES[5] == "Adversarial"

    def test_tier_complexity_map(self) -> None:
        """Test tier to complexity mapping."""
        assert TIER_COMPLEXITY_MAP[1] == ComplexityLevel.SIMPLE
        assert TIER_COMPLEXITY_MAP[2] == ComplexityLevel.MODERATE
        assert TIER_COMPLEXITY_MAP[3] == ComplexityLevel.COMPLEX
        assert TIER_COMPLEXITY_MAP[4] == ComplexityLevel.EXPERT
        assert TIER_COMPLEXITY_MAP[5] == ComplexityLevel.SIMPLE  # Adversarial

    def test_tier_failure_categories(self) -> None:
        """Test tier to failure categories mapping."""
        assert FailureCategory.AMBIGUOUS_COLUMNS in TIER_FAILURE_CATEGORIES[1]
        assert FailureCategory.TEMPORAL_CONFUSION in TIER_FAILURE_CATEGORIES[2]
        assert FailureCategory.JOIN_COMPLEXITY in TIER_FAILURE_CATEGORIES[3]
        assert FailureCategory.BUSINESS_LOGIC in TIER_FAILURE_CATEGORIES[4]
        assert FailureCategory.TRICK_QUESTIONS in TIER_FAILURE_CATEGORIES[5]
