#!/usr/bin/env python
"""Multi-Genie Orchestrator testing script.

Test parallel queries across multiple Genie Spaces.

Usage:
    uv run python scripts/test_multi_genie.py "What is the total count?"
    uv run python scripts/test_multi_genie.py --mock "Show top products"
    uv run python scripts/test_multi_genie.py --spaces "Sales,Customers" "Revenue by region?"
    uv run python scripts/test_multi_genie.py --config-json config.json "Query here"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.multi_genie_orchestrator import (
    MultiGenieOrchestrator,
    GenieSpaceConfig,
)
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


def load_configs_from_json(filepath: str) -> list[GenieSpaceConfig]:
    """Load GenieSpaceConfig objects from a JSON file.

    Args:
        filepath: Path to the JSON configuration file

    Returns:
        List of GenieSpaceConfig objects
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    configs = []
    for item in data:
        configs.append(
            GenieSpaceConfig(
                space_id=item["space_id"],
                name=item["name"],
                domain=item.get("domain", ""),
                timeout_seconds=item.get("timeout_seconds", 120),
                retry_count=item.get("retry_count", 2),
                retry_delay=item.get("retry_delay", 1.0),
            )
        )
    return configs


def main():
    parser = argparse.ArgumentParser(
        description="Test Multi-Genie Orchestrator with parallel queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mock mode with sample spaces
  uv run python scripts/test_multi_genie.py --mock "What are total sales?"

  # Query specific spaces
  uv run python scripts/test_multi_genie.py --mock --spaces "Sales Data,Customer Analytics" "Show totals"

  # Load configuration from JSON file
  uv run python scripts/test_multi_genie.py --config-json spaces.json "Query"

  # Adjust concurrency
  uv run python scripts/test_multi_genie.py --mock --concurrency 5 "Show summary"
        """
    )
    parser.add_argument(
        "query",
        help="Natural language query to run across spaces"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock mode (no Databricks connection)"
    )
    parser.add_argument(
        "--spaces",
        type=str,
        default=None,
        help="Comma-separated list of space names to query (default: all)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Maximum parallel queries (default: 3)"
    )
    parser.add_argument(
        "--config-json",
        type=str,
        default=None,
        help="Path to JSON file with space configurations"
    )

    args = parser.parse_args()

    # Determine configuration source
    print("=" * 70)
    print("Multi-Genie Orchestrator Tester")
    print("=" * 70)

    configs: list[GenieSpaceConfig] = []
    base_config: Config

    if args.config_json:
        print(f"Loading configs from: {args.config_json}")
        configs = load_configs_from_json(args.config_json)
        base_config = Config.from_env()
        if args.mock:
            base_config = Config(mock_mode=True)
    elif args.mock:
        print("Using mock configuration")
        configs = get_mock_configs()
        base_config = Config(mock_mode=True)
    else:
        # Load from environment
        base_config = Config.from_env()
        configs = base_config.get_genie_space_configs()
        if not configs:
            print("ERROR: No space configurations found.")
            print("Set GENIE_SPACES environment variable or use --mock or --config-json")
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

    # Execute query
    print(f"\nQuery: {args.query}")
    print("-" * 70)
    print("Progress:")

    start_time = time.time()

    if args.spaces:
        space_names = [s.strip() for s in args.spaces.split(",")]
        print(f"  Querying specific spaces: {space_names}")
        result = orchestrator.query_spaces(args.query, space_names=space_names)
    else:
        result = orchestrator.query_all(args.query)

    elapsed = time.time() - start_time

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\nTotal Time: {elapsed:.2f}s")
    print(f"Overall Success: {result.overall_success}")
    print(f"Partial Success: {result.partial_success}")
    print(f"Any Success: {result.any_success}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")

    print("\n" + "-" * 70)
    print("Query Metadata:")
    for name, meta in result.metadata.items():
        status = "OK" if meta.success else "FAIL"
        retry_info = f" (retries: {meta.retries_used})" if meta.retries_used > 0 else ""
        print(f"  {name}: {status} in {meta.query_time_seconds:.2f}s{retry_info}")

    print("\n" + "-" * 70)
    print("Combined Results:")
    print()
    print(result.to_combined_markdown(max_rows_per_space=5))

    # Show space status
    print("\n" + "-" * 70)
    print("Space Status:")
    status = orchestrator.get_space_status()
    for name, info in status.items():
        conv_id = info.get("conversation_id")
        conv_info = f" (conv: {conv_id[:8]}...)" if conv_id else ""
        print(f"  {name}: initialized={info['agent_initialized']}{conv_info}")


if __name__ == "__main__":
    main()
