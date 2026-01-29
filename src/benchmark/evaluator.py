"""Benchmark evaluator with before/after comparison support.

This module provides the BenchmarkEvaluator class that wraps GenieEvaluator
and adds benchmark-specific functionality including comparison logic for
measuring the impact of Genie Space enhancements.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal, Optional

from .models import BenchmarkComparison, BenchmarkQuery, BenchmarkRun
from src.config import Config
from src.evaluation.evaluator import EvaluationResults, GenieEvaluator
from src.evaluation.models import EvaluationResult, EvaluationSummary, TestQuery


class BenchmarkEvaluator:
    """Evaluator with before/after comparison support.

    Wraps GenieEvaluator and adds benchmark-specific functionality for
    running controlled experiments to measure the impact of Genie Space
    improvements.

    The evaluator supports:
    - Running baseline benchmarks before enhancements
    - Running enhanced benchmarks after modifications
    - Comparing results to detect improvements and regressions
    - Saving/loading runs for reproducibility

    Example:
        >>> config = Config(genie_space_id="abc123", mock_mode=True)
        >>> evaluator = BenchmarkEvaluator(config)
        >>> baseline = evaluator.run_benchmark(queries, "baseline")
        >>> # ... make enhancements to Genie Space ...
        >>> enhanced = evaluator.run_benchmark(queries, "enhanced")
        >>> comparison = evaluator.compare_runs(baseline, enhanced)
        >>> print(f"Accuracy improved by {comparison.accuracy_delta:.1f}%")
    """

    def __init__(
        self,
        config: Config,
        genie_evaluator: Optional[GenieEvaluator] = None,
    ) -> None:
        """Initialize the benchmark evaluator.

        Args:
            config: Configuration instance with Genie settings
            genie_evaluator: Optional pre-configured GenieEvaluator instance.
                If not provided, one will be created lazily when needed.
        """
        self.config = config
        self._evaluator = genie_evaluator

    @property
    def evaluator(self) -> GenieEvaluator:
        """Lazy-load GenieEvaluator.

        Returns:
            The underlying GenieEvaluator instance
        """
        if self._evaluator is None:
            self._evaluator = GenieEvaluator(self.config)
        return self._evaluator

    def run_benchmark(
        self,
        queries: list[BenchmarkQuery],
        run_type: Literal["baseline", "enhanced"],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        fresh: bool = True,
    ) -> BenchmarkRun:
        """Execute a single benchmark run.

        Evaluates a list of benchmark queries against the configured Genie Space
        and captures results, timing, and configuration snapshot for
        reproducibility.

        Args:
            queries: Benchmark queries to evaluate
            run_type: Whether this is a "baseline" (before enhancements) or
                "enhanced" (after modifications) run
            progress_callback: Optional callback function that receives
                (current_index, total_count, message) for progress updates
            fresh: If True (default), bypass cache for each query to ensure
                fair comparison between runs. Set to False only if you want
                to measure cached performance.

        Returns:
            BenchmarkRun containing all evaluation results, summary statistics,
            and provenance information
        """
        if not queries:
            # Handle empty query list gracefully
            return BenchmarkRun(
                run_id=self._generate_run_id(),
                space_id=self.config.genie_space_id,
                run_type=run_type,
                queries_evaluated=0,
                results=[],
                summary=EvaluationSummary(total_queries=0),
                started_at=datetime.now().isoformat(),
                completed_at=datetime.now().isoformat(),
                config_snapshot=self._capture_config_snapshot(),
                provenance=self._build_provenance(queries),
            )

        started_at = datetime.now().isoformat()
        run_id = self._generate_run_id()

        # Convert BenchmarkQuery to TestQuery for the evaluator
        test_queries = [query.to_test_query() for query in queries]

        # Create a wrapper callback that adapts the signature
        # GenieEvaluator expects: (current, total, TestQuery)
        # We expose: (current, total, message)
        def adapted_callback(
            current: int, total: int, test_query: TestQuery
        ) -> None:
            if progress_callback:
                progress_callback(
                    current,
                    total,
                    f"Evaluating: {test_query.question[:50]}..."
                    if len(test_query.question) > 50
                    else f"Evaluating: {test_query.question}",
                )

        # Run evaluation using the wrapped GenieEvaluator
        eval_results: EvaluationResults = self.evaluator.evaluate(
            test_queries=test_queries,
            progress_callback=adapted_callback,
            fresh=fresh,
        )

        completed_at = datetime.now().isoformat()

        # Build provenance information
        provenance = self._build_provenance(queries)
        provenance["run_type"] = run_type
        provenance["fresh_mode"] = fresh
        provenance["evaluator_version"] = "1.0.0"

        # Build and return the BenchmarkRun
        return BenchmarkRun(
            run_id=run_id,
            space_id=self.config.genie_space_id,
            run_type=run_type,
            queries_evaluated=len(queries),
            results=eval_results.results if eval_results else [],
            summary=eval_results.summary if eval_results else None,
            started_at=started_at,
            completed_at=completed_at,
            config_snapshot=self._capture_config_snapshot(),
            provenance=provenance,
        )

    def compare_runs(
        self,
        baseline: BenchmarkRun,
        enhanced: BenchmarkRun,
    ) -> BenchmarkComparison:
        """Compare baseline and enhanced benchmark runs.

        Calculates improvement metrics, detects regressions, and provides
        detailed breakdown of changes by category.

        Args:
            baseline: The benchmark run before enhancements
            enhanced: The benchmark run after enhancements

        Returns:
            BenchmarkComparison with calculated metrics including:
            - Overall accuracy delta
            - Category-level improvements
            - Lists of improved, regressed, and unchanged queries
        """
        comparison = BenchmarkComparison(
            comparison_id=self._generate_comparison_id(),
            baseline=baseline,
            enhanced=enhanced,
        )
        comparison.calculate_metrics()
        return comparison

    def _generate_run_id(self) -> str:
        """Generate unique run identifier.

        Format: run_YYYYMMDD_HHMMSS_<8-char-hex>

        Returns:
            Unique identifier string for the benchmark run
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:8]
        return f"run_{timestamp}_{unique_suffix}"

    def _generate_comparison_id(self) -> str:
        """Generate unique comparison identifier.

        Format: cmp_YYYYMMDD_HHMMSS_<8-char-hex>

        Returns:
            Unique identifier string for the comparison
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:8]
        return f"cmp_{timestamp}_{unique_suffix}"

    def _capture_config_snapshot(self) -> dict[str, Any]:
        """Capture current config for reproducibility.

        Creates a snapshot of the relevant configuration settings at the
        time of the benchmark run.

        Returns:
            Dictionary containing configuration values relevant to benchmarking
        """
        return {
            "space_id": self.config.genie_space_id,
            "warehouse_id": self.config.warehouse_id,
            "model_endpoint": self.config.model_endpoint,
            "mock_mode": self.config.mock_mode,
            "databricks_host": self.config.databricks_host,
            "cache_enabled": self.config.cache_enabled,
            "cache_ttl_seconds": self.config.cache_ttl_seconds,
            "default_timeout_seconds": self.config.default_timeout_seconds,
        }

    def _build_provenance(self, queries: list[BenchmarkQuery]) -> dict[str, Any]:
        """Build provenance information for a benchmark run.

        Captures metadata about the queries being evaluated for traceability.

        Args:
            queries: The benchmark queries being evaluated

        Returns:
            Dictionary containing provenance metadata
        """
        if not queries:
            return {
                "total_queries": 0,
                "generated_at": datetime.now().isoformat(),
            }

        # Collect unique generation sources
        generation_sources = set()
        model_names = set()
        domains = set()
        schema_versions = set()

        for query in queries:
            generation_sources.add(query.generated_by)
            if query.model_name:
                model_names.add(query.model_name)
            if query.domain:
                domains.add(query.domain)
            if query.schema_version:
                schema_versions.add(query.schema_version)

        return {
            "total_queries": len(queries),
            "generation_sources": list(generation_sources),
            "model_names": list(model_names) if model_names else None,
            "domains": list(domains) if domains else None,
            "schema_versions": list(schema_versions) if schema_versions else None,
            "adversarial_count": sum(1 for q in queries if q.is_adversarial),
            "generated_at": datetime.now().isoformat(),
        }

    @staticmethod
    def save_run(run: BenchmarkRun, path: str | Path) -> None:
        """Save a benchmark run to JSON file.

        Creates parent directories if they don't exist.

        Args:
            run: The benchmark run to save
            path: File path for the JSON output

        Example:
            >>> evaluator.save_run(baseline, "benchmarks/baseline_2024.json")
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run.to_dict(), f, indent=2, default=str)

    @staticmethod
    def load_run(path: str | Path) -> BenchmarkRun:
        """Load a benchmark run from JSON file.

        Args:
            path: File path to the JSON benchmark run

        Returns:
            BenchmarkRun instance reconstructed from the file

        Raises:
            FileNotFoundError: If the specified file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            KeyError: If required fields are missing from the JSON
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BenchmarkRun.from_dict(data)

    @staticmethod
    def save_comparison(comparison: BenchmarkComparison, path: str | Path) -> None:
        """Save a benchmark comparison to JSON file.

        Creates parent directories if they don't exist.

        Args:
            comparison: The benchmark comparison to save
            path: File path for the JSON output

        Example:
            >>> evaluator.save_comparison(comp, "benchmarks/comparison_2024.json")
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(comparison.to_dict(), f, indent=2, default=str)

    @staticmethod
    def load_comparison(path: str | Path) -> BenchmarkComparison:
        """Load a benchmark comparison from JSON file.

        Args:
            path: File path to the JSON benchmark comparison

        Returns:
            BenchmarkComparison instance reconstructed from the file

        Raises:
            FileNotFoundError: If the specified file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            KeyError: If required fields are missing from the JSON
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BenchmarkComparison.from_dict(data)
