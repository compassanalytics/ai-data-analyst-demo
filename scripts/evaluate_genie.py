#!/usr/bin/env python
"""Genie Evaluation CLI Script.

Usage:
    uv run python scripts/evaluate_genie.py --space-id ID
    uv run python scripts/evaluate_genie.py --mock --query-types aggregation,filter
    uv run python scripts/evaluate_genie.py --compare-spaces CLEAN_ID,DIRTY_ID
    uv run python scripts/evaluate_genie.py --report-only results.json
    uv run python scripts/evaluate_genie.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.evaluation import (
    ComplexityLevel,
    EvaluationResults,
    EvaluationReporter,
    FailureCategory,
    GenieEvaluator,
    QueryGenerator,
    QueryType,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Evaluate Databricks Genie Space query performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run evaluation on a specific space
  uv run python scripts/evaluate_genie.py --space-id abc123

  # Use mock mode for testing
  uv run python scripts/evaluate_genie.py --mock

  # Filter to specific query types
  uv run python scripts/evaluate_genie.py --query-types aggregation,filter,join

  # Filter to specific complexity levels
  uv run python scripts/evaluate_genie.py --complexity simple,moderate

  # Filter to specific failure categories
  uv run python scripts/evaluate_genie.py --failure-categories ambiguous_columns,cryptic_codes

  # Compare two spaces (clean vs dirty)
  uv run python scripts/evaluate_genie.py --compare-spaces CLEAN_ID,DIRTY_ID

  # Generate reports from existing results
  uv run python scripts/evaluate_genie.py --report-only results.json

  # Dry run to see queries without executing
  uv run python scripts/evaluate_genie.py --dry-run

  # Limit number of queries (for cost control)
  uv run python scripts/evaluate_genie.py --limit 10

  # Custom output directory and formats
  uv run python scripts/evaluate_genie.py --output-dir ./my-reports --formats md,html
        """
    )

    # Space configuration
    parser.add_argument(
        "--space-id",
        default=os.getenv("GENIE_SPACE_ID", ""),
        help="Genie Space ID (default: from GENIE_SPACE_ID env var)"
    )

    # Filtering options
    parser.add_argument(
        "--query-types",
        help="Comma-separated list of query types to include (aggregation,filter,join,temporal,ranking,comparison)"
    )
    parser.add_argument(
        "--complexity",
        help="Comma-separated list of complexity levels to include (simple,moderate,complex)"
    )
    parser.add_argument(
        "--failure-categories",
        help="Comma-separated list of failure categories to include (ambiguous_columns,cryptic_codes,business_logic,temporal_confusion,aggregation_ambiguity,join_complexity)"
    )
    parser.add_argument(
        "--adversarial",
        action="store_true",
        help="Mark all test queries as adversarial"
    )

    # Comparison mode
    parser.add_argument(
        "--compare-spaces",
        help="Two space IDs separated by comma for comparison (CLEAN_ID,DIRTY_ID)"
    )

    # Execution modes
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock mode (no Databricks connection required)"
    )
    parser.add_argument(
        "--report-only",
        metavar="JSON_FILE",
        help="Generate reports from existing JSON results file (no query execution)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show queries that would be executed without running them"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of queries to execute (for cost control)"
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory to save reports (default: reports)"
    )
    parser.add_argument(
        "--formats",
        default="md,html,json",
        help="Comma-separated output formats (md,html,json)"
    )
    parser.add_argument(
        "--title",
        help="Custom title for the report"
    )

    # Execution options
    parser.add_argument(
        "--fresh",
        action="store_true",
        default=True,
        help="Bypass cache for each query (default: True)"
    )
    parser.add_argument(
        "--no-fresh",
        action="store_false",
        dest="fresh",
        help="Allow cached results"
    )

    # Output verbosity
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for each query"
    )

    return parser.parse_args()


def parse_query_types(types_str: str) -> list[QueryType]:
    """Parse query types from comma-separated string.

    Args:
        types_str: Comma-separated query type names

    Returns:
        List of QueryType enum values
    """
    if not types_str:
        return []

    result = []
    for name in types_str.split(","):
        name = name.strip().lower()
        try:
            result.append(QueryType(name))
        except ValueError:
            print(f"Warning: Unknown query type '{name}', skipping")
    return result


def parse_complexity_levels(levels_str: str) -> list[ComplexityLevel]:
    """Parse complexity levels from comma-separated string.

    Args:
        levels_str: Comma-separated complexity level names

    Returns:
        List of ComplexityLevel enum values
    """
    if not levels_str:
        return []

    result = []
    for name in levels_str.split(","):
        name = name.strip().lower()
        try:
            result.append(ComplexityLevel(name))
        except ValueError:
            print(f"Warning: Unknown complexity level '{name}', skipping")
    return result


