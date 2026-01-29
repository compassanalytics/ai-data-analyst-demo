#!/usr/bin/env python
"""Benchmark CLI Script.

LLM-powered benchmark system for Genie Spaces. Generates domain-specific test
queries, runs before/after evaluations, and produces comparison reports.

Usage:
    uv run python scripts/benchmark.py generate --schema PATH --output PATH
    uv run python scripts/benchmark.py run --queries PATH --space-id ID [--baseline|--compare-to PATH]
    uv run python scripts/benchmark.py report --baseline PATH --enhanced PATH --output PATH
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmark import (
    BenchmarkEvaluator,
    BenchmarkReporter,
    LLMQueryGenerator,
    SchemaParser,
)
from src.config import Config
from src.evaluation.models import ComplexityLevel, FailureCategory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="LLM-powered benchmark system for Genie Spaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate benchmark queries from schema
  uv run python scripts/benchmark.py generate \\
    --schema infra/configs/velocity_motors/sales_analytics.yaml \\
    --output benchmarks/velocity_motors_sales.json \\
    --queries-per-category 5

  # Run baseline benchmark
  uv run python scripts/benchmark.py run \\
    --queries benchmarks/velocity_motors_sales.json \\
    --space-id $GENIE_SPACE_ID \\
    --baseline \\
    --output-dir results/

  # Run enhanced benchmark and compare
  uv run python scripts/benchmark.py run \\
    --queries benchmarks/velocity_motors_sales.json \\
    --space-id $GENIE_SPACE_ID \\
    --compare-to results/baseline_run.json \\
    --output-dir results/

  # Run with LLM-as-Judge semantic evaluation
  uv run python scripts/benchmark.py run \\
    --queries benchmarks/velocity_motors_sales.json \\
    --baseline \\
    --judge \\
    --output-dir results/

  # Generate comparison report
  uv run python scripts/benchmark.py report \\
    --baseline results/baseline_run.json \\
    --enhanced results/enhanced_run.json \\
    --output reports/
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # =========================================================================
    # Generate subcommand
    # =========================================================================
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate benchmark queries from a schema",
        description="Generate domain-specific test queries using LLM based on YAML schema config.",
    )
    gen_parser.add_argument(
        "--schema",
        required=True,
        help="Path to YAML schema config file",
    )
    gen_parser.add_argument(
        "--output",
        required=True,
        help="Output path for generated queries JSON",
    )
    gen_parser.add_argument(
        "--queries-per-category",
        type=int,
        default=5,
        help="Number of queries to generate per failure category (default: 5)",
    )
    gen_parser.add_argument(
        "--failure-categories",
        help="Comma-separated list of failure categories (default: all)",
    )
    gen_parser.add_argument(
        "--complexity-tier",
        help="Comma-separated list of complexity tiers (default: all). Valid: simple,moderate,complex,expert",
    )
    gen_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM for testing (no API calls)",
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility",
    )

    # =========================================================================
    # Run subcommand
    # =========================================================================
    run_parser = subparsers.add_parser(
        "run",
        help="Run benchmark evaluation",
        description="Execute benchmark queries against a Genie Space and optionally compare to baseline.",
    )
    run_parser.add_argument(
        "--queries",
        required=True,
        help="Path to benchmark queries JSON file",
    )
    run_parser.add_argument(
        "--space-id",
        help="Genie Space ID (overrides GENIE_SPACE_ID env var)",
    )
    run_parser.add_argument(
        "--baseline",
        action="store_true",
        help="Mark this as a baseline run",
    )
    run_parser.add_argument(
        "--compare-to",
        help="Path to baseline run JSON for comparison",
    )
    run_parser.add_argument(
        "--output-dir",
        default="results",
        help="Output directory for results (default: results/)",
    )
    run_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock mode for testing",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of queries to evaluate",
    )
    run_parser.add_argument(
        "--judge",
        action="store_true",
        help="Use LLM-as-Judge for semantic evaluation (default: string matching)",
    )
    run_parser.add_argument(
        "--judge-model",
        help="Model endpoint for LLM judge (default: config.model_endpoint)",
    )
    run_parser.add_argument(
        "--complexity-tier",
        help="Filter queries by complexity tier (comma-separated). Valid: simple,moderate,complex,expert",
    )

    # =========================================================================
    # Report subcommand
    # =========================================================================
    report_parser = subparsers.add_parser(
        "report",
        help="Generate comparison report",
        description="Generate comparison report from baseline and enhanced benchmark runs.",
    )
    report_parser.add_argument(
        "--baseline",
        required=True,
        help="Path to baseline run JSON",
    )
    report_parser.add_argument(
        "--enhanced",
        required=True,
        help="Path to enhanced run JSON",
    )
    report_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for reports",
    )
    report_parser.add_argument(
        "--formats",
        default="md,html,json",
        help="Comma-separated output formats (default: md,html,json)",
    )
    report_parser.add_argument(
        "--title",
        help="Report title",
    )

    return parser


def cmd_generate(args: argparse.Namespace) -> int:
    """Handle generate subcommand."""
    logger.info(f"Generating benchmark queries from schema: {args.schema}")

    # Parse schema
    parser = SchemaParser(args.schema)
    try:
        domain_context = parser.parse()
        schema_version = parser.get_schema_hash()
    except Exception as e:
        logger.error(f"Failed to parse schema: {e}")
        return 1

    logger.info(f"Parsed schema: {domain_context.domain_name}")
    logger.info(f"  Tables: {len(domain_context.tables)}")
    logger.info(f"  Relationships: {len(domain_context.relationships)}")
    logger.info(f"  Business rules: {len(domain_context.business_rules)}")
    logger.info(f"  Schema version: {schema_version[:12]}...")

    # Parse failure categories
    failure_categories: list[FailureCategory] | None = None
    if args.failure_categories:
        category_names = [c.strip() for c in args.failure_categories.split(",")]
        try:
            failure_categories = [FailureCategory(name) for name in category_names]
        except ValueError as e:
            logger.error(f"Invalid failure category: {e}")
            logger.info(f"Valid categories: {[c.value for c in FailureCategory]}")
            return 1

    # Parse complexity tiers
    complexity_tiers: list[ComplexityLevel] | None = None
    if args.complexity_tier:
        tier_names = [t.strip().lower() for t in args.complexity_tier.split(",")]
        try:
            complexity_tiers = [ComplexityLevel(name) for name in tier_names]
        except ValueError as e:
            logger.error(f"Invalid complexity tier: {e}")
            logger.info(f"Valid tiers: {[c.value for c in ComplexityLevel]}")
            return 1

    # Create config
    config = Config.from_env()
    if args.mock:
        config.mock_mode = True

    # Generate queries
    generator = LLMQueryGenerator(config)
    try:
        queries = generator.generate(
            domain_context=domain_context,
            failure_categories=failure_categories,
            complexity_tiers=complexity_tiers,
            queries_per_category=args.queries_per_category,
            schema_version=schema_version,
            seed=args.seed,
        )
    except Exception as e:
        logger.error(f"Failed to generate queries: {e}")
        return 1

    logger.info(f"Generated {len(queries)} queries")

    # Save queries
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generator.save_queries(queries, output_path)
    logger.info(f"Saved queries to: {output_path}")

    # Print summary
    category_counts: dict[str, int] = {}
    for q in queries:
        cat = q.failure_category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("\n" + "=" * 60)
    print("BENCHMARK QUERIES GENERATED")
    print("=" * 60)
    print(f"Output: {output_path}")
    print(f"Total queries: {len(queries)}")
    print("\nBy failure category:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")
    print("=" * 60)

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Handle run subcommand."""
    logger.info(f"Running benchmark with queries: {args.queries}")

    # Load queries
    try:
        queries = LLMQueryGenerator.load_queries(args.queries)
    except Exception as e:
        logger.error(f"Failed to load queries: {e}")
        return 1

    if args.limit:
        queries = queries[: args.limit]
        logger.info(f"Limited to {len(queries)} queries")

    # Filter by complexity tier if specified
    if args.complexity_tier:
        tier_names = [t.strip().lower() for t in args.complexity_tier.split(",")]
        try:
            complexity_tiers = [ComplexityLevel(name) for name in tier_names]
            queries = [q for q in queries if q.complexity in complexity_tiers]
            logger.info(f"Filtered to {len(queries)} queries matching complexity tiers: {tier_names}")
        except ValueError as e:
            logger.error(f"Invalid complexity tier: {e}")
            logger.info(f"Valid tiers: {[c.value for c in ComplexityLevel]}")
            return 1

    logger.info(f"Loaded {len(queries)} benchmark queries")

    # Create config
    config = Config.from_env()
    if args.mock:
        config.mock_mode = True
    if args.space_id:
        config.genie_space_id = args.space_id

    # Determine run type
    run_type = "baseline" if args.baseline else "enhanced"
    logger.info(f"Run type: {run_type}")

    # Determine evaluation mode
    use_llm_judge = getattr(args, "judge", False)
    judge_model = getattr(args, "judge_model", None)
    if use_llm_judge:
        logger.info("Evaluation mode: LLM Judge (semantic evaluation)")
        if judge_model:
            logger.info(f"Judge model: {judge_model}")
    else:
        logger.info("Evaluation mode: String matching")

    # Create evaluator and run
    evaluator = BenchmarkEvaluator(
        config,
        use_llm_judge=use_llm_judge,
        judge_model=judge_model,
    )

    def progress_callback(current: int, total: int, message: str) -> None:
        print(f"  [{current}/{total}] {message}", flush=True)

    try:
        run = evaluator.run_benchmark(
            queries=queries,
            run_type=run_type,
            progress_callback=progress_callback,
        )
    except Exception as e:
        logger.error(f"Benchmark run failed: {e}")
        return 1

    # Save run
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / f"{run_type}_run.json"
    evaluator.save_run(run, run_path)
    logger.info(f"Saved run to: {run_path}")

    # Print summary
    print("\n" + "=" * 60)
    print(f"BENCHMARK RUN COMPLETE ({run_type.upper()})")
    print("=" * 60)
    print(f"Run ID: {run.run_id}")
    print(f"Space ID: {run.space_id}")
    print(f"Evaluation mode: {run.evaluation_mode.value}")
    if run.judge_model:
        print(f"Judge model: {run.judge_model}")
    print(f"Queries: {run.queries_evaluated}")
    print(f"Overall accuracy: {run.summary.overall_accuracy:.1f}%")
    print(f"  Correct: {run.summary.correct_count}")
    print(f"  Partial: {run.summary.partial_count}")
    print(f"  Wrong: {run.summary.wrong_count}")
    print(f"  Failed: {run.summary.failed_count}")
    print(f"Output: {run_path}")
    print("=" * 60)

    # Compare if requested
    if args.compare_to:
        logger.info(f"Comparing to baseline: {args.compare_to}")
        try:
            baseline = evaluator.load_run(args.compare_to)
            comparison = evaluator.compare_runs(baseline, run)

            # Save comparison
            comparison_path = output_dir / "comparison.json"
            evaluator.save_comparison(comparison, comparison_path)
            logger.info(f"Saved comparison to: {comparison_path}")

            # Print comparison summary
            print("\n" + "=" * 60)
            print("COMPARISON RESULTS")
            print("=" * 60)
            print(f"Accuracy delta: {comparison.accuracy_delta:+.1f}%")
            print(f"Improvements: {len(comparison.improvements)}")
            print(f"Regressions: {len(comparison.regressions)}")
            print(f"Unchanged: {len(comparison.unchanged)}")

            if comparison.has_regressions():
                print("\nWARNING: Regressions detected!")
                for qid in comparison.regressions[:5]:
                    print(f"  - {qid}")
                if len(comparison.regressions) > 5:
                    print(f"  ... and {len(comparison.regressions) - 5} more")
            print("=" * 60)

        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return 1

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Handle report subcommand."""
    logger.info("Generating comparison report")

    # Load runs
    try:
        baseline = BenchmarkEvaluator.load_run(args.baseline)
        enhanced = BenchmarkEvaluator.load_run(args.enhanced)
    except Exception as e:
        logger.error(f"Failed to load runs: {e}")
        return 1

    logger.info(f"Baseline: {baseline.run_id}")
    logger.info(f"Enhanced: {enhanced.run_id}")

    # Create comparison
    evaluator = BenchmarkEvaluator(Config.from_env())
    comparison = evaluator.compare_runs(baseline, enhanced)

    # Generate reports
    reporter = BenchmarkReporter()
    formats = [f.strip() for f in args.formats.split(",")]

    try:
        saved = reporter.save_reports(
            comparison=comparison,
            output_dir=args.output,
            formats=formats,
            title=args.title,
        )
    except Exception as e:
        logger.error(f"Failed to generate reports: {e}")
        return 1

    # Print summary
    print("\n" + "=" * 60)
    print("REPORTS GENERATED")
    print("=" * 60)
    print(f"Comparison ID: {comparison.comparison_id}")
    print(f"Accuracy delta: {comparison.accuracy_delta:+.1f}%")
    print("\nGenerated files:")
    for fmt, path in saved.items():
        print(f"  {fmt}: {path}")
    print("=" * 60)

    return 0


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "generate":
        return cmd_generate(args)
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "report":
        return cmd_report(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
