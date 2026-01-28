#!/usr/bin/env python
"""Test script for PlannerAgent query decomposition.

Test the PlannerAgent's ability to decompose complex questions into
domain-specific sub-queries for multiple Genie Spaces.

Usage:
    uv run python scripts/test_planner.py "What is the total revenue?"
    uv run python scripts/test_planner.py --mock "Compare sales with customer segments"
    uv run python scripts/test_planner.py --list-spaces
    uv run python scripts/test_planner.py --json "Show inventory levels"
"""

import argparse
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.agents.planner_agent import PlannerAgent
from src.agents.multi_genie_orchestrator import GenieSpaceConfig


def create_demo_configs() -> list[GenieSpaceConfig]:
    """Create demo space configs for testing.

    Returns:
        List of sample GenieSpaceConfig objects for demo purposes
    """
    return [
        GenieSpaceConfig(
            space_id="demo_sales_001",
            name="Sales Analytics",
            domain="sales, revenue, orders, products, pricing",
        ),
        GenieSpaceConfig(
            space_id="demo_customers_001",
            name="Customer Intelligence",
            domain="customers, segments, leads, retention, churn",
        ),
        GenieSpaceConfig(
            space_id="demo_operations_001",
            name="Operations & Inventory",
            domain="inventory, parts, warehouse, fulfillment, supply",
        ),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Test PlannerAgent query decomposition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mock mode decomposition
  uv run python scripts/test_planner.py --mock "What are total sales?"

  # List available spaces
  uv run python scripts/test_planner.py --list-spaces

  # Output as JSON
  uv run python scripts/test_planner.py --mock --json "Compare revenue by region"

  # Live mode (requires Databricks credentials)
  uv run python scripts/test_planner.py "Customer retention analysis"
        """,
    )
    parser.add_argument("query", nargs="?", help="Question to decompose")
    parser.add_argument("--mock", action="store_true", help="Force mock mode")
    parser.add_argument("--list-spaces", action="store_true", help="List available spaces")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    space_configs = create_demo_configs()

    if args.list_spaces:
        print("Available Genie Spaces:")
        print("=" * 50)
        for cfg in space_configs:
            print(f"  - {cfg.name}")
            print(f"    Domain: {cfg.domain}")
            print()
        return

    if not args.query:
        parser.print_help()
        return

    # Determine configuration
    config = Config(mock_mode=True) if args.mock else Config.from_env()
    if not config.databricks_host:
        config = Config(mock_mode=True)

    print("=" * 60)
    print("PlannerAgent Tester")
    print("=" * 60)
    print(f"Mode: {'Mock' if config.mock_mode else 'Live'}")
    print(f"Spaces: {', '.join(c.name for c in space_configs)}")
    print(f"Query: {args.query}")
    print("=" * 60)

    planner = PlannerAgent(config, space_configs)
    plan = planner.decompose(args.query)

    if args.json:
        print(plan.to_json())
        return

    # Display human-readable output
    print(f"\nOriginal: {plan.original_question}")
    print(f"Target Spaces: {plan.target_spaces}")
    print(f"Single Space: {plan.is_single_space}")
    print()
    print("Sub-Queries:")
    for sq in plan.sub_queries:
        deps = f" (depends on: {', '.join(sq.depends_on)})" if sq.depends_on else ""
        print(f"  [{sq.id}] -> {sq.target_space} (priority {sq.priority}){deps}")
        print(f'      "{sq.query}"')
    print()
    print(f"Synthesis: {plan.synthesis_instructions}")
    if plan.metadata:
        print(f"Metadata: {plan.metadata}")


if __name__ == "__main__":
    main()
