"""Tests for the LLM-Powered Benchmark System.

This module provides unit tests for the benchmark system including:
- Models (BenchmarkQuery, BenchmarkRun, BenchmarkComparison)
- Schema parser (SchemaParser, DomainContext)
- LLM query generator (mock mode)
- Benchmark evaluator (mock mode)
- Benchmark reporter

All tests use mock mode to avoid API calls.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.benchmark import (
    BenchmarkComparison,
    BenchmarkEvaluator,
    BenchmarkQuery,
    BenchmarkReporter,
    BenchmarkRun,
    ColumnInfo,
    DomainContext,
    EvaluationMode,
    GenerationSource,
    LLMJudgeEvaluator,
    LLMQueryGenerator,
    RelationshipInfo,
    SchemaParser,
    Severity,
    TableInfo,
)
from src.config import Config
from src.evaluation.models import (
    AccuracyScore,
    ComparisonDetails,
    ComplexityLevel,
    EvaluationFailureType,
    EvaluationResult,
    EvaluationSummary,
    FailureCategory,
    QueryType,
    TestQuery,
)

# =============================================================================
# Test BenchmarkQuery Model
# =============================================================================


class TestBenchmarkQuery:
    """Tests for BenchmarkQuery dataclass."""

    def test_create_benchmark_query(self) -> None:
        """Test creating a BenchmarkQuery with all fields."""
        query = BenchmarkQuery(
            id="bm_001",
            question="What is total revenue by region?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.MODERATE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
            expected_columns=["region", "revenue"],
            expected_tables=["sales"],
            description="Test revenue aggregation by region",
            is_adversarial=False,
            domain="sales",
            generated_by="llm",
            schema_version="abc123",
            expected_failure=None,
            correct_sql="SELECT region, SUM(revenue) FROM sales GROUP BY region",
            severity=Severity.HIGH,
            model_name="databricks-meta-llama-3-1-70b-instruct",
            temperature=0.1,
            prompt_hash="xyz789",
            generated_at="2024-01-28T12:00:00",
        )

        assert query.id == "bm_001"
        assert query.question == "What is total revenue by region?"
        assert query.query_type == QueryType.AGGREGATION
        assert query.complexity == ComplexityLevel.MODERATE
        assert query.failure_category == FailureCategory.AMBIGUOUS_COLUMNS
        assert query.expected_columns == ["region", "revenue"]
        assert query.expected_tables == ["sales"]
        assert query.domain == "sales"
        assert query.generated_by == "llm"
        assert query.schema_version == "abc123"
        assert query.severity == Severity.HIGH
        assert query.model_name == "databricks-meta-llama-3-1-70b-instruct"
        assert query.temperature == 0.1

    def test_to_test_query_conversion(self) -> None:
        """Test converting BenchmarkQuery to TestQuery."""
        benchmark_query = BenchmarkQuery(
            id="bm_002",
            question="Show top 10 products",
            query_type=QueryType.RANKING,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.CRYPTIC_CODES,
            expected_columns=["product_name", "sales"],
            expected_tables=["products", "sales"],
            description="Test ranking query",
            is_adversarial=True,
            domain="inventory",
            generated_by="llm",
        )

        test_query = benchmark_query.to_test_query()

        assert isinstance(test_query, TestQuery)
        assert test_query.id == "bm_002"
        assert test_query.question == "Show top 10 products"
        assert test_query.query_type == QueryType.RANKING
        assert test_query.complexity == ComplexityLevel.SIMPLE
        assert test_query.failure_category == FailureCategory.CRYPTIC_CODES
        assert test_query.expected_columns == ["product_name", "sales"]
        assert test_query.expected_tables == ["products", "sales"]
        assert test_query.is_adversarial is True

    def test_to_dict_serialization(self) -> None:
        """Test BenchmarkQuery serialization to dict."""
        query = BenchmarkQuery(
            id="bm_003",
            question="Test question",
            query_type=QueryType.JOIN,
            complexity=ComplexityLevel.COMPLEX,
            failure_category=FailureCategory.JOIN_COMPLEXITY,
            expected_columns=["a", "b"],
            expected_tables=["t1", "t2"],
            domain="test_domain",
            generated_by="static",
            severity=Severity.CRITICAL,
        )

        data = query.to_dict()

        assert data["id"] == "bm_003"
        assert data["query_type"] == "join"
        assert data["complexity"] == "complex"
        assert data["failure_category"] == "join_complexity"
        assert data["domain"] == "test_domain"
        assert data["generated_by"] == "static"
        assert data["severity"] == "critical"

    def test_from_dict_deserialization(self) -> None:
        """Test BenchmarkQuery deserialization from dict."""
        data = {
            "id": "bm_004",
            "question": "What are monthly sales trends?",
            "query_type": "temporal",
            "complexity": "moderate",
            "failure_category": "temporal_confusion",
            "expected_columns": ["month", "sales"],
            "expected_tables": ["sales"],
            "domain": "analytics",
            "generated_by": "llm",
            "schema_version": "v1.0",
            "severity": "high",
            "model_name": "test-model",
        }

        query = BenchmarkQuery.from_dict(data)

        assert query.id == "bm_004"
        assert query.query_type == QueryType.TEMPORAL
        assert query.complexity == ComplexityLevel.MODERATE
        assert query.failure_category == FailureCategory.TEMPORAL_CONFUSION
        assert query.domain == "analytics"
        assert query.generated_by == "llm"
        assert query.severity == Severity.HIGH
        assert query.model_name == "test-model"

    def test_roundtrip_serialization(self) -> None:
        """Test BenchmarkQuery serialization roundtrip."""
        original = BenchmarkQuery(
            id="bm_005",
            question="Complex join query",
            query_type=QueryType.JOIN,
            complexity=ComplexityLevel.COMPLEX,
            failure_category=FailureCategory.JOIN_COMPLEXITY,
            expected_columns=["a", "b", "c"],
            expected_tables=["t1", "t2", "t3"],
            description="Test complex join",
            is_adversarial=True,
            domain="test",
            generated_by="llm",
            schema_version="hash123",
            expected_failure="Expected to fail on join",
            correct_sql="SELECT a, b, c FROM t1 JOIN t2 JOIN t3",
            severity=Severity.MEDIUM,
            model_name="test-model",
            temperature=0.5,
            prompt_hash="prompt123",
            generated_at="2024-01-28T10:00:00",
        )

        data = original.to_dict()
        restored = BenchmarkQuery.from_dict(data)

        assert restored.id == original.id
        assert restored.question == original.question
        assert restored.query_type == original.query_type
        assert restored.complexity == original.complexity
        assert restored.failure_category == original.failure_category
        assert restored.expected_columns == original.expected_columns
        assert restored.expected_tables == original.expected_tables
        assert restored.is_adversarial == original.is_adversarial
        assert restored.domain == original.domain
        assert restored.generated_by == original.generated_by
        assert restored.schema_version == original.schema_version
        assert restored.severity == original.severity
        assert restored.model_name == original.model_name
        assert restored.temperature == original.temperature


# =============================================================================
# Test BenchmarkRun Model
# =============================================================================


class TestBenchmarkRun:
    """Tests for BenchmarkRun dataclass."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.test_query = TestQuery(
            id="test_001",
            question="Test question",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
        )

        self.result = EvaluationResult(
            test_query=self.test_query,
            accuracy=AccuracyScore.CORRECT,
            failure_type=EvaluationFailureType.NONE,
            comparison=ComparisonDetails(),
            execution_time_ms=100,
        )

        self.summary = EvaluationSummary(
            total_queries=1,
            correct_count=1,
            partial_count=0,
            wrong_count=0,
            failed_count=0,
        )

    def test_create_benchmark_run(self) -> None:
        """Test creating a BenchmarkRun."""
        run = BenchmarkRun(
            run_id="run_001",
            space_id="test_space_123",
            run_type="baseline",
            queries_evaluated=10,
            results=[self.result],
            summary=self.summary,
            config_snapshot={"mock_mode": True},
            provenance={"model": "test"},
        )

        assert run.run_id == "run_001"
        assert run.space_id == "test_space_123"
        assert run.run_type == "baseline"
        assert run.queries_evaluated == 10
        assert len(run.results) == 1
        assert run.summary is not None
        assert run.summary.total_queries == 1

    def test_benchmark_run_serialization(self) -> None:
        """Test BenchmarkRun serialization to dict."""
        run = BenchmarkRun(
            run_id="run_002",
            space_id="space_456",
            run_type="enhanced",
            queries_evaluated=5,
            results=[self.result],
            summary=self.summary,
            started_at="2024-01-28T10:00:00",
            completed_at="2024-01-28T10:05:00",
        )

        data = run.to_dict()

        assert data["run_id"] == "run_002"
        assert data["space_id"] == "space_456"
        assert data["run_type"] == "enhanced"
        assert data["queries_evaluated"] == 5
        assert len(data["results"]) == 1
        assert data["summary"]["total_queries"] == 1

    def test_benchmark_run_roundtrip(self) -> None:
        """Test BenchmarkRun serialization roundtrip."""
        original = BenchmarkRun(
            run_id="run_003",
            space_id="space_789",
            run_type="baseline",
            queries_evaluated=1,
            results=[self.result],
            summary=self.summary,
        )

        data = original.to_dict()
        restored = BenchmarkRun.from_dict(data)

        assert restored.run_id == original.run_id
        assert restored.space_id == original.space_id
        assert restored.run_type == original.run_type
        assert restored.queries_evaluated == original.queries_evaluated
        assert len(restored.results) == len(original.results)


