"""
Finance Banking Dataset Generator
=================================

A fictional bank dataset with 8 tables in a star schema design:

**Dimension Tables:**
- dim_customer: Customer master data with segment, risk, and KYC information
- dim_product: Banking products (loans, cards, deposits, investments)
- dim_account: Customer accounts with status and currency
- dim_branch: Bank branch locations and types
- dim_employee: Bank employees with roles and departments
- dim_date: Date dimension with fiscal calendar (fiscal year starts Feb 1)

**Fact Tables:**
- fact_transaction: Transaction records with amounts, types, and channels
- fact_account_balance: Daily account balance snapshots

**Anti-Pattern Super Table:**
The dirty generator also produces a denormalized super table demonstrating
common data quality issues that break AI/BI tools:
- Duplicate ID columns (6 variations each for transactions, accounts, customers)
- Multiple date formats (10+ columns)
- Ambiguous amount columns (8 variations)
- Cryptic codes vs readable names
- Inconsistent boolean formats (0/1/Y/N/True/False)
- Mystery columns with no documentation

Usage:
    from finance_banking import (
        generate_finance_domain,
        set_random_seed,
    )

    # Set seed for reproducibility
    set_random_seed(42)

    # Generate all tables and save to disk
    tables = generate_finance_domain(scale=1.0, output_dir='./data/finance_star_schema')

    # Or generate without saving
    tables = generate_finance_domain(scale=0.1)
    dim_customer = tables['dim_customer']
    fact_transaction = tables['fact_transaction']
"""

import os
from typing import Dict, Optional

import pandas as pd

from .accounts import generate_accounts_domain
from .organization import generate_operations_domain
from .transactions import generate_transaction_facts
from .utils import set_random_seed

__all__ = [
    "set_random_seed",
    "generate_finance_domain",
    "generate_finance_super_table",
]


def generate_finance_domain(
    scale: float = 1.0,
    output_dir: str | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Generate all finance banking domain tables.

    Orchestrates generation of dimension and fact tables in the correct order
    to maintain referential integrity.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)
        output_dir: Directory to save parquet files (optional)

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    all_tables = {}

    # 1. Generate account-related dimensions (customer, product, account)
    print("\n[1/3] Generating Accounts Domain...")
    print("-" * 50)
    accounts_data = generate_accounts_domain(scale=scale)
    all_tables.update(accounts_data)

    # 2. Generate organization dimensions (branch, employee, date)
    print("\n[2/3] Generating Operations Domain...")
    print("-" * 50)
    ops_data = generate_operations_domain(scale=scale)
    all_tables.update(ops_data)

    # 3. Generate fact tables (transactions, balances)
    print("\n[3/3] Generating Transaction Facts...")
    print("-" * 50)
    facts_data = generate_transaction_facts(
        scale=scale,
        dim_date=all_tables["dim_date"],
        dim_account=all_tables["dim_account"],
        dim_customer=all_tables["dim_customer"],
        dim_branch=all_tables["dim_branch"],
        dim_employee=all_tables["dim_employee"],
    )
    all_tables.update(facts_data)

    # Save to parquet if output_dir specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nSaving tables to {output_dir}...")
        for table_name, df in all_tables.items():
            path = os.path.join(output_dir, f"{table_name}.parquet")
            df.to_parquet(path, index=False)
            print(f"  Saved {table_name}.parquet ({len(df):,} rows)")

    return all_tables


# Re-export for convenience
def generate_finance_super_table(n_rows: int = 500000) -> pd.DataFrame:
    """
    Generate a denormalized super table with anti-patterns.

    This is a convenience re-export from dirty_generator.

    Args:
        n_rows: Number of rows to generate

    Returns:
        DataFrame with anti-patterns embedded
    """
    from .dirty_generator import generate_finance_super_table as _generate

    return _generate(n_rows=n_rows)
