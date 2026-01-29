"""Progressive difficulty benchmark suite generation and execution.

This module provides classes for generating and running 5-tier progressive
difficulty benchmark suites. Tiers are:
- Tier 1 (Simple): Basic single-table queries
- Tier 2 (Moderate): 2-table joins with GROUP BY
- Tier 3 (Complex): 3+ table joins, subqueries, CTEs
- Tier 4 (Expert): Window functions, advanced analytics
- Tier 5 (Adversarial): Trick questions that should be refused
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

from src.config import Config
from src.evaluation.models import ComplexityLevel, EvaluationResult, FailureCategory

from .evaluator import BenchmarkEvaluator
from .llm_generator import LLMQueryGenerator
from .models import BenchmarkQuery, EvaluationMode

logger = logging.getLogger(__name__)


# =============================================================================
# TIER DEFINITIONS
# =============================================================================

TIER_NAMES: dict[int, str] = {
    1: "Simple",
    2: "Moderate",
    3: "Complex",
    4: "Expert",
    5: "Adversarial",
}

TIER_COMPLEXITY_MAP: dict[int, ComplexityLevel] = {
    1: ComplexityLevel.SIMPLE,
    2: ComplexityLevel.MODERATE,
    3: ComplexityLevel.COMPLEX,
    4: ComplexityLevel.EXPERT,
    5: ComplexityLevel.SIMPLE,  # Adversarial uses SIMPLE + is_adversarial=True
}

TIER_FAILURE_CATEGORIES: dict[int, list[FailureCategory]] = {
    1: [FailureCategory.AMBIGUOUS_COLUMNS, FailureCategory.CRYPTIC_CODES],
    2: [FailureCategory.TEMPORAL_CONFUSION, FailureCategory.AGGREGATION_AMBIGUITY],
    3: [FailureCategory.JOIN_COMPLEXITY, FailureCategory.BUSINESS_LOGIC],
    4: [FailureCategory.JOIN_COMPLEXITY, FailureCategory.BUSINESS_LOGIC],
    5: [FailureCategory.TRICK_QUESTIONS],
}


# =============================================================================
# TIER DERIVATION FUNCTIONS
# =============================================================================


def get_tier(query: BenchmarkQuery) -> int:
    """Derive tier from query complexity and is_adversarial flag.

    Args:
        query: The benchmark query to classify

    Returns:
        Tier number (1-5)
    """
    if query.is_adversarial or query.failure_category == FailureCategory.TRICK_QUESTIONS:
        return 5
    return {
        ComplexityLevel.SIMPLE: 1,
        ComplexityLevel.MODERATE: 2,
        ComplexityLevel.COMPLEX: 3,
        ComplexityLevel.EXPERT: 4,
    }.get(query.complexity, 1)


def group_by_tier(queries: list[BenchmarkQuery]) -> dict[int, list[BenchmarkQuery]]:
    """Group queries by their derived tier.

    Args:
        queries: List of benchmark queries

    Returns:
        Dictionary mapping tier number to list of queries
    """
    grouped: dict[int, list[BenchmarkQuery]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    for q in queries:
        tier = get_tier(q)
        grouped[tier].append(q)
    return grouped


# =============================================================================
# TIER RESULT MODEL
# =============================================================================


@dataclass
class TierResult:
    """Results for a single tier in a benchmark run.

    Attributes:
        tier: Tier number (1-5)
        tier_name: Human-readable tier name
        queries_count: Number of queries in this tier
        correct_count: Number of correct results
        partial_count: Number of partial results
        wrong_count: Number of wrong results
        failed_count: Number of failed results
        accuracy: Accuracy percentage (0-100)
        results: Individual evaluation results
    """

    tier: int
    tier_name: str
    queries_count: int
    correct_count: int = 0
    partial_count: int = 0
    wrong_count: int = 0
    failed_count: int = 0
    accuracy: float = 0.0
    results: list[EvaluationResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate accuracy after initialization."""
        if self.queries_count > 0:
            self.accuracy = (self.correct_count / self.queries_count) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "tier": self.tier,
            "tier_name": self.tier_name,
            "queries_count": self.queries_count,
            "correct_count": self.correct_count,
            "partial_count": self.partial_count,
            "wrong_count": self.wrong_count,
            "failed_count": self.failed_count,
            "accuracy": self.accuracy,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TierResult:
        """Create from dictionary.

        Args:
            data: Dictionary containing tier result data

        Returns:
            TierResult instance
        """
        return cls(
            tier=data["tier"],
            tier_name=data["tier_name"],
            queries_count=data["queries_count"],
            correct_count=data.get("correct_count", 0),
            partial_count=data.get("partial_count", 0),
            wrong_count=data.get("wrong_count", 0),
            failed_count=data.get("failed_count", 0),
            accuracy=data.get("accuracy", 0.0),
            results=[EvaluationResult.from_dict(r) for r in data.get("results", [])],
        )


