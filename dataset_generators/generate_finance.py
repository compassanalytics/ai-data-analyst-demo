#!/usr/bin/env python3
"""
Generate Finance Banking Dataset
=================================

CLI script to generate the Finance Banking fictional bank dataset.

Usage:
    uv run python generate_finance.py
    uv run python generate_finance.py --scale 0.1 --seed 42
    uv run python generate_finance.py --clean-only
    uv run python generate_finance.py --dirty-only

Options:
    --output-dir    Output directory for parquet files (default: ./data)
    --scale         Scale factor for record counts (default: 1.0, use 0.1 for 10%)
    --seed          Random seed for reproducibility (default: 42)
    --clean-only    Generate only the star schema (clean) dataset
    --dirty-only    Generate only the super table (dirty) dataset
"""

import argparse
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from finance_banking import generate_finance_domain, set_random_seed
from finance_banking.dirty_generator import save_finance_super_table


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate Finance Banking fictional bank dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate full dataset (clean star schema + dirty super table)
    uv run python generate_finance.py

    # Generate 10% scale for testing
    uv run python generate_finance.py --scale 0.1 --seed 42

    # Generate only clean star schema
    uv run python generate_finance.py --clean-only

    # Generate only dirty super table
    uv run python generate_finance.py --dirty-only

    # Custom output directory
    uv run python generate_finance.py --output-dir /path/to/output
        """,
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data",
        help="Base output directory for parquet files (default: ./data)",
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale factor for record counts (default: 1.0, use 0.1 for 10%%)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Generate only the star schema (clean) dataset",
    )

    parser.add_argument(
        "--dirty-only",
        action="store_true",
        help="Generate only the super table (dirty) dataset",
    )

    return parser.parse_args()


def validate_args(args):
    """Validate command line arguments."""
    if args.scale <= 0:
        print(f"Error: --scale must be greater than 0, got {args.scale}")
        sys.exit(1)

    if args.scale > 10:
        print(f"Warning: --scale {args.scale} will generate a very large dataset")

    if args.clean_only and args.dirty_only:
        print("Error: Cannot specify both --clean-only and --dirty-only")
        sys.exit(1)


def print_summary(clean_tables, dirty_df, output_dir, elapsed_seconds):
    """Print summary table of generated data."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_rows = 0
    total_tables = 0

    if clean_tables:
        print("\nSTAR SCHEMA (Clean):")
        for table_name, df in clean_tables.items():
            rows = len(df)
            cols = len(df.columns)
            print(f"    {table_name}: {rows:,} rows, {cols} columns")
            total_rows += rows
            total_tables += 1

    if dirty_df is not None:
        print("\nSUPER TABLE (Dirty):")
        rows = len(dirty_df)
        cols = len(dirty_df.columns)
        print(f"    finance_super_table: {rows:,} rows, {cols} columns")
        total_rows += rows
        total_tables += 1

    print(f"\n{'=' * 70}")
    print(f"Total: {total_tables} tables, {total_rows:,} rows")
    print(f"Output: {output_dir}")
    print(f"Time: {elapsed_seconds:.2f} seconds")
    print("=" * 70)


def main():
    """Main entry point."""
    args = parse_args()
    validate_args(args)

    print("=" * 70)
    print("FINANCE BANKING DATASET GENERATOR")
    print("=" * 70)
    print("\nConfiguration:")
    print(f"    Output:     {args.output_dir}")
    print(f"    Scale:      {args.scale}")
    print(f"    Seed:       {args.seed}")
    print(f"    Clean Only: {args.clean_only}")
    print(f"    Dirty Only: {args.dirty_only}")

    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Create base output directory
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Set random seed
    set_random_seed(args.seed)

    start_time = datetime.now()
    clean_tables = None
    dirty_df = None

    # Generate clean star schema
    if not args.dirty_only:
        clean_output = os.path.join(output_dir, "finance_star_schema")
        print(f"\nGenerating star schema to: {clean_output}")
        clean_tables = generate_finance_domain(
            scale=args.scale,
            output_dir=clean_output,
        )

    # Generate dirty super table
    if not args.clean_only:
        dirty_output = os.path.join(output_dir, "finance_super_table")
        print(f"\nGenerating super table to: {dirty_output}")
        # Scale dirty table rows
        n_rows = int(500000 * args.scale)
        dirty_df = save_finance_super_table(
            output_dir=dirty_output,
            n_rows=n_rows,
        )

    elapsed = (datetime.now() - start_time).total_seconds()
    print_summary(clean_tables, dirty_df, output_dir, elapsed)

    print("\nFiles generated successfully!")

    print("\nNEXT STEPS:")
    print("-" * 70)
    print("""
1. Upload to Databricks Unity Catalog:
   - Create catalog and schema (e.g., workshop.finance_banking)
   - Upload parquet files as managed tables

2. Add table comments and column descriptions:
   - See dataset_generators/README.md for schema documentation

3. Create Genie Space:
   - Add star schema tables for "good" demo
   - Add super table separately for "bad" demo
   - Configure with sample questions and business context

4. Demo Script:
   - Start with super table, show failures
   - Switch to star schema, show same questions succeeding
   - Discuss data engineering best practices
""")


if __name__ == "__main__":
    main()
