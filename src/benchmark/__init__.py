"""LLM-Powered Benchmark System for Genie Spaces."""

from .evaluator import BenchmarkEvaluator
from .llm_client import LLMConfig, LLMResponse, UnifiedLLMClient, create_llm_client
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
from .data_aware_generator import DataAwareGenerator
from .data_profiler import ColumnProfile, DataProfile, DataProfiler
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
    # Data-Aware Generator
    "DataAwareGenerator",
    # Data Profiler
    "ColumnProfile",
    "DataProfile",
    "DataProfiler",
    # Evaluator
    "BenchmarkEvaluator",
    # LLM Client
    "LLMConfig",
    "LLMResponse",
    "UnifiedLLMClient",
    "create_llm_client",
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