# =============================================================================
# Test BenchmarkComparison Model
# =============================================================================


class TestBenchmarkComparison:
    """Tests for BenchmarkComparison dataclass."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create test queries
        self.query1 = TestQuery(
            id="q1",
            question="Query 1",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
        )
        self.query2 = TestQuery(
            id="q2",
            question="Query 2",
            query_type=QueryType.FILTER,
            complexity=ComplexityLevel.MODERATE,
            failure_category=FailureCategory.CRYPTIC_CODES,
        )

        # Create baseline results (q1: WRONG, q2: PARTIAL)
        self.baseline_results = [
            EvaluationResult(
                test_query=self.query1,
                accuracy=AccuracyScore.WRONG,
                failure_type=EvaluationFailureType.WRONG_COLUMNS,
                comparison=ComparisonDetails(),
            ),
            EvaluationResult(
                test_query=self.query2,
                accuracy=AccuracyScore.PARTIAL,
                failure_type=EvaluationFailureType.WRONG_COLUMNS,
                comparison=ComparisonDetails(),
            ),
        ]

        # Create enhanced results (q1: CORRECT improvement, q2: WRONG regression)
        self.enhanced_results = [
            EvaluationResult(
                test_query=self.query1,
                accuracy=AccuracyScore.CORRECT,
                failure_type=EvaluationFailureType.NONE,
                comparison=ComparisonDetails(),
            ),
            EvaluationResult(
                test_query=self.query2,
                accuracy=AccuracyScore.WRONG,
                failure_type=EvaluationFailureType.WRONG_COLUMNS,
                comparison=ComparisonDetails(),
            ),
        ]

        self.baseline_summary = EvaluationSummary(
            total_queries=2,
            correct_count=0,
            partial_count=1,
            wrong_count=1,
            failed_count=0,
            accuracy_by_failure_category={
                "ambiguous_columns": {"correct": 0, "wrong": 1},
                "cryptic_codes": {"partial": 1},
            },
        )

        self.enhanced_summary = EvaluationSummary(
            total_queries=2,
            correct_count=1,
            partial_count=0,
            wrong_count=1,
            failed_count=0,
            accuracy_by_failure_category={
                "ambiguous_columns": {"correct": 1},
                "cryptic_codes": {"wrong": 1},
            },
        )

    def test_calculate_metrics(self) -> None:
        """Test calculation of comparison metrics."""
        baseline = BenchmarkRun(
            run_id="baseline_1",
            space_id="space",
            run_type="baseline",
            queries_evaluated=2,
            results=self.baseline_results,
            summary=self.baseline_summary,
        )

        enhanced = BenchmarkRun(
            run_id="enhanced_1",
            space_id="space",
            run_type="enhanced",
            queries_evaluated=2,
            results=self.enhanced_results,
            summary=self.enhanced_summary,
        )

        comparison = BenchmarkComparison(
            comparison_id="cmp_1",
            baseline=baseline,
            enhanced=enhanced,
        )
        comparison.calculate_metrics()

        # Enhanced: 50% (1/2), Baseline: 0% (0/2) -> delta = 50
        assert comparison.accuracy_delta == 50.0

        # q1 improved (WRONG -> CORRECT)
        assert "q1" in comparison.improvements

        # q2 regressed (PARTIAL -> WRONG)
        assert "q2" in comparison.regressions

    def test_has_regressions(self) -> None:
        """Test regression detection."""
        baseline = BenchmarkRun(
            run_id="baseline",
            space_id="space",
            run_type="baseline",
            queries_evaluated=2,
            results=self.baseline_results,
            summary=self.baseline_summary,
        )

        enhanced = BenchmarkRun(
            run_id="enhanced",
            space_id="space",
            run_type="enhanced",
            queries_evaluated=2,
            results=self.enhanced_results,
            summary=self.enhanced_summary,
        )

        comparison = BenchmarkComparison(
            comparison_id="cmp",
            baseline=baseline,
            enhanced=enhanced,
        )
        comparison.calculate_metrics()

        assert comparison.has_regressions() is True

    def test_comparison_serialization_roundtrip(self) -> None:
        """Test BenchmarkComparison serialization roundtrip."""
        baseline = BenchmarkRun(
            run_id="baseline",
            space_id="space",
            run_type="baseline",
            queries_evaluated=2,
            results=self.baseline_results,
            summary=self.baseline_summary,
        )

        enhanced = BenchmarkRun(
            run_id="enhanced",
            space_id="space",
            run_type="enhanced",
            queries_evaluated=2,
            results=self.enhanced_results,
            summary=self.enhanced_summary,
        )

        original = BenchmarkComparison(
            comparison_id="cmp_original",
            baseline=baseline,
            enhanced=enhanced,
        )
        original.calculate_metrics()

        data = original.to_dict()
        restored = BenchmarkComparison.from_dict(data)

        assert restored.comparison_id == original.comparison_id
        assert restored.accuracy_delta == original.accuracy_delta
        assert restored.regressions == original.regressions
        assert restored.improvements == original.improvements


# =============================================================================
# Test Schema Parser
# =============================================================================


class TestSchemaParser:
    """Tests for SchemaParser and DomainContext."""

    def test_table_info_creation(self) -> None:
        """Test TableInfo dataclass creation."""
        table = TableInfo(
            name="sales",
            full_identifier="catalog.schema.sales",
            description="Sales transactions",
            columns=[
                ColumnInfo(name="id", data_type="int", description="Primary key"),
                ColumnInfo(name="revenue", data_type="float", description="Sale revenue"),
            ],
        )

        assert table.name == "sales"
        assert table.full_identifier == "catalog.schema.sales"
        assert len(table.columns) == 2
        assert table.columns[0].name == "id"

    def test_domain_context_to_prompt_context(self) -> None:
        """Test DomainContext.to_prompt_context() generation."""
        context = DomainContext(
            domain_name="Test Sales Domain",
            tables=[
                TableInfo(
                    name="sales",
                    full_identifier="catalog.schema.sales",
                    description="Sales data",
                    columns=[
                        ColumnInfo(name="sale_id", data_type="int"),
                        ColumnInfo(name="revenue", data_type="float"),
                    ],
                ),
            ],
            relationships=[
                RelationshipInfo(
                    left_table="sales",
                    right_table="products",
                    join_keys=["product_id"],
                    relationship_type="many-to-one",
                ),
            ],
            business_rules=["Revenue should always be positive"],
            metrics=["Total Revenue", "Sales Count"],
        )

        prompt = context.to_prompt_context()

        assert "Test Sales Domain" in prompt
        assert "sales" in prompt
        assert "revenue" in prompt
        assert "Revenue should always be positive" in prompt

    def test_schema_parser_with_minimal_yaml(self) -> None:
        """Test SchemaParser with minimal YAML config (Genie Space format)."""
        # The parser expects Genie Space config format with 'identifier' field
        yaml_content = """
