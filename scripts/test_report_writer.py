#!/usr/bin/env python
"""Report Writer testing script.

Test report generation from synthesis results in Markdown and HTML formats.

Usage:
    uv run python scripts/test_report_writer.py --mock
    uv run python scripts/test_report_writer.py --mock --output reports/ --open
    uv run python scripts/test_report_writer.py --mock --title "Q4 Analysis Report"
"""

import argparse
import os
import sys
import time
import webbrowser
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.multi_genie_orchestrator import (
    MultiGenieOrchestrator,
    GenieSpaceConfig,
)
from src.agents.synthesizer_agent import SynthesizerAgent
from src.agents.report_writer import ReportWriter, ReportConfig
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
        description="Test Report Writer with Markdown and HTML output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mock mode - generate and print markdown
  uv run python scripts/test_report_writer.py --mock

  # Mock mode - save reports to directory
  uv run python scripts/test_report_writer.py --mock --output reports/

  # Mock mode - save and open HTML in browser
  uv run python scripts/test_report_writer.py --mock --output reports/ --open

  # Custom title
  uv run python scripts/test_report_writer.py --mock --title "Q4 Analysis Report"
        """
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="What are the current sales trends, inventory levels, and customer segments?",
        help="Natural language query to run across spaces"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock mode (no Databricks connection)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output directory for saving reports (if not specified, only prints markdown)"
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default=None,
        help="Custom title for the reports"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_browser",
        help="Open HTML report in browser after generation"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Maximum parallel queries (default: 3)"
    )

    args = parser.parse_args()

    # Setup
    print("=" * 70)
    print("Report Writer Tester")
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
    if args.output:
        print(f"Output Directory: {args.output}")
    if args.title:
        print(f"Report Title: {args.title}")
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

    # Create report writer
    report_config = ReportConfig(
        title=args.title,
        include_timestamp=True,
        max_table_rows=10,
    )
    report_writer = ReportWriter(base_config, report_config)

    # Execute pipeline
    print(f"\nQuery: {args.query}")
    print("-" * 70)
    print("Step 1: Querying Genie Spaces...")

    start_time = time.time()
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

    print(f"Synthesis completed in {synth_elapsed:.2f}s")
    print(f"  Success: {synthesis.success}")
    print(f"  Insights: {len(synthesis.key_insights)}")
    print(f"  Correlations: {len(synthesis.cross_domain_correlations)}")
    print(f"  Anomalies: {len(synthesis.anomalies)}")
    print(f"  Recommendations: {len(synthesis.recommendations)}")

    # Generate reports
    print("\n" + "-" * 70)
    print("Step 3: Generating reports...")

    report_start = time.time()

    if args.output:
        # Save reports to files
        md_path, html_path = report_writer.save_report(
            synthesis,
            args.output,
            filename_prefix="report",
            title=args.title,
        )
        report_elapsed = time.time() - report_start

        print(f"Reports generated in {report_elapsed:.2f}s")
        print(f"  Markdown: {md_path}")
        print(f"  HTML:     {html_path}")

        if args.open_browser:
            print(f"\nOpening HTML report in browser...")
            webbrowser.open(f"file://{html_path.absolute()}")

    # Always print markdown output
    print("\n" + "=" * 70)
    print("MARKDOWN REPORT:")
    print("=" * 70)

    markdown = report_writer.generate_markdown(synthesis, args.title)
    print(markdown)

    # Print total time
    total_elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"Total pipeline time: {total_elapsed:.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