def parse_failure_categories(categories_str: str) -> list[FailureCategory]:
    """Parse failure categories from comma-separated string.

    Args:
        categories_str: Comma-separated failure category names

    Returns:
        List of FailureCategory enum values
    """
    if not categories_str:
        return []

    result = []
    for name in categories_str.split(","):
        name = name.strip().lower()
        try:
            result.append(FailureCategory(name))
        except ValueError:
            print(f"Warning: Unknown failure category '{name}', skipping")
    return result


def progress_callback(current: int, total: int, query, quiet: bool = False, verbose: bool = False):
    """Print progress during evaluation.

    Args:
        current: Current query number
        total: Total queries
        query: Current TestQuery
        quiet: Suppress output if True
        verbose: Show detailed output if True
    """
    if quiet:
        return

    pct = (current / total) * 100
    print(f"[{current}/{total}] ({pct:.0f}%) {query.question[:60]}...", flush=True)

    if verbose:
        print(f"  ID: {query.id}")
        print(f"  Type: {query.query_type.value}, Complexity: {query.complexity.value}")
        print(f"  Category: {query.failure_category.value}")


def run_evaluation(args: argparse.Namespace) -> EvaluationResults:
    """Run the evaluation based on arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        EvaluationResults from the evaluation
    """
    # Generate test queries
    generator = QueryGenerator()

    query_types = parse_query_types(args.query_types) if args.query_types else None
    complexity_levels = parse_complexity_levels(args.complexity) if args.complexity else None
    failure_categories = parse_failure_categories(args.failure_categories) if args.failure_categories else None

    test_queries = generator.generate_suite(
        query_types=query_types,
        complexity_levels=complexity_levels,
        failure_categories=failure_categories,
        adversarial=args.adversarial,
    )

    # Apply limit if specified
    if args.limit and args.limit < len(test_queries):
        if not args.quiet:
            print(f"Limiting to {args.limit} queries (from {len(test_queries)} total)")
        test_queries = test_queries[:args.limit]

    if not args.quiet:
        print(f"\n{'='*60}")
        print("Genie Evaluation")
        print(f"{'='*60}")
        print(f"Space ID: {args.space_id or '(mock)'}")
        print(f"Mode: {'Mock' if args.mock else 'Live'}")
        print(f"Total Queries: {len(test_queries)}")
        print(f"Fresh (no cache): {args.fresh}")
        print(f"{'='*60}\n")

    # Create config
    config = Config(
        genie_space_id=args.space_id,
        mock_mode=args.mock,
    )

    # Create evaluator and run
    evaluator = GenieEvaluator(config)

    def callback(current, total, query):
        progress_callback(current, total, query, args.quiet, args.verbose)

    results = evaluator.evaluate(
        test_queries,
        progress_callback=callback,
        fresh=args.fresh,
    )

    return results


def run_comparison(args: argparse.Namespace) -> tuple[EvaluationResults, EvaluationResults]:
    """Run comparison evaluation between two spaces.

    Args:
        args: Parsed command line arguments

    Returns:
        Tuple of (results_space1, results_space2)
    """
    space_ids = args.compare_spaces.split(",")
    if len(space_ids) != 2:
        print("Error: --compare-spaces requires exactly two space IDs separated by comma")
        sys.exit(1)

    space1_id, space2_id = [s.strip() for s in space_ids]

    if not args.quiet:
        print(f"\n{'='*60}")
        print("Genie Space Comparison")
        print(f"{'='*60}")
        print(f"Space 1: {space1_id}")
        print(f"Space 2: {space2_id}")
        print(f"{'='*60}\n")

    # Generate test queries (same for both)
    generator = QueryGenerator()

    query_types = parse_query_types(args.query_types) if args.query_types else None
    complexity_levels = parse_complexity_levels(args.complexity) if args.complexity else None
    failure_categories = parse_failure_categories(args.failure_categories) if args.failure_categories else None

    test_queries = generator.generate_suite(
        query_types=query_types,
        complexity_levels=complexity_levels,
        failure_categories=failure_categories,
        adversarial=args.adversarial,
    )

    if args.limit and args.limit < len(test_queries):
        test_queries = test_queries[:args.limit]

    # Evaluate Space 1
    if not args.quiet:
        print(f"\n--- Evaluating Space 1: {space1_id} ---\n")

    config1 = Config(genie_space_id=space1_id, mock_mode=args.mock)
    evaluator1 = GenieEvaluator(config1)

    def callback(current, total, query):
        progress_callback(current, total, query, args.quiet, args.verbose)

    results1 = evaluator1.evaluate(test_queries, progress_callback=callback, fresh=args.fresh)

    # Evaluate Space 2
    if not args.quiet:
        print(f"\n--- Evaluating Space 2: {space2_id} ---\n")

    config2 = Config(genie_space_id=space2_id, mock_mode=args.mock)
    evaluator2 = GenieEvaluator(config2)
    results2 = evaluator2.evaluate(test_queries, progress_callback=callback, fresh=args.fresh)

    return results1, results2


