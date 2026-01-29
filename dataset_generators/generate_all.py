"""
Generate All Demo Datasets
==========================

Run this script to generate both the star schema and super table datasets,
or generate datasets at a specific cleanliness level using the unified generator.

Usage:
    # Default: Generate both star schema (cleanliness=100) and super table (cleanliness=0)
    uv run python -m dataset_generators.generate_all

    # Generate at specific cleanliness level (0-100)
    uv run python -m dataset_generators.generate_all --cleanliness 50

    # Generate at preset level
    uv run python -m dataset_generators.generate_all --level messy

    # Custom output directory and seed
    uv run python -m dataset_generators.generate_all --cleanliness 75 --output ./my_data --seed 123

Output:
    ./data/star_schema/       - Good data engineering example (default mode)
    ./data/super_table/       - Bad data engineering example (default mode)
    ./data/cleanliness_<N>/   - Dataset at cleanliness level N (when using --cleanliness or --level)
"""

import argparse
import os

from .unified_generator import generate_dataset


def _generate_default_datasets(base_output_dir: str) -> None:
    """
    Generate both star schema and super table datasets (original default behavior).

    Args:
        base_output_dir: Base directory for output files
    """
    print("=" * 70)
    print("DATABRICKS AI/BI WORKSHOP - DATASET GENERATOR")
    print("=" * 70)

    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    star_dir = os.path.join(base_output_dir, "star_schema")
    super_dir = os.path.join(base_output_dir, "super_table")

    # Create output directories
    os.makedirs(star_dir, exist_ok=True)
    os.makedirs(super_dir, exist_ok=True)

    print("\n[1/3] Generating Star Schema (Good Example)...")
    print("-" * 70)
    from .star_schema_generator import generate_star_schema

    star_data = generate_star_schema(output_dir=star_dir)

    print("\n[2/3] Generating Super Table (Bad Example)...")
    print("-" * 70)
    from .super_table_generator import save_super_table

    super_data = save_super_table(output_dir=super_dir)

    print("\n[3/3] Summary...")
    print("-" * 70)

    print("\n STAR SCHEMA (Good):")
    print(f"   Location: {star_dir}/")
    print("   Tables:")
    for name, df in star_data.items():
        print(f"      - {name}.parquet: {len(df):,} rows, {len(df.columns)} cols")

    print("\n SUPER TABLE (Bad):")
    print(f"   Location: {super_dir}/")
    print(f"   Table: super_table.parquet: {len(super_data):,} rows, {len(super_data.columns)} cols")

    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("""
1. Upload to Databricks:
   - Create a catalog/schema in Unity Catalog
   - Upload parquet files as managed tables
   - Add column descriptions (for star schema)

2. Create Genie Spaces:
   - Space 1: "Super Table Demo" - add super_table only
   - Space 2: "Star Schema Demo" - add all dim_* and fact_* tables

3. Configure Star Schema Space:
   - Add SQL expressions from genie_failure_scenarios.py
   - Add sample questions
   - Add system prompt with business context

4. Run the demo:
   - Follow the script in genie_failure_scenarios.py DEMO_SCRIPT
""")

    print("=" * 70)
    print("Files generated successfully!")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Generate datasets for AI Data Analyst Workshop")
    parser.add_argument(
        "--cleanliness",
        "-c",
        type=int,
        default=None,
        help="Cleanliness level (0-100). If set, uses unified generator. Default: generate both star (100) and super (0)",
    )
    parser.add_argument(
        "--level",
        "-l",
        choices=["pristine", "mostly_clean", "moderate", "messy", "chaotic", "nightmare"],
        default=None,
        help="Preset cleanliness level. Alternative to --cleanliness.",
    )
    parser.add_argument("--output", "-o", type=str, default="./data", help="Base output directory (default: ./data)")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    # Map preset levels to cleanliness values
    level_map = {
        "pristine": 100,
        "mostly_clean": 85,
        "moderate": 70,
        "messy": 50,
        "chaotic": 25,
        "nightmare": 0,
    }

    if args.level:
        cleanliness = level_map[args.level]
        output_dir = os.path.join(args.output, f"cleanliness_{cleanliness}")
        print(f"Generating dataset at {args.level} level (cleanliness={cleanliness})...")
        result, queries = generate_dataset(cleanliness=cleanliness, seed=args.seed, output_dir=output_dir)
        print(f"\nGenerated {len(result['tables'])} table(s) in {result['format']} format")
        print(f"Active patterns: {len(result['active_patterns'])}")
        print(f"Active traps: {len(result['active_traps'])}")

    elif args.cleanliness is not None:
        output_dir = os.path.join(args.output, f"cleanliness_{args.cleanliness}")
        print(f"Generating dataset at cleanliness={args.cleanliness}...")
        result, queries = generate_dataset(cleanliness=args.cleanliness, seed=args.seed, output_dir=output_dir)
        print(f"\nGenerated {len(result['tables'])} table(s) in {result['format']} format")
        print(f"Active patterns: {len(result['active_patterns'])}")
        print(f"Active traps: {len(result['active_traps'])}")

    else:
        # Default behavior: generate both star schema and super table
        # (original behavior for backward compatibility)
        _generate_default_datasets(args.output)


if __name__ == "__main__":
    main()
