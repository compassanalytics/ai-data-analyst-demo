#!/usr/bin/env python3
"""
Generate Healthcare Dataset
============================

CLI script to generate the Healthcare dataset with two versions:
- Star Schema (clean): 9 tables demonstrating proper dimensional modeling
- Super Table (dirty): 100+ columns demonstrating anti-patterns

Usage:
    uv run python -m dataset_generators.generate_healthcare
    uv run python -m dataset_generators.generate_healthcare --scale 0.1 --seed 42
    uv run python -m dataset_generators.generate_healthcare --clean-only --dry-run

Options:
    --output-dir    Output directory for parquet files (default: ./data)
    --scale         Scale factor for record counts (default: 1.0, use 0.1 for 10%)
    --seed          Random seed for reproducibility (default: 42)
    --dry-run       Show what would be generated without writing files
    --clean-only    Generate only star schema (clean version)
    --dirty-only    Generate only super table (dirty version)
"""

import argparse
import os
import sys
from datetime import datetime

# Add parent directory to path for imports when running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataset_generators.healthcare import (
    generate_healthcare_star_schema,
    generate_healthcare_super_table,
    scale_count,
    set_random_seed,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate Healthcare dataset (star schema and super table)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate both datasets (full size)
    uv run python -m dataset_generators.generate_healthcare

    # Generate 10% scale for testing
    uv run python -m dataset_generators.generate_healthcare --scale 0.1

    # Generate only star schema
    uv run python -m dataset_generators.generate_healthcare --clean-only

    # Preview without writing files
    uv run python -m dataset_generators.generate_healthcare --dry-run
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
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )

    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Generate only star schema (clean version)",
    )

    parser.add_argument(
        "--dirty-only",
        action="store_true",
        help="Generate only super table (dirty version)",
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
        print("Error: Cannot use both --clean-only and --dirty-only")
        sys.exit(1)


def print_summary(star_data, super_df, star_dir, super_dir, elapsed_seconds, dry_run):
    """Print summary table of generated data."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_rows = 0
    total_tables = 0

    if star_data:
        print("\nSTAR SCHEMA (Clean Version):")
        print(f"  Output: {star_dir}")
        for table_name, df in star_data.items():
            rows = len(df)
            cols = len(df.columns)
            print(f"    {table_name}: {rows:,} rows, {cols} columns")
            total_rows += rows
            total_tables += 1

    if super_df is not None:
        print("\nSUPER TABLE (Dirty Version):")
        print(f"  Output: {super_dir}")
        print(f"    healthcare_super_table: {len(super_df):,} rows, {len(super_df.columns)} columns")
        total_rows += len(super_df)
        total_tables += 1

    print(f"\n{'=' * 70}")
    print(f"Total: {total_tables} table(s), {total_rows:,} rows")
    print(f"Time: {elapsed_seconds:.2f} seconds")
    print("=" * 70)

    if dry_run:
        print("\n[DRY RUN] No files were written")


def main():
    """Main entry point."""
    args = parse_args()
    validate_args(args)

    print("=" * 70)
    print("HEALTHCARE DATASET GENERATOR")
    print("=" * 70)
    print("\nConfiguration:")
    print(f"    Output:     {args.output_dir}")
    print(f"    Scale:      {args.scale}")
    print(f"    Seed:       {args.seed}")
    print(f"    Dry Run:    {args.dry_run}")
    print(f"    Clean Only: {args.clean_only}")
    print(f"    Dirty Only: {args.dirty_only}")

    # Ensure we're working with absolute paths
    output_dir = os.path.abspath(args.output_dir)
    star_dir = os.path.join(output_dir, "healthcare_star")
    super_dir = os.path.join(output_dir, "healthcare_super")

    # Set random seed
    set_random_seed(args.seed)

    start_time = datetime.now()
    star_data = None
    super_df = None

    # Generate Star Schema (Clean Version)
    if not args.dirty_only:
        print("\n[1/2] Generating Star Schema (Clean Version)...")
        print("-" * 70)

        if args.dry_run:
            # Show what would be generated
            n_patients = scale_count(5000, args.scale)
            n_providers = scale_count(500, args.scale)
            n_encounters = scale_count(50000, args.scale)
            n_claims = scale_count(60000, args.scale)
            n_prescriptions = scale_count(40000, args.scale)

            print("  [DRY RUN] Would generate:")
            print(f"    - dim_patient: ~{n_patients:,} rows")
            print(f"    - dim_provider: ~{n_providers:,} rows")
            print("    - dim_date: ~1,461 rows (4 years)")
            print(
                f"    - dim_diagnosis: ~{len(__import__('dataset_generators.healthcare.codes', fromlist=['ICD10_CODES_CLEAN']).ICD10_CODES_CLEAN)} rows"
            )
            print(
                f"    - dim_procedure: ~{len(__import__('dataset_generators.healthcare.codes', fromlist=['CPT_CODES']).CPT_CODES)} rows"
            )
            print("    - dim_payer: ~25 rows")
            print(f"    - fact_encounters: ~{n_encounters:,} rows")
            print(f"    - fact_claims: ~{n_claims:,} rows")
            print(f"    - fact_prescriptions: ~{n_prescriptions:,} rows")
            print(f"  [DRY RUN] Would save to: {star_dir}/")

            # Create placeholder for summary
            star_data = {
                "dim_patient": type("DF", (), {"__len__": lambda s: n_patients, "columns": range(14)})(),
                "dim_provider": type("DF", (), {"__len__": lambda s: n_providers, "columns": range(8)})(),
                "dim_date": type("DF", (), {"__len__": lambda s: 1461, "columns": range(10)})(),
                "dim_diagnosis": type("DF", (), {"__len__": lambda s: 50, "columns": range(5)})(),
                "dim_procedure": type("DF", (), {"__len__": lambda s: 35, "columns": range(4)})(),
                "dim_payer": type("DF", (), {"__len__": lambda s: 25, "columns": range(4)})(),
                "fact_encounters": type("DF", (), {"__len__": lambda s: n_encounters, "columns": range(9)})(),
                "fact_claims": type("DF", (), {"__len__": lambda s: n_claims, "columns": range(9)})(),
                "fact_prescriptions": type("DF", (), {"__len__": lambda s: n_prescriptions, "columns": range(12)})(),
            }
        else:
            star_data = generate_healthcare_star_schema(
                scale=args.scale,
                seed=args.seed,
                output_dir=star_dir,
            )

    # Generate Super Table (Dirty Version)
    if not args.clean_only:
        print("\n[2/2] Generating Super Table (Dirty Version)...")
        print("-" * 70)

        n_rows = scale_count(50000, args.scale)

        if args.dry_run:
            print("  [DRY RUN] Would generate:")
            print(f"    - healthcare_super_table: ~{n_rows:,} rows, 100+ columns")
            print(f"  [DRY RUN] Would save to: {super_dir}/")

            # Create placeholder for summary
            super_df = type("DF", (), {"__len__": lambda s: n_rows, "columns": range(105)})()
        else:
            super_df = generate_healthcare_super_table(
                n_rows=n_rows,
                seed=args.seed,
                output_dir=super_dir,
            )

    elapsed = (datetime.now() - start_time).total_seconds()
    print_summary(star_data, super_df, star_dir, super_dir, elapsed, args.dry_run)

    if not args.dry_run:
        print("\nFiles generated successfully!")

    print("\nNEXT STEPS:")
    print("-" * 70)
    print("""
1. Upload to Databricks Unity Catalog:
   - Create catalog and schema (e.g., healthcare.bronze)
   - Upload parquet files as managed tables

2. Add table comments and column descriptions:
   - Run ALTER TABLE commands to add COMMENT metadata
   - See the HEALTHCARE_FAILURE_SCENARIOS for demo questions

3. Create Genie Space:
   - Add star schema tables for success demo
   - Add super table for failure demo
   - Configure with sample questions

4. Demo the difference:
   - Ask "How many unique patients?" on both
   - Ask "What is total revenue?" on both
   - Show how star schema answers correctly
""")


if __name__ == "__main__":
    main()
