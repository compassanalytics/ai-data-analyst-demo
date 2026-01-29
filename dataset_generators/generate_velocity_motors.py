#!/usr/bin/env python3
"""
Generate Velocity Motors Dataset
=================================

CLI script to generate the Velocity Motors fictional automotive company dataset.

Usage:
    uv run python generate_velocity_motors.py
    uv run python generate_velocity_motors.py --scale 0.1 --seed 42
    uv run python generate_velocity_motors.py --domain sales --dry-run

Options:
    --output-dir    Output directory for parquet files (default: ./data/velocity_motors)
    --scale         Scale factor for record counts (default: 1.0, use 0.1 for 10%)
    --seed          Random seed for reproducibility (default: 42)
    --dry-run       Show what would be generated without writing files
    --domain        Generate only specific domain: sales, crm, operations, or all (default: all)
"""

import argparse
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from velocity_motors import (
    set_random_seed,
    generate_sales_domain,
    generate_crm_domain,
    generate_operations_domain,
)
from velocity_motors.sales import generate_salespersons, generate_vehicles, generate_orders, generate_order_items
from velocity_motors.utils import scale_count


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate Velocity Motors fictional automotive dataset',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate full dataset
    uv run python generate_velocity_motors.py

    # Generate 10% scale for testing
    uv run python generate_velocity_motors.py --scale 0.1 --seed 42

    # Generate only sales domain
    uv run python generate_velocity_motors.py --domain sales

    # Preview without writing files
    uv run python generate_velocity_motors.py --dry-run
        """,
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='./data/velocity_motors',
        help='Output directory for parquet files (default: ./data/velocity_motors)',
    )

    parser.add_argument(
        '--scale',
        type=float,
        default=1.0,
        help='Scale factor for record counts (default: 1.0, use 0.1 for 10%%)',
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)',
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without writing files',
    )

    parser.add_argument(
        '--domain',
        type=str,
        choices=['sales', 'crm', 'operations', 'all'],
        default='all',
        help='Generate only specific domain (default: all)',
    )

    parser.add_argument(
        '--cleanliness',
        type=int,
        default=100,
        help='Data cleanliness level 0-100 (100=pristine, 0=messy). Default: 100',
    )

    return parser.parse_args()


def validate_args(args):
    """Validate command line arguments."""
    if args.scale <= 0:
        print(f"Error: --scale must be greater than 0, got {args.scale}")
        sys.exit(1)

    if args.scale > 10:
        print(f"Warning: --scale {args.scale} will generate a very large dataset")

    if args.cleanliness < 0 or args.cleanliness > 100:
        print(f"Error: --cleanliness must be between 0 and 100, got {args.cleanliness}")
        sys.exit(1)


def save_domain(domain_data: dict, output_dir: str, domain_name: str, dry_run: bool):
    """Save domain DataFrames to parquet files."""
    for table_name, df in domain_data.items():
        path = os.path.join(output_dir, f'{table_name}.parquet')
        if dry_run:
            print(f"    [DRY RUN] Would write {path} ({len(df):,} rows)")
        else:
            df.to_parquet(path, index=False)
            print(f"    Saved {table_name}.parquet ({len(df):,} rows)")


def print_summary(all_data: dict, output_dir: str, elapsed_seconds: float):
    """Print summary table of generated data."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_rows = 0
    total_tables = 0

    for domain_name, domain_data in all_data.items():
        print(f"\n{domain_name.upper()} DOMAIN:")
        for table_name, df in domain_data.items():
            rows = len(df)
            cols = len(df.columns)
            print(f"    {table_name}: {rows:,} rows, {cols} columns")
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
    print("VELOCITY MOTORS DATASET GENERATOR")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"    Output:     {args.output_dir}")
    print(f"    Scale:      {args.scale}")
    print(f"    Seed:       {args.seed}")
    print(f"    Domain:     {args.domain}")
    print(f"    Cleanliness: {args.cleanliness}")
    print(f"    Dry Run:    {args.dry_run}")

    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Create output directory
    output_dir = os.path.abspath(args.output_dir)
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Set random seed
    set_random_seed(args.seed)

    start_time = datetime.now()
    all_data = {}

    # Determine if we should use extended data (at cleanliness < 90)
    use_extended = args.cleanliness < 90

    if args.domain == 'all':
        # =====================================================================
        # MULTI-PHASE GENERATION - Fixes FK circular dependency
        # =====================================================================
        # The circular dependency problem:
        # - Sales.orders needs CRM.customer_ids
        # - CRM.leads needs Sales.salesperson_ids
        #
        # Solution: Generate independent dimension tables first, then generate
        # dependent fact tables with proper FK references.
        # =====================================================================

        print("\n[Phase A] Generating Independent Dimension Tables...")
        print("-" * 70)

        # Step 1: Generate salespersons (independent)
        print("  Generating salespersons...")
        salespersons_df = generate_salespersons(
            n=scale_count(50, args.scale),
            cleanliness=args.cleanliness,
        )
        salesperson_ids = salespersons_df['salesperson_id'].tolist()

        # Step 2: Generate vehicles (independent)
        print("  Generating vehicles...")
        vehicles_df = generate_vehicles(
            n=scale_count(5000, args.scale),
            cleanliness=args.cleanliness,
            use_extended=use_extended,
        )
        vehicle_ids = vehicles_df['vehicle_id'].tolist()

        print("\n[Phase B] Generating CRM Domain (with salesperson FK)...")
        print("-" * 70)

        # Step 3: Generate CRM domain with salesperson_ids
        crm_data = generate_crm_domain(
            scale=args.scale,
            cleanliness=args.cleanliness,
            salesperson_ids=salesperson_ids,
        )
        customer_ids = crm_data['customers']['customer_id'].tolist()
        all_data['crm'] = crm_data
        save_domain(crm_data, output_dir, 'crm', args.dry_run)

        print("\n[Phase C] Generating Sales Orders (with customer FK)...")
        print("-" * 70)

        # Step 4: Generate orders with VALID customer_ids
        print("  Generating orders...")
        orders_df = generate_orders(
            n=scale_count(100000, args.scale),
            customer_ids=customer_ids,  # PASS VALID customer IDs
            vehicle_ids=vehicle_ids,
            salesperson_ids=salesperson_ids,
            cleanliness=args.cleanliness,
        )

        # Step 5: Generate order_items
        print("  Generating order_items...")
        order_items_df = generate_order_items(orders_df, vehicles_df)

        # Assemble sales data
        sales_data = {
            'salespersons': salespersons_df,
            'vehicles': vehicles_df,
            'orders': orders_df,
            'order_items': order_items_df,
        }
        all_data['sales'] = sales_data
        save_domain(sales_data, output_dir, 'sales', args.dry_run)

        print("\n[Phase D] Generating Operations Domain...")
        print("-" * 70)

        # Step 6: Generate operations with proper FKs
        ops_data = generate_operations_domain(
            scale=args.scale,
            cleanliness=args.cleanliness,
            customer_ids=customer_ids,
            vehicle_ids=vehicle_ids,
        )
        all_data['operations'] = ops_data
        save_domain(ops_data, output_dir, 'operations', args.dry_run)

    else:
        # Single domain generation (original behavior)
        # Note: When generating single domains, FK integrity may not be guaranteed

        # Generate Sales Domain
        if args.domain == 'sales':
            print("\n[1/3] Generating Sales Domain...")
            print("-" * 70)
            sales_data = generate_sales_domain(
                scale=args.scale,
                cleanliness=args.cleanliness,
            )
            all_data['sales'] = sales_data
            save_domain(sales_data, output_dir, 'sales', args.dry_run)

        # Generate CRM Domain
        elif args.domain == 'crm':
            print("\n[2/3] Generating CRM Domain...")
            print("-" * 70)
            crm_data = generate_crm_domain(
                scale=args.scale,
                cleanliness=args.cleanliness,
            )
            all_data['crm'] = crm_data
            save_domain(crm_data, output_dir, 'crm', args.dry_run)

        # Generate Operations Domain
        elif args.domain == 'operations':
            print("\n[3/3] Generating Operations Domain...")
            print("-" * 70)
            ops_data = generate_operations_domain(
                scale=args.scale,
                cleanliness=args.cleanliness,
            )
            all_data['operations'] = ops_data
            save_domain(ops_data, output_dir, 'operations', args.dry_run)

    elapsed = (datetime.now() - start_time).total_seconds()
    print_summary(all_data, output_dir, elapsed)

    if args.dry_run:
        print("\n[DRY RUN] No files were written")
    else:
        print("\nFiles generated successfully!")

    print("\nNEXT STEPS:")
    print("-" * 70)
    print("""
1. Upload to Databricks Unity Catalog:
   - Create catalog and schema (e.g., velocity_motors.bronze)
   - Upload parquet files as managed tables

2. Add table comments and column descriptions:
   - See data/velocity_motors/README.md for schema documentation

3. Create Genie Space:
   - Add all 12 tables
   - Configure with sample questions and business context
""")


if __name__ == "__main__":
    main()
