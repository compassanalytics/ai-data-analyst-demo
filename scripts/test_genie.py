#!/usr/bin/env python
"""Interactive Genie Space testing script.

Usage:
    uv run python scripts/test_genie.py
    uv run python scripts/test_genie.py "What are total sales by region?"
    uv run python scripts/test_genie.py --space-id YOUR_SPACE_ID
"""

import argparse
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.genie_agent import GenieDataAgent
from src.config import Config


def main():
    parser = argparse.ArgumentParser(
        description="Test Databricks Genie Space queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/test_genie.py
  uv run python scripts/test_genie.py "Show top 10 customers"
  uv run python scripts/test_genie.py --space-id abc123 "Total sales?"
        """,
    )
    parser.add_argument("query", nargs="?", help="Query to run (if not provided, enters interactive mode)")
    parser.add_argument(
        "--space-id",
        default=os.getenv("GENIE_SPACE_ID", ""),
        help="Genie Space ID (default: from GENIE_SPACE_ID env var)",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock mode (no Databricks connection)")

    args = parser.parse_args()

    # Initialize
    print("=" * 60)
    print("Genie Space Tester")
    print("=" * 60)
    print(f"Space ID: {args.space_id}")
    print(f"Mode: {'Mock' if args.mock else 'Live'}")
    print("=" * 60)

    config = Config(genie_space_id=args.space_id, mock_mode=args.mock)

    genie = GenieDataAgent(config)

    if args.query:
        # Single query mode
        run_query(genie, args.query)
    else:
        # Interactive mode
        interactive_mode(genie)


def run_query(genie: GenieDataAgent, query: str):
    """Run a single query and display results."""
    print(f"\nQ: {query}")
    print("-" * 60)

    result = genie.query(query)

    if result.success:
        if result.sql:
            print(f"\nSQL:\n{result.sql}")

        print("\nResults:")
        print(result.to_markdown_table())

        if result.description:
            print(f"\nAnalysis: {result.description}")
    else:
        print(f"\nError: {result.error}")

    print()


def interactive_mode(genie: GenieDataAgent):
    """Interactive query loop."""
    print("\nEntering interactive mode. Type 'quit' or 'exit' to stop.")
    print("Try: 'What are total sales by order status?'")
    print()

    while True:
        try:
            query = input("Ask Genie> ").strip()

            if not query:
                continue

            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if query.lower() == "help":
                print_help()
                continue

            if query.lower() == "examples":
                print_examples()
                continue

            run_query(genie, query)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def print_help():
    """Print help message."""
    print("""
Commands:
  help      - Show this help
  examples  - Show example queries
  quit/exit - Exit interactive mode

Or just type your question!
""")


def print_examples():
    """Print example queries for Velocity Motors data."""
    print("""
Example queries for Velocity Motors data:

  Data Analysis:
    - What is the total revenue by vehicle make?
    - Show top 10 salespeople by total sales
    - What is the average order value by customer segment?
    - Which suppliers have the longest lead times?
    - Show monthly sales trends for the past 12 months

  Aggregations:
    - How many orders per region?
    - What is the breakdown of orders by payment method?
    - Count customers by segment (Individual/Fleet/Dealer)

  Comparisons:
    - Compare sales: New vs Certified Pre-Owned vs Used vehicles
    - Which region has the highest average order value?
""")


if __name__ == "__main__":
    main()