title: Test Product Domain
tables:
  - identifier: catalog.schema.products
instructions: |
  Column Definitions for products:
  - product_id: Primary key identifier
  - product_name: Name of the product
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            yaml_path = f.name

        try:
            parser = SchemaParser(yaml_path)
            context = parser.parse()

            assert context.domain_name == "Test Product Domain"
            assert len(context.tables) == 1
            assert context.tables[0].name == "products"
            assert context.tables[0].full_identifier == "catalog.schema.products"
        finally:
            Path(yaml_path).unlink()

    def test_schema_parser_get_schema_hash(self) -> None:
        """Test schema hash generation for versioning."""
        yaml_content = """
tables:
  - name: test
    columns:
      - name: id
        type: int
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            yaml_path = f.name

        try:
            parser = SchemaParser(yaml_path)
            parser.parse()
            hash1 = parser.get_schema_hash()

            # Same content should produce same hash
            parser2 = SchemaParser(yaml_path)
            parser2.parse()
            hash2 = parser2.get_schema_hash()

            assert hash1 == hash2
            assert len(hash1) > 0
        finally:
            Path(yaml_path).unlink()


# =============================================================================
# Test LLM Query Generator (Mock Mode)
# =============================================================================


class TestLLMQueryGenerator:
    """Tests for LLMQueryGenerator in mock mode."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = Config(genie_space_id="test_space", mock_mode=True)
        self.generator = LLMQueryGenerator(self.config)

        self.domain_context = DomainContext(
            domain_name="Test Sales Domain",
            tables=[
                TableInfo(
                    name="sales",
                    full_identifier="catalog.schema.sales",
                    description="Sales transactions",
                    columns=[
                        ColumnInfo(name="sale_id", data_type="int"),
                        ColumnInfo(name="revenue", data_type="float"),
                        ColumnInfo(name="sale_date", data_type="date"),
                    ],
                ),
            ],
            relationships=[],
            business_rules=["Revenue is always positive"],
            metrics=["Total Revenue"],
        )

    def test_mock_mode_generation(self) -> None:
        """Test query generation in mock mode."""
        queries = self.generator.generate(
            domain_context=self.domain_context,
            failure_categories=[FailureCategory.AMBIGUOUS_COLUMNS],
            queries_per_category=3,
            schema_version="test_v1",
        )

        # Mock mode generates fixed number of queries (2 per category)
        assert len(queries) >= 1
        for query in queries:
            assert isinstance(query, BenchmarkQuery)
            assert query.failure_category == FailureCategory.AMBIGUOUS_COLUMNS
            assert query.schema_version == "test_v1"
            assert query.generated_by == "llm"

    def test_generate_multiple_categories(self) -> None:
        """Test generating queries for multiple failure categories."""
        categories = [
            FailureCategory.AMBIGUOUS_COLUMNS,
            FailureCategory.TEMPORAL_CONFUSION,
        ]

        queries = self.generator.generate(
            domain_context=self.domain_context,
            failure_categories=categories,
            queries_per_category=2,
        )

        assert len(queries) == 4  # 2 categories * 2 queries

        # Check we have queries for both categories
        category_values = {q.failure_category for q in queries}
        assert FailureCategory.AMBIGUOUS_COLUMNS in category_values
        assert FailureCategory.TEMPORAL_CONFUSION in category_values

    def test_save_and_load_queries(self) -> None:
        """Test saving and loading queries to/from JSON."""
        queries = self.generator.generate(
            domain_context=self.domain_context,
            failure_categories=[FailureCategory.AMBIGUOUS_COLUMNS],
            queries_per_category=2,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json_path = Path(f.name)

        try:
            self.generator.save_queries(queries, json_path)
            loaded = LLMQueryGenerator.load_queries(json_path)

            assert len(loaded) == len(queries)
            for orig, load in zip(queries, loaded):
                assert orig.id == load.id
                assert orig.question == load.question
                assert orig.failure_category == load.failure_category
        finally:
            json_path.unlink()


# =============================================================================
# Test Benchmark Evaluator (Mock Mode)
# =============================================================================


class TestBenchmarkEvaluator:
    """Tests for BenchmarkEvaluator in mock mode."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = Config(genie_space_id="test_space", mock_mode=True)
        self.evaluator = BenchmarkEvaluator(self.config)

        self.benchmark_queries = [
            BenchmarkQuery(
                id="bm_001",
                question="What is total revenue?",
                query_type=QueryType.AGGREGATION,
                complexity=ComplexityLevel.SIMPLE,
                failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
                expected_columns=["revenue"],
                expected_tables=["sales"],
            ),
            BenchmarkQuery(
                id="bm_002",
                question="Show sales by region",
                query_type=QueryType.AGGREGATION,
                complexity=ComplexityLevel.MODERATE,
                failure_category=FailureCategory.CRYPTIC_CODES,
                expected_columns=["region", "sales"],
                expected_tables=["sales"],
            ),
        ]

    def test_run_benchmark_baseline(self) -> None:
        """Test running a baseline benchmark."""
        run = self.evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="baseline",
        )

        assert isinstance(run, BenchmarkRun)
        assert run.run_type == "baseline"
        assert run.queries_evaluated == 2
        assert len(run.results) == 2
        assert run.summary is not None
        assert run.summary.total_queries == 2

    def test_run_benchmark_enhanced(self) -> None:
        """Test running an enhanced benchmark."""
        run = self.evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="enhanced",
        )

        assert run.run_type == "enhanced"
        assert run.queries_evaluated == 2

    def test_compare_runs(self) -> None:
        """Test comparing baseline and enhanced runs."""
        baseline = self.evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="baseline",
        )

        enhanced = self.evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="enhanced",
        )

        comparison = self.evaluator.compare_runs(baseline, enhanced)

        assert isinstance(comparison, BenchmarkComparison)
        assert comparison.baseline.run_id == baseline.run_id
        assert comparison.enhanced.run_id == enhanced.run_id
        # Metrics should be calculated
        assert comparison.accuracy_delta is not None

    def test_save_and_load_run(self) -> None:
        """Test saving and loading benchmark runs."""
        run = self.evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="baseline",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json_path = Path(f.name)

        try:
            self.evaluator.save_run(run, json_path)
            loaded = BenchmarkEvaluator.load_run(json_path)

            assert loaded.run_id == run.run_id
            assert loaded.run_type == run.run_type
            assert loaded.queries_evaluated == run.queries_evaluated
        finally:
            json_path.unlink()


# =============================================================================
# Test Benchmark Reporter
# =============================================================================


class TestBenchmarkReporter:
    """Tests for BenchmarkReporter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.reporter = BenchmarkReporter()

        # Create test data
        test_query = TestQuery(
            id="test_001",
            question="What is total revenue?",
            query_type=QueryType.AGGREGATION,
            complexity=ComplexityLevel.SIMPLE,
            failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
        )

        baseline_result = EvaluationResult(
            test_query=test_query,
            accuracy=AccuracyScore.WRONG,
            failure_type=EvaluationFailureType.WRONG_COLUMNS,
            comparison=ComparisonDetails(),
        )

        enhanced_result = EvaluationResult(
            test_query=test_query,
            accuracy=AccuracyScore.CORRECT,
            failure_type=EvaluationFailureType.NONE,
            comparison=ComparisonDetails(),
        )

        baseline_summary = EvaluationSummary(
            total_queries=1,
            correct_count=0,
            partial_count=0,
            wrong_count=1,
            failed_count=0,
            accuracy_by_failure_category={"ambiguous_columns": {"wrong": 1}},
        )

        enhanced_summary = EvaluationSummary(
            total_queries=1,
            correct_count=1,
            partial_count=0,
            wrong_count=0,
            failed_count=0,
            accuracy_by_failure_category={"ambiguous_columns": {"correct": 1}},
        )

        self.baseline_run = BenchmarkRun(
            run_id="baseline_test",
            space_id="test_space",
            run_type="baseline",
            queries_evaluated=1,
            results=[baseline_result],
            summary=baseline_summary,
        )

        self.enhanced_run = BenchmarkRun(
            run_id="enhanced_test",
            space_id="test_space",
            run_type="enhanced",
            queries_evaluated=1,
            results=[enhanced_result],
            summary=enhanced_summary,
        )

        self.comparison = BenchmarkComparison(
            comparison_id="cmp_test",
            baseline=self.baseline_run,
            enhanced=self.enhanced_run,
        )
        self.comparison.calculate_metrics()

    def test_generate_markdown(self) -> None:
        """Test markdown report generation."""
        markdown = self.reporter.generate_markdown(self.comparison, title="Test Benchmark Report")

        assert "# Test Benchmark Report" in markdown
        assert "Baseline" in markdown
        assert "Enhanced" in markdown
        assert "baseline_test" in markdown
        assert "enhanced_test" in markdown

    def test_generate_html(self) -> None:
        """Test HTML report generation."""
        html = self.reporter.generate_html(self.comparison, title="Test Benchmark Dashboard")

        assert "<html" in html
        assert "Test Benchmark Dashboard" in html
        assert "Baseline" in html
        assert "Enhanced" in html

    def test_generate_json(self) -> None:
        """Test JSON report generation."""
        json_str = self.reporter.generate_json(self.comparison)

        data = json.loads(json_str)

        assert "comparison_id" in data
        assert "baseline" in data
        assert "enhanced" in data
        assert "accuracy_delta" in data
        assert data["comparison_id"] == "cmp_test"

    def test_save_reports(self) -> None:
        """Test saving reports to files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = self.reporter.save_reports(
                comparison=self.comparison,
                output_dir=tmpdir,
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
            assert data["comparison_id"] == "cmp_test"


# =============================================================================
# Test Enum Values
# =============================================================================


class TestEnumValues:
    """Tests for enum value consistency."""

    def test_generation_source_values(self) -> None:
        """Test GenerationSource enum values."""
        assert GenerationSource.LLM.value == "llm"
        assert GenerationSource.STATIC.value == "static"
        assert GenerationSource.HYBRID.value == "hybrid"

    def test_severity_values(self) -> None:
        """Test Severity enum values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"

    def test_evaluation_mode_values(self) -> None:
        """Test EvaluationMode enum values."""
        assert EvaluationMode.STRING_MATCH.value == "string_match"
        assert EvaluationMode.LLM_JUDGE.value == "llm_judge"


# =============================================================================
# Test LLM Judge Evaluator (Mock Mode)
# =============================================================================


class TestLLMJudgeEvaluator:
    """Tests for LLMJudgeEvaluator in mock mode."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = Config(genie_space_id="test_space", mock_mode=True)
        self.judge = LLMJudgeEvaluator(self.config)

    def test_mock_evaluate_semantic_match(self) -> None:
        """Test mock evaluation with semantically equivalent columns."""
        accuracy, failure_type, comparison = self.judge.evaluate(
            question="What is total revenue?",
            expected_columns=["revenue"],
            expected_tables=["sales"],
            sql="SELECT SUM(total_revenue) FROM sales",
            actual_columns=["total_revenue"],
        )

        # Mock uses substring containment - "revenue" is in "total_revenue"
        assert accuracy == AccuracyScore.CORRECT
        assert failure_type == EvaluationFailureType.NONE
        assert "[Mock LLM Judge]" in comparison.comparison_notes

    def test_mock_evaluate_exact_match(self) -> None:
        """Test mock evaluation with exact column match."""
        accuracy, failure_type, comparison = self.judge.evaluate(
            question="What is revenue by region?",
            expected_columns=["region", "revenue"],
            expected_tables=["sales"],
            sql="SELECT region, SUM(revenue) FROM sales GROUP BY region",
            actual_columns=["region", "revenue"],
        )

        assert accuracy == AccuracyScore.CORRECT
        assert failure_type == EvaluationFailureType.NONE

    def test_mock_evaluate_partial_match(self) -> None:
        """Test mock evaluation with partial column match."""
        accuracy, failure_type, comparison = self.judge.evaluate(
            question="What are sales by product and region?",
            expected_columns=["product", "region", "sales"],
            expected_tables=["sales"],
            sql="SELECT product, SUM(sales) FROM sales GROUP BY product",
            actual_columns=["product", "sales"],
        )

        # 2/3 columns match = ~67% < 80% but >= 50% = PARTIAL
        assert accuracy == AccuracyScore.PARTIAL
        assert "region" in comparison.missing_columns

    def test_mock_evaluate_wrong(self) -> None:
        """Test mock evaluation with completely wrong columns."""
        accuracy, failure_type, comparison = self.judge.evaluate(
            question="What is total revenue?",
            expected_columns=["revenue"],
            expected_tables=["sales"],
            sql="SELECT customer_name FROM customers",
            actual_columns=["customer_name"],
        )

        # No column match = WRONG
        assert accuracy == AccuracyScore.WRONG

    def test_mock_evaluate_no_sql(self) -> None:
        """Test mock evaluation when no SQL was generated."""
        accuracy, failure_type, comparison = self.judge.evaluate(
            question="What is total revenue?",
            expected_columns=["revenue"],
            expected_tables=["sales"],
            sql=None,
            actual_columns=[],
        )

        assert accuracy == AccuracyScore.FAILED
        assert failure_type == EvaluationFailureType.NO_SQL_GENERATED
        assert "No SQL was generated" in comparison.comparison_notes

    def test_model_endpoint_property(self) -> None:
        """Test model endpoint property returns correct value."""
        assert self.judge.model_endpoint == self.config.model_endpoint

        # Test with override
        judge_with_override = LLMJudgeEvaluator(self.config, model_override="custom-model")
        assert judge_with_override.model_endpoint == "custom-model"

    def test_llm_lazy_loading_mock_mode(self) -> None:
        """Test that LLM is not loaded in mock mode."""
        # In mock mode, llm property should return None
        assert self.judge.llm is None


class TestBenchmarkEvaluatorWithLLMJudge:
    """Tests for BenchmarkEvaluator with LLM judge enabled."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = Config(genie_space_id="test_space", mock_mode=True)
        self.benchmark_queries = [
            BenchmarkQuery(
                id="bm_001",
                question="What is total revenue?",
                query_type=QueryType.AGGREGATION,
                complexity=ComplexityLevel.SIMPLE,
                failure_category=FailureCategory.AMBIGUOUS_COLUMNS,
                expected_columns=["revenue"],
                expected_tables=["sales"],
            ),
            BenchmarkQuery(
                id="bm_002",
                question="Show sales by region",
                query_type=QueryType.AGGREGATION,
                complexity=ComplexityLevel.MODERATE,
                failure_category=FailureCategory.CRYPTIC_CODES,
                expected_columns=["region", "sales"],
                expected_tables=["sales"],
            ),
        ]

    def test_evaluator_without_judge(self) -> None:
        """Test evaluator defaults to string matching mode."""
        evaluator = BenchmarkEvaluator(self.config)
        assert evaluator.evaluation_mode == EvaluationMode.STRING_MATCH
        assert evaluator._use_llm_judge is False

    def test_evaluator_with_judge(self) -> None:
        """Test evaluator with LLM judge enabled."""
        evaluator = BenchmarkEvaluator(self.config, use_llm_judge=True)
        assert evaluator.evaluation_mode == EvaluationMode.LLM_JUDGE
        assert evaluator._use_llm_judge is True

    def test_llm_judge_lazy_loading(self) -> None:
        """Test that LLM judge is lazy-loaded."""
        evaluator = BenchmarkEvaluator(self.config, use_llm_judge=True)

        # Judge should not be loaded yet
        assert evaluator._llm_judge is None

        # Accessing property should load it
        judge = evaluator.llm_judge
        assert judge is not None
        assert isinstance(judge, LLMJudgeEvaluator)

    def test_run_benchmark_with_judge(self) -> None:
        """Test running benchmark with LLM judge."""
        evaluator = BenchmarkEvaluator(self.config, use_llm_judge=True)

        run = evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="baseline",
        )

        assert isinstance(run, BenchmarkRun)
        assert run.evaluation_mode == EvaluationMode.LLM_JUDGE
        assert run.judge_model is None  # Uses default model
        assert run.queries_evaluated == 2

        # Results should have LLM judge notes in comparison
        for result in run.results:
            assert "[Mock LLM Judge]" in result.comparison.comparison_notes

    def test_run_benchmark_with_judge_model_override(self) -> None:
        """Test running benchmark with custom judge model."""
        evaluator = BenchmarkEvaluator(
            self.config,
            use_llm_judge=True,
            judge_model="custom-judge-model",
        )

        run = evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="baseline",
        )

        assert run.evaluation_mode == EvaluationMode.LLM_JUDGE
        assert run.judge_model == "custom-judge-model"

    def test_benchmark_run_evaluation_mode_serialization(self) -> None:
        """Test that evaluation mode is properly serialized."""
        evaluator = BenchmarkEvaluator(self.config, use_llm_judge=True)

        run = evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="baseline",
        )

        # Serialize and deserialize
        data = run.to_dict()
        restored = BenchmarkRun.from_dict(data)

        assert restored.evaluation_mode == EvaluationMode.LLM_JUDGE
        assert data["evaluation_mode"] == "llm_judge"

    def test_benchmark_run_string_match_default(self) -> None:
        """Test that default evaluation mode is string_match."""
        evaluator = BenchmarkEvaluator(self.config)

        run = evaluator.run_benchmark(
            queries=self.benchmark_queries,
            run_type="baseline",
        )

        assert run.evaluation_mode == EvaluationMode.STRING_MATCH
        assert run.judge_model is None

    def test_empty_queries_with_judge(self) -> None:
        """Test handling empty query list with LLM judge enabled."""
        evaluator = BenchmarkEvaluator(self.config, use_llm_judge=True)

        run = evaluator.run_benchmark(
            queries=[],
            run_type="baseline",
        )

        assert run.queries_evaluated == 0
        assert run.evaluation_mode == EvaluationMode.LLM_JUDGE
