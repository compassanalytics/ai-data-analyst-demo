#!/usr/bin/env python
"""Synthesizer Agent testing script.

Test cross-domain synthesis from multiple Genie Space results.

Usage:
    uv run python scripts/test_synthesizer.py --mock "What are sales trends and inventory levels?"
    uv run python scripts/test_synthesizer.py --mock --query "Show customer segments and revenue"
    uv run python scripts/test_synthesizer.py --mock "Compare inventory stock with sales velocity"
"""

import argparse
import os
import sys
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.multi_genie_orchestrator import (
    GenieSpaceConfig,
    MultiGenieOrchestrator,
)
from src.agents.synthesizer_agent import SynthesizerAgent
from src.config import Config


def get_mock_configs() -> list[GenieSpaceConfig]:
    """Return sample mock configurations for testing.

    Returns:
        List of sample GenieSpaceConfig objects
    """
    return [
        GenieSpaceConfig(
            space_id="mock-sales-001",
            name="Sales Data",
            domain="sales, revenue, orders, products",
            timeout_seconds=60,
            retry_count=1,
        ),
        GenieSpaceConfig(
            space_id="mock-customers-002",
            name="Customer Analytics",
            domain="customers, segments, churn, retention",
            timeout_seconds=60,
            retry_count=1,
        ),
        GenieSpaceConfig(
            space_id="mock-inventory-003",
            name="Inventory Management",
            domain="inventory, stock, warehouse, supply chain",
            timeout_seconds=60,
            retry_count=1,
        ),
    ]


def progress_callback(space_name: str, status: str) -> None:
    """Print timestamped progress updates.

    Args:
        space_name: Name of the space reporting progress
        status: Status message
    """
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"  [{timestamp}] {space_name}: {status}")