# =============================================================================
# TIERED BENCHMARK SUITE MODEL
# =============================================================================


@dataclass
class TieredBenchmarkSuite:
    """A 5-tier progressive difficulty benchmark suite.

    Attributes:
        suite_id: Unique identifier for this suite
        domain_name: Domain this suite targets
        schema_version: Schema version hash
        tiers: Dictionary mapping tier number to list of queries
        total_queries: Total number of queries across all tiers
        queries_per_tier: Target number of queries per tier
        created_at: When the suite was created
        provenance: Additional metadata about suite generation
    """

    suite_id: str
    domain_name: str
    schema_version: str
    tiers: dict[int, list[BenchmarkQuery]] = field(default_factory=dict)
    total_queries: int = 0
    queries_per_tier: int = 20
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure tiers dict has all tier keys."""
        for tier in range(1, 6):
            if tier not in self.tiers:
                self.tiers[tier] = []
        self.total_queries = sum(len(queries) for queries in self.tiers.values())

    def get_all_queries(self) -> list[BenchmarkQuery]:
        """Get all queries from all tiers.

        Returns:
            Flat list of all queries
        """
        queries: list[BenchmarkQuery] = []
        for tier in range(1, 6):
            queries.extend(self.tiers.get(tier, []))
        return queries

    def get_tier_queries(self, tier: int) -> list[BenchmarkQuery]:
        """Get queries for a specific tier.

        Args:
            tier: Tier number (1-5)

        Returns:
            List of queries for that tier
        """
        return self.tiers.get(tier, [])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "suite_id": self.suite_id,
            "domain_name": self.domain_name,
            "schema_version": self.schema_version,
            "tiers": {str(tier): [q.to_dict() for q in queries] for tier, queries in self.tiers.items()},
            "total_queries": self.total_queries,
            "queries_per_tier": self.queries_per_tier,
            "created_at": self.created_at,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TieredBenchmarkSuite:
        """Create from dictionary.

        Args:
            data: Dictionary containing suite data

        Returns:
            TieredBenchmarkSuite instance
        """
        tiers: dict[int, list[BenchmarkQuery]] = {}
        tiers_data = data.get("tiers", {})
        for tier_str, queries_data in tiers_data.items():
            tier = int(tier_str)
            tiers[tier] = [BenchmarkQuery.from_dict(q) for q in queries_data]

        return cls(
            suite_id=data["suite_id"],
            domain_name=data["domain_name"],
            schema_version=data["schema_version"],
            tiers=tiers,
            total_queries=data.get("total_queries", 0),
            queries_per_tier=data.get("queries_per_tier", 20),
            created_at=data.get("created_at", ""),
            provenance=data.get("provenance", {}),
        )


# =============================================================================
# TIERED BENCHMARK RESULT MODEL
# =============================================================================


@dataclass
class TieredBenchmarkResult:
    """Results from running a tiered benchmark suite.

    Attributes:
        result_id: Unique identifier for this result
        suite_id: ID of the suite that was run
        space_id: Genie Space ID that was evaluated
        run_type: Whether this is baseline or enhanced
        tier_results: Results by tier
        overall_accuracy: Overall accuracy across all tiers
        capability_score: Average accuracy for tiers 1-4 (capability)
        safety_score: Accuracy for tier 5 (adversarial safety)
        total_queries: Total queries evaluated
        evaluation_mode: Evaluation mode used
        judge_model: Judge model if LLM judge was used
        started_at: When the run started
        completed_at: When the run completed
        provenance: Additional metadata
    """

    result_id: str
    suite_id: str
    space_id: str
    run_type: Literal["baseline", "enhanced"]
    tier_results: dict[int, TierResult] = field(default_factory=dict)
    overall_accuracy: float = 0.0
    capability_score: float = 0.0
    safety_score: float = 0.0
    total_queries: int = 0
    evaluation_mode: EvaluationMode = EvaluationMode.STRING_MATCH
    judge_model: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure tier_results has all tier keys."""
        for tier in range(1, 6):
            if tier not in self.tier_results:
                self.tier_results[tier] = TierResult(
                    tier=tier,
                    tier_name=TIER_NAMES.get(tier, f"Tier {tier}"),
                    queries_count=0,
                )

    def calculate_scores(self) -> None:
        """Calculate overall, capability, and safety scores from tier results."""
        # Calculate total queries
        self.total_queries = sum(tr.queries_count for tr in self.tier_results.values())

        if self.total_queries == 0:
            self.overall_accuracy = 0.0
            self.capability_score = 0.0
            self.safety_score = 0.0
            return

        # Overall accuracy: all correct across all tiers
        total_correct = sum(tr.correct_count for tr in self.tier_results.values())
        self.overall_accuracy = (total_correct / self.total_queries) * 100

        # Capability score: average of tiers 1-4
        capability_tiers = [self.tier_results[t] for t in range(1, 5) if self.tier_results[t].queries_count > 0]
        if capability_tiers:
            self.capability_score = sum(tr.accuracy for tr in capability_tiers) / len(capability_tiers)
        else:
            self.capability_score = 0.0

        # Safety score: tier 5 accuracy
        if self.tier_results[5].queries_count > 0:
            self.safety_score = self.tier_results[5].accuracy
        else:
            self.safety_score = 0.0

    def get_tier_result(self, tier: int) -> TierResult:
        """Get results for a specific tier.

        Args:
            tier: Tier number (1-5)

        Returns:
            TierResult for that tier
        """
        return self.tier_results.get(
            tier,
            TierResult(tier=tier, tier_name=TIER_NAMES.get(tier, f"Tier {tier}"), queries_count=0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "result_id": self.result_id,
            "suite_id": self.suite_id,
            "space_id": self.space_id,
            "run_type": self.run_type,
            "tier_results": {str(tier): tr.to_dict() for tier, tr in self.tier_results.items()},
            "overall_accuracy": self.overall_accuracy,
            "capability_score": self.capability_score,
            "safety_score": self.safety_score,
            "total_queries": self.total_queries,
            "evaluation_mode": self.evaluation_mode.value,
            "judge_model": self.judge_model,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TieredBenchmarkResult:
        """Create from dictionary.

        Args:
            data: Dictionary containing result data

        Returns:
            TieredBenchmarkResult instance
        """
        tier_results: dict[int, TierResult] = {}
        tier_results_data = data.get("tier_results", {})
        for tier_str, tr_data in tier_results_data.items():
            tier = int(tier_str)
            tier_results[tier] = TierResult.from_dict(tr_data)

        eval_mode_str = data.get("evaluation_mode", "string_match")
        evaluation_mode = EvaluationMode(eval_mode_str)

        return cls(
            result_id=data["result_id"],
            suite_id=data["suite_id"],
            space_id=data["space_id"],
            run_type=data["run_type"],
            tier_results=tier_results,
            overall_accuracy=data.get("overall_accuracy", 0.0),
            capability_score=data.get("capability_score", 0.0),
            safety_score=data.get("safety_score", 0.0),
            total_queries=data.get("total_queries", 0),
            evaluation_mode=evaluation_mode,
            judge_model=data.get("judge_model"),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            provenance=data.get("provenance", {}),
        )


# =============================================================================
# SUITE GENERATOR
# =============================================================================


class SuiteGenerator:
    """Generate progressive difficulty benchmark suites.

    Uses LLMQueryGenerator to create queries for each tier based on
    complexity levels and failure categories.

    Example:
        >>> config = Config.from_env()
        >>> generator = SuiteGenerator(config, schema_path)
        >>> suite = generator.generate(queries_per_tier=20)
        >>> generator.save_suite(suite, "benchmarks/velocity_motors")
    """

    def __init__(
        self,
        config: Config,
        schema_path: str | Path,
    ) -> None:
        """Initialize the suite generator.

        Args:
            config: Configuration instance
            schema_path: Path to YAML schema file
        """
        self.config = config
        self.schema_path = Path(schema_path)
        self._llm_generator: LLMQueryGenerator | None = None
        self._domain_context = None
        self._schema_version = ""

    @property
    def llm_generator(self) -> LLMQueryGenerator:
        """Lazy-load LLMQueryGenerator.

        Returns:
            LLMQueryGenerator instance
        """
        if self._llm_generator is None:
            self._llm_generator = LLMQueryGenerator(self.config)
        return self._llm_generator

    @property
    def domain_context(self):
        """Lazy-load domain context from schema.

        Returns:
            DomainContext from parsed schema
        """
        if self._domain_context is None:
            from .schema_parser import SchemaParser

            parser = SchemaParser(self.schema_path)
            self._domain_context = parser.parse()
            self._schema_version = parser.get_schema_hash()
        return self._domain_context

    @property
    def schema_version(self) -> str:
        """Get schema version hash.

        Returns:
            Schema version hash string
        """
        if not self._schema_version:
            # Trigger lazy load
            _ = self.domain_context
        return self._schema_version

    def generate(
        self,
        queries_per_tier: int = 20,
        tiers: list[int] | None = None,
        seed: int | None = None,
    ) -> TieredBenchmarkSuite:
        """Generate a tiered benchmark suite.

        Args:
            queries_per_tier: Number of queries to generate per tier
            tiers: List of tiers to generate (default: all 1-5)
            seed: Random seed for reproducibility

        Returns:
            TieredBenchmarkSuite with generated queries
        """
        tiers_to_generate = tiers or [1, 2, 3, 4, 5]
        suite_id = f"suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info(f"Generating suite {suite_id}")
        logger.info(f"Domain: {self.domain_context.domain_name}")
        logger.info(f"Tiers: {tiers_to_generate}")
        logger.info(f"Queries per tier: {queries_per_tier}")

        all_queries: dict[int, list[BenchmarkQuery]] = {}

        for tier in tiers_to_generate:
            logger.info(f"Generating Tier {tier} ({TIER_NAMES.get(tier, '')})")

            complexity = TIER_COMPLEXITY_MAP.get(tier, ComplexityLevel.SIMPLE)
            failure_categories = TIER_FAILURE_CATEGORIES.get(tier, [FailureCategory.AMBIGUOUS_COLUMNS])

            # For tier 5, we need adversarial queries
            if tier == 5:
                # Generate adversarial queries using TRICK_QUESTIONS category
                queries = self.llm_generator.generate(
                    domain_context=self.domain_context,
                    failure_categories=[FailureCategory.TRICK_QUESTIONS],
                    complexity_tiers=[ComplexityLevel.SIMPLE],  # Adversarial can be any complexity
                    queries_per_category=queries_per_tier,
                    seed=seed,
                    schema_version=self.schema_version,
                )
                # Ensure is_adversarial flag is set
                for q in queries:
                    q.is_adversarial = True
            else:
                # Generate queries for capability tiers
                # Distribute queries across failure categories for this tier
                queries_per_category = max(1, queries_per_tier // len(failure_categories))
                queries = self.llm_generator.generate(
                    domain_context=self.domain_context,
                    failure_categories=failure_categories,
                    complexity_tiers=[complexity],
                    queries_per_category=queries_per_category,
                    seed=seed,
                    schema_version=self.schema_version,
                )

            all_queries[tier] = queries[:queries_per_tier]  # Cap at requested count
            logger.info(f"  Generated {len(all_queries[tier])} queries for Tier {tier}")

        # Build provenance
        provenance = {
            "generator": "SuiteGenerator",
            "model_endpoint": self.config.model_endpoint,
            "mock_mode": self.config.mock_mode,
            "seed": seed,
            "schema_path": str(self.schema_path),
        }

        suite = TieredBenchmarkSuite(
            suite_id=suite_id,
            domain_name=self.domain_context.domain_name,
            schema_version=self.schema_version,
            tiers=all_queries,
            queries_per_tier=queries_per_tier,
            provenance=provenance,
        )

        logger.info(f"Suite generated: {suite.total_queries} total queries")
        return suite

    def save_suite(
        self,
        suite: TieredBenchmarkSuite,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        """Save suite to files.

        Creates:
        - Individual tier files: tier_1.json, tier_2.json, etc.
        - Full suite file: full_suite.json

        Args:
            suite: The suite to save
            output_dir: Output directory

        Returns:
            Dictionary mapping file type to path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files: dict[str, Path] = {}

        # Save individual tier files
        for tier in range(1, 6):
            tier_queries = suite.tiers.get(tier, [])
            if tier_queries:
                tier_file = output_path / f"tier_{tier}.json"
                tier_data = {
                    "tier": tier,
                    "tier_name": TIER_NAMES.get(tier, f"Tier {tier}"),
                    "suite_id": suite.suite_id,
                    "queries_count": len(tier_queries),
                    "queries": [q.to_dict() for q in tier_queries],
                }
                with open(tier_file, "w", encoding="utf-8") as f:
                    json.dump(tier_data, f, indent=2, ensure_ascii=False)
                saved_files[f"tier_{tier}"] = tier_file
                logger.info(f"Saved tier {tier}: {tier_file}")

        # Save full suite
        full_suite_file = output_path / "full_suite.json"
        with open(full_suite_file, "w", encoding="utf-8") as f:
            json.dump(suite.to_dict(), f, indent=2, ensure_ascii=False)
        saved_files["full_suite"] = full_suite_file
        logger.info(f"Saved full suite: {full_suite_file}")

        return saved_files

    @classmethod
    def load_suite(cls, suite_path: str | Path) -> TieredBenchmarkSuite:
        """Load a suite from JSON file.

        Args:
            suite_path: Path to full_suite.json file

        Returns:
            TieredBenchmarkSuite instance
        """
        with open(suite_path, encoding="utf-8") as f:
            data = json.load(f)
        return TieredBenchmarkSuite.from_dict(data)


# =============================================================================
# SUITE RUNNER
# =============================================================================


# Progress callback type: (tier, current_query, total_queries, message)
ProgressCallback = Callable[[int, int, int, str], None]


class SuiteRunner:
    """Execute tiered benchmark suites against Genie Spaces.

    Runs each tier sequentially and aggregates results into a
    TieredBenchmarkResult.

    Example:
        >>> config = Config.from_env()
        >>> runner = SuiteRunner(config)
        >>> result = runner.run(suite, run_type="baseline")
        >>> runner.save_result(result, "results/baseline_result.json")
    """

    def __init__(
        self,
        config: Config,
        use_llm_judge: bool = False,
        judge_model: str | None = None,
    ) -> None:
        """Initialize the suite runner.

        Args:
            config: Configuration instance
            use_llm_judge: Whether to use LLM-as-judge evaluation
            judge_model: Optional override for judge model endpoint
        """
        self.config = config
        self._use_llm_judge = use_llm_judge
        self._judge_model = judge_model
        self._evaluator: BenchmarkEvaluator | None = None

    @property
    def evaluator(self) -> BenchmarkEvaluator:
        """Lazy-load BenchmarkEvaluator.

        Returns:
            BenchmarkEvaluator instance
        """
        if self._evaluator is None:
            self._evaluator = BenchmarkEvaluator(
                self.config,
                use_llm_judge=self._use_llm_judge,
                judge_model=self._judge_model,
            )
        return self._evaluator

    def run(
        self,
        suite: TieredBenchmarkSuite,
        run_type: Literal["baseline", "enhanced"] = "baseline",
        tiers: list[int] | None = None,
        progress_callback: ProgressCallback | None = None,
        stop_on_zero_accuracy: bool = False,
    ) -> TieredBenchmarkResult:
        """Run the benchmark suite.

        Args:
            suite: The suite to run
            run_type: Whether this is baseline or enhanced run
            tiers: Specific tiers to run (default: all with queries)
            progress_callback: Optional callback (tier, current, total, message)
            stop_on_zero_accuracy: Stop if a tier has 0% accuracy

        Returns:
            TieredBenchmarkResult with all tier results
        """
        result_id = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now().isoformat()

        logger.info(f"Starting suite run: {result_id}")
        logger.info(f"Suite: {suite.suite_id}")
        logger.info(f"Run type: {run_type}")

        # Determine tiers to run
        tiers_to_run = tiers or [t for t in range(1, 6) if suite.tiers.get(t)]

        tier_results: dict[int, TierResult] = {}
        evaluation_mode = self.evaluator.evaluation_mode

        for tier in tiers_to_run:
            tier_queries = suite.get_tier_queries(tier)

            if not tier_queries:
                logger.info(f"Tier {tier}: No queries, skipping")
                tier_results[tier] = TierResult(
                    tier=tier,
                    tier_name=TIER_NAMES.get(tier, f"Tier {tier}"),
                    queries_count=0,
                )
                continue

            logger.info(f"Running Tier {tier} ({TIER_NAMES.get(tier, '')}): {len(tier_queries)} queries")

            # Create progress wrapper
            def tier_progress(current: int, total: int, message: str) -> None:
                if progress_callback:
                    progress_callback(tier, current, total, message)

            # Run benchmark for this tier
            tier_run = self.evaluator.run_benchmark(
                queries=tier_queries,
                run_type=run_type,
                progress_callback=tier_progress,
            )

            # Build tier result
            tier_result = TierResult(
                tier=tier,
                tier_name=TIER_NAMES.get(tier, f"Tier {tier}"),
                queries_count=len(tier_queries),
                correct_count=tier_run.summary.correct_count if tier_run.summary else 0,
                partial_count=tier_run.summary.partial_count if tier_run.summary else 0,
                wrong_count=tier_run.summary.wrong_count if tier_run.summary else 0,
                failed_count=tier_run.summary.failed_count if tier_run.summary else 0,
                results=tier_run.results,
            )
            tier_results[tier] = tier_result

            logger.info(f"Tier {tier} accuracy: {tier_result.accuracy:.1f}%")

            # Check for early stop
            if stop_on_zero_accuracy and tier_result.accuracy == 0.0 and tier_result.queries_count > 0:
                logger.warning(f"Tier {tier} has 0% accuracy, stopping early")
                break

        completed_at = datetime.now().isoformat()

        # Build result
        result = TieredBenchmarkResult(
            result_id=result_id,
            suite_id=suite.suite_id,
            space_id=self.config.genie_space_id,
            run_type=run_type,
            tier_results=tier_results,
            evaluation_mode=evaluation_mode,
            judge_model=self._judge_model if self._use_llm_judge else None,
            started_at=started_at,
            completed_at=completed_at,
            provenance={
                "suite_domain": suite.domain_name,
                "schema_version": suite.schema_version,
                "tiers_run": tiers_to_run,
                "stop_on_zero_accuracy": stop_on_zero_accuracy,
            },
        )

        # Calculate aggregate scores
        result.calculate_scores()

        logger.info(f"Suite run complete: {result_id}")
        logger.info(f"Overall accuracy: {result.overall_accuracy:.1f}%")
        logger.info(f"Capability score: {result.capability_score:.1f}%")
        logger.info(f"Safety score: {result.safety_score:.1f}%")

        return result

    @staticmethod
    def save_result(result: TieredBenchmarkResult, path: str | Path) -> None:
        """Save a result to JSON file.

        Args:
            result: The result to save
            path: Output file path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        logger.info(f"Saved result to: {path}")

    @staticmethod
    def load_result(path: str | Path) -> TieredBenchmarkResult:
        """Load a result from JSON file.

        Args:
            path: Path to result JSON file

        Returns:
            TieredBenchmarkResult instance
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return TieredBenchmarkResult.from_dict(data)
