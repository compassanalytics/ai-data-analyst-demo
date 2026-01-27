"""
Generate All Demo Datasets
==========================

Run this script to generate both the star schema and super table datasets.

Usage:
    uv run python generate_all.py

Output:
    ./data/star_schema/   - Good data engineering example
    ./data/super_table/   - Bad data engineering example
"""

import os
import sys

def main():
    print("="*70)
    print("DATABRICKS AI/BI WORKSHOP - DATASET GENERATOR")
    print("="*70)

    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Create output directories
    os.makedirs("./data/star_schema", exist_ok=True)
    os.makedirs("./data/super_table", exist_ok=True)

    print("\n[1/3] Generating Star Schema (Good Example)...")
    print("-"*70)
    from star_schema_generator import generate_star_schema
    star_data = generate_star_schema(output_dir="./data/star_schema")

    print("\n[2/3] Generating Super Table (Bad Example)...")
    print("-"*70)
    from super_table_generator import save_super_table
    super_data = save_super_table(output_dir="./data/super_table")

    print("\n[3/3] Summary...")
    print("-"*70)

    print("\n STAR SCHEMA (Good):")
    print("   Location: ./data/star_schema/")
    print("   Tables:")
    for name, df in star_data.items():
        print(f"      - {name}.parquet: {len(df):,} rows, {len(df.columns)} cols")

    print("\n SUPER TABLE (Bad):")
    print(f"   Location: ./data/super_table/")
    print(f"   Table: super_table.parquet: {len(super_data):,} rows, {len(super_data.columns)} cols")

    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
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

    print("="*70)
    print("Files generated successfully!")
    print("="*70)


if __name__ == "__main__":
    main()