def main():
    parser = argparse.ArgumentParser(
        description="Test Synthesizer Agent with cross-domain insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mock mode - sales and inventory analysis
  uv run python scripts/test_synthesizer.py --mock "What are sales trends and inventory levels?"

  # Mock mode - customer analysis
  uv run python scripts/test_synthesizer.py --mock "Show customer segments and their revenue"

  # Mock mode with custom query
  uv run python scripts/test_synthesizer.py --mock --query "Compare inventory stock with sales velocity"

  # Single domain test (limited insights)
  uv run python scripts/test_synthesizer.py --mock --spaces "Sales Data" "Show top products"
        """,
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="What are the current sales trends, inventory levels, and customer segments?",
        help="Natural language query to run across spaces",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock mode (no Databricks connection)")
    parser.add_argument(
        "--spaces", type=str, default=None, help="Comma-separated list of space names to query (default: all)"
    )
    parser.add_argument("--concurrency", type=int, default=3, help="Maximum parallel queries (default: 3)")

    args = parser.parse_args()

    # Setup
    print("=" * 70)
    print("Synthesizer Agent Tester")
    print("=" * 70)

    if args.mock:
        print("Using mock configuration")
        configs = get_mock_configs()
        base_config = Config(mock_mode=True)
    else:
        base_config = Config.from_env()
        configs = base_config.get_genie_space_configs()
        if not configs:
            print("ERROR: No space configurations found.")
            print("Set GENIE_SPACES environment variable or use --mock")
            sys.exit(1)

    print(f"Mode: {'Mock' if base_config.mock_mode else 'Live'}")
    print(f"Max Concurrency: {args.concurrency}")
    print(f"Spaces Configured: {len(configs)}")
    for cfg in configs:
        print(f"  - {cfg.name} ({cfg.space_id[:8]}...): {cfg.domain or 'no domain'}")
    print("=" * 70)

    # Create orchestrator
    orchestrator = MultiGenieOrchestrator(
        space_configs=configs,
        base_config=base_config,
        max_concurrency=args.concurrency,
        progress_callback=progress_callback,
    )

    # Create synthesizer
    synthesizer = SynthesizerAgent(base_config)

    # Execute query
    print(f"\nQuery: {args.query}")
    print("-" * 70)
    print("Step 1: Querying Genie Spaces...")

    start_time = time.time()

    if args.spaces:
        space_names = [s.strip() for s in args.spaces.split(",")]
        print(f"  Querying specific spaces: {space_names}")
        multi_result = orchestrator.query_spaces(args.query, space_names=space_names)
    else:
        multi_result = orchestrator.query_all(args.query)

    query_elapsed = time.time() - start_time

    print(f"\nQuery completed in {query_elapsed:.2f}s")
    print(f"  Overall Success: {multi_result.overall_success}")
    print(f"  Any Success: {multi_result.any_success}")

    # Display query metadata
    print("\n" + "-" * 70)
    print("Query Results Summary:")
    for name, meta in multi_result.metadata.items():
        status = "OK" if meta.success else "FAIL"
        print(f"  {name}: {status} in {meta.query_time_seconds:.2f}s")

    # Run synthesis
    print("\n" + "-" * 70)
    print("Step 2: Synthesizing cross-domain insights...")

    synth_start = time.time()
    synthesis = synthesizer.synthesize(
        multi_result,
        args.query,
        context={"current_date": datetime.now().strftime("%Y-%m-%d")},
    )
    synth_elapsed = time.time() - synth_start

    total_elapsed = time.time() - start_time

    # Display synthesis results
    print(f"\nSynthesis completed in {synth_elapsed:.2f}s")
    print(f"Total time: {total_elapsed:.2f}s")

    print("\n" + "=" * 70)
    print("SYNTHESIS RESULTS")
    print("=" * 70)

    print(f"\nSuccess: {synthesis.success}")
    if synthesis.error:
        print(f"Error: {synthesis.error}")
    print(f"Domains Analyzed: {', '.join(synthesis.domains_analyzed) if synthesis.domains_analyzed else 'None'}")

    # Warnings
    if synthesis.warnings:
        print(f"\nWarnings ({len(synthesis.warnings)}):")
        for warning in synthesis.warnings:
            print(f"  - {warning}")

    # Key Insights
    print("\n" + "-" * 70)
    print("KEY INSIGHTS:")
    if synthesis.key_insights:
        for i, insight in enumerate(synthesis.key_insights, 1):
            importance = insight.importance.upper()
            domains = ", ".join(insight.domains) if insight.domains else "General"
            print(f"\n  {i}. [{importance}] {insight.insight}")
            print(f"     Domains: {domains}")
            if insight.evidence:
                print(f"     Evidence: {insight.evidence}")
    else:
        print("  No insights generated")

    # Correlations
    print("\n" + "-" * 70)
    print("CROSS-DOMAIN CORRELATIONS:")
    if synthesis.cross_domain_correlations:
        for corr in synthesis.cross_domain_correlations:
            print(f"\n  - {corr.description}")
            if corr.domain_a and corr.domain_b:
                print(f"    {corr.domain_a} ({corr.metric_a}) <-> {corr.domain_b} ({corr.metric_b})")
            if corr.relationship:
                print(f"    Relationship: {corr.relationship}")
    else:
        print("  No correlations detected")

    # Anomalies
    print("\n" + "-" * 70)
    print("ANOMALIES DETECTED:")
    if synthesis.anomalies:
        for anomaly in synthesis.anomalies:
            severity = anomaly.severity.upper()
            print(f"\n  - [{severity}] {anomaly.description}")
            if anomaly.domain:
                print(f"    Domain: {anomaly.domain}")
            if anomaly.metric:
                print(f"    Metric: {anomaly.metric}")
            if anomaly.expected_range and anomaly.actual_value:
                print(f"    Expected: {anomaly.expected_range}, Actual: {anomaly.actual_value}")
    else:
        print("  No anomalies detected")

    # Recommendations
    print("\n" + "-" * 70)
    print("RECOMMENDATIONS:")
    if synthesis.recommendations:
        for i, rec in enumerate(synthesis.recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("  No recommendations")

    # Markdown output
    print("\n" + "=" * 70)
    print("MARKDOWN REPORT:")
    print("=" * 70)
    print(synthesis.to_markdown())


if __name__ == "__main__":
    main()
