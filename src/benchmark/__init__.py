"""LLM-Powered Benchmark System for Genie Spaces."""

from .evaluator import BenchmarkEvaluator
from .llm_generator import LLMQueryGenerator
from .llm_judge import LLMJudgeEvaluator
from .models import (
    BenchmarkComparison,
    BenchmarkQuery,
    BenchmarkRun,
    EvaluationMode,
    GenerationSource,
    Severity,
)
from .progressive_reporter import ProgressiveReporter
from .reporter import BenchmarkReporter
from .schema_parser import (
    ColumnInfo,
    DomainContext,
    RelationshipInfo,
    SchemaParser,
    TableInfo,
)
from .suite import (
    TIER_COMPLEXITY_MAP,
    TIER_FAILURE_CATEGORIES,
    TIER_NAMES,
    SuiteGenerator,
    SuiteRunner,
    TierResult,
    TieredBenchmarkResult,
    TieredBenchmarkSuite,
    get_tier,
    group_by_tier,
)

__all__ = [
    # Evaluator
    "BenchmarkEvaluator",
    # LLM Generator
    "LLMQueryGenerator",
    # LLM Judge
    "LLMJudgeEvaluator",
    # Models
    "BenchmarkComparison",
    "BenchmarkQuery",
    "BenchmarkRun",
    "EvaluationMode",
    "GenerationSource",
    "Severity",
    # Reporter
    "BenchmarkReporter",
    # Progressive Reporter
    "ProgressiveReporter",
    # Schema parser
    "ColumnInfo",
    "DomainContext",
    "RelationshipInfo",
    "SchemaParser",
    "TableInfo",
    # Suite - Classes
    "SuiteGenerator",
    "SuiteRunner",
    "TierResult",
    "TieredBenchmarkResult",
    "TieredBenchmarkSuite",
    # Suite - Constants
    "TIER_NAMES",
    "TIER_COMPLEXITY_MAP",
    "TIER_FAILURE_CATEGORIES",
    # Suite - Functions
    "get_tier",
    "group_by_tier",
]