def print_summary(results: EvaluationResults, title: str = "Summary") -> None:
    """Print a summary of evaluation results.

    Args:
        results: EvaluationResults to summarize
        title: Title for the summary
    """
    summary = results.summary
    if not summary:
        print("No summary available")
        return

    print(f"\n{'='*60}")
    print(title)
    print(f"{'='*60}")
    print(f"Total Queries: {summary.total_queries}")
    print(f"Correct:       {summary.correct_count} ({summary.overall_accuracy:.1f}%)")
    print(f"Partial:       {summary.partial_count}")
    print(f"Wrong:         {summary.wrong_count}")
    print(f"Failed:        {summary.failed_count}")
    print(f"Success Rate:  {summary.success_rate:.1f}%")
    print(f"Total Time:    {summary.total_execution_time_ms/1000:.2f}s")
    print(f"Avg Time:      {summary.average_execution_time_ms:.0f}ms")
    print(f"{'='*60}\n")


def main():
    """Main entry point."""
    args = parse_args()

    # Handle report-only mode
    if args.report_only:
        if not args.quiet:
            print(f"Loading results from {args.report_only}...")

        with open(args.report_only, "r") as f:
            data = json.load(f)

        results = EvaluationResults.from_dict(data)

        reporter = EvaluationReporter()
        formats = [f.strip() for f in args.formats.split(",")]
        saved = reporter.save_reports(
            results,
            args.output_dir,
            formats=formats,
            title=args.title,
        )

        print("\nReports generated:")
        for fmt, path in saved.items():
            print(f"  {fmt}: {path}")

        return

    # Handle dry-run mode
    if args.dry_run:
        generator = QueryGenerator()

        query_types = parse_query_types(args.query_types) if args.query_types else None
        complexity_levels = parse_complexity_levels(args.complexity) if args.complexity else None
        failure_categories = parse_failure_categories(args.failure_categories) if args.failure_categories else None

        test_queries = generator.generate_suite(
            query_types=query_types,
            complexity_levels=complexity_levels,
            failure_categories=failure_categories,
            adversarial=args.adversarial,
        )

        if args.limit:
            test_queries = test_queries[:args.limit]

        print(f"\n{'='*60}")
        print("DRY RUN - Queries that would be executed")
        print(f"{'='*60}")
        print(f"Total: {len(test_queries)} queries\n")

        for i, query in enumerate(test_queries, 1):
            print(f"{i}. [{query.id}] {query.question}")
            print(f"   Type: {query.query_type.value}, Complexity: {query.complexity.value}")
            print(f"   Category: {query.failure_category.value}")
            if query.description:
                print(f"   Description: {query.description}")
            print()

        # Print summary
        summary = generator.get_summary()
        print(f"{'='*60}")
        print("Query Summary")
        print(f"{'='*60}")
        print(f"Total: {summary['total']}")
        print(f"\nBy Category:")
        for cat, count in summary["by_category"].items():
            print(f"  {cat}: {count}")
        print(f"\nBy Type:")
        for typ, count in summary["by_type"].items():
            print(f"  {typ}: {count}")
        print(f"\nBy Complexity:")
        for comp, count in summary["by_complexity"].items():
            print(f"  {comp}: {count}")

        return

    # Handle comparison mode
    if args.compare_spaces:
        results1, results2 = run_comparison(args)

        space_ids = args.compare_spaces.split(",")
        space1_id, space2_id = [s.strip() for s in space_ids]

        print_summary(results1, f"Space 1 ({space1_id}) Summary")
        print_summary(results2, f"Space 2 ({space2_id}) Summary")

        # Generate reports for both
        reporter = EvaluationReporter()
        formats = [f.strip() for f in args.formats.split(",")]

        saved1 = reporter.save_reports(
            results1,
            args.output_dir,
            formats=formats,
            filename_prefix=f"evaluation_space1_{space1_id[:8]}",
            title=args.title or f"Evaluation: {space1_id}",
        )

        saved2 = reporter.save_reports(
            results2,
            args.output_dir,
            formats=formats,
            filename_prefix=f"evaluation_space2_{space2_id[:8]}",
            title=args.title or f"Evaluation: {space2_id}",
        )

        print("\nReports generated:")
        print(f"Space 1 ({space1_id}):")
        for fmt, path in saved1.items():
            print(f"  {fmt}: {path}")
        print(f"Space 2 ({space2_id}):")
        for fmt, path in saved2.items():
            print(f"  {fmt}: {path}")

        return

    # Validate space ID for non-mock mode
    if not args.mock and not args.space_id:
        print("Error: --space-id is required when not using --mock mode")
        print("Set GENIE_SPACE_ID environment variable or use --space-id argument")
        sys.exit(1)

    # Run standard evaluation
    results = run_evaluation(args)

    # Print summary
    print_summary(results)

    # Generate reports
    reporter = EvaluationReporter()
    formats = [f.strip() for f in args.formats.split(",")]

    saved = reporter.save_reports(
        results,
        args.output_dir,
        formats=formats,
        title=args.title,
    )

    print("Reports generated:")
    for fmt, path in saved.items():
        print(f"  {fmt}: {path}")


if __name__ == "__main__":
    main()
