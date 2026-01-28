"""
Anti-Pattern System for Dataset Generators.

This module provides a registry of data quality anti-patterns that cause
AI/BI tools like Databricks Genie to fail. Each pattern is documented with:
- What it does
- Why it causes failures
- Real-world enterprise examples
- How star schema design fixes the issue

Anti-patterns are organized by category:
- naming: Cryptic codes, abbreviations, inconsistent naming
- redundancy: Duplicate columns, calculated fields stored with raw data
- type: Mixed booleans, inconsistent dates, null variations
- structural: Denormalization, conflicting values, orphan keys
- metadata: Missing descriptions, undocumented codes, hidden logic
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class AntiPattern(ABC):
    """
    Base class for data quality anti-patterns.

    Each anti-pattern represents a common data quality issue found in
    enterprise data warehouses that causes AI/BI tools to fail.
    """

    id: str
    category: str
    name: str
    description: str
    why_it_fails: str
    real_world_example: str
    fix_reference: str
    severity: int  # 1-5, 5 = most severe

    @abstractmethod
    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """
        Apply this anti-pattern to a DataFrame.

        Args:
            df: Input DataFrame to transform
            intensity: How strongly to apply (0.0-1.0). Higher values
                      affect more rows/columns.

        Returns:
            Modified DataFrame with anti-pattern applied
        """
        raise NotImplementedError

    def _sample_rows(self, df: pd.DataFrame, intensity: float) -> pd.Index:
        """Helper to get a sample of row indices based on intensity."""
        n_rows = max(1, int(len(df) * intensity))
        return df.sample(n=n_rows).index


# =============================================================================
# CATEGORY 1: NAMING ANTI-PATTERNS
# =============================================================================


@dataclass
class CrypticCodesPattern(AntiPattern):
    """Replace readable values with cryptic codes."""

    id: str = "naming_cryptic_codes"
    category: str = "naming"
    name: str = "Cryptic Codes"
    description: str = "Replace human-readable values with cryptic codes"
    why_it_fails: str = (
        "Genie cannot infer meaning from codes like 'BER', 'ENT', 'RTD'. "
        "Without documentation, the model must guess or ask for clarification, "
        "leading to incorrect queries or confused users."
    )
    real_world_example: str = (
        "Beer category stored as 'BER', Cider as 'CID', Ready-to-Drink as 'RTD'. "
        "Customer segments: ENT=Enterprise, MID=Mid-Market, SMB=Small Business."
    )
    fix_reference: str = (
        "Star schema uses full readable names: category='Beer', segment='Enterprise'. "
        "Codes can exist as secondary columns but primary columns are human-readable."
    )
    severity: int = 5

    code_mappings: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        'category': {'Beer': 'BER', 'Cider': 'CID', 'Ready-to-Drink': 'RTD', 'Non-Alcoholic': 'NAB'},
        'segment': {'Enterprise': 'ENT', 'Mid-Market': 'MID', 'Small Business': 'SMB', 'Independent': 'IND'},
        'subcategory': {
            'Lager': 'LGR', 'Ale': 'ALE', 'IPA': 'IPA', 'Stout': 'STT', 'Pilsner': 'PLS',
            'Apple': 'APL', 'Pear': 'PER', 'Mixed Fruit': 'MXF',
            'Vodka Soda': 'VOD', 'Rum Punch': 'RUM', 'Tequila Mix': 'TEQ',
            'NA Beer': 'NAB', 'Sparkling Water': 'SPA', 'Energy Drink': 'NRG'
        },
        'region': {
            'Northeast': 'NE', 'Southeast': 'SE', 'Midwest': 'MW',
            'Southwest': 'SW', 'West': 'W'
        },
        'channel': {'On-Premise': 'ON', 'Off-Premise': 'OFF', 'E-Commerce': 'EC'},
        'brand': {
            'Northern Brew': 'NB', 'Mountain Gold': 'MG', 'Craft Select': 'CS',
            'Heritage Lager': 'HL', 'Orchard Fresh': 'OF', 'Valley Cider': 'VC',
            'Social Hour': 'SH', 'Party Starter': 'PS', 'Zero Proof': 'ZP',
            'Pure Fizz': 'PF', 'Boost': 'BO'
        },
        'container_type': {'Can': 'C', 'Bottle': 'B', 'Draft': 'D'},
        'pack_size': {'Single': '1PK', '6-Pack': '6PK', '12-Pack': '12PK', '24-Pack': '24PK', 'Keg': 'KEG'},
        'store_type': {
            'Distribution Center': 'DC', 'Regional Warehouse': 'RW', 'Local Depot': 'LD'
        },
        'promotion_type': {
            'Price Discount': 'PD', 'Buy One Get One': 'BOGO', 'Bundle Deal': 'BDL',
            'Loyalty Reward': 'LR', 'Seasonal Special': 'SS'
        }
    })

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Apply cryptic code transformations to categorical columns."""
        df = df.copy()

        for col, mapping in self.code_mappings.items():
            if col in df.columns:
                # At lower intensity, only convert some values
                if intensity < 1.0:
                    mask = np.random.random(len(df)) < intensity
                    df.loc[mask, col] = df.loc[mask, col].map(
                        lambda x: mapping.get(x, x)
                    )
                else:
                    df[col] = df[col].map(lambda x: mapping.get(x, x))

        return df


@dataclass
class InconsistentCasePattern(AntiPattern):
    """Mix camelCase, snake_case, and UPPER_CASE for column names."""

    id: str = "naming_inconsistent_case"
    category: str = "naming"
    name: str = "Inconsistent Case"
    description: str = "Mix camelCase, snake_case, and UPPER_CASE naming conventions"
    why_it_fails: str = (
        "Genie struggles to recognize that 'customer_id', 'customerId', 'CustomerID', "
        "and 'CUSTOMER_ID' might refer to the same concept. Semantic matching fails "
        "when the same concept has inconsistent naming."
    )
    real_world_example: str = (
        "Same table has: net_amount, NetAmount, NET_AMT, netAmt. "
        "Sales team added 'SaleDate', engineering used 'sale_date'."
    )
    fix_reference: str = (
        "Star schema enforces consistent snake_case naming throughout: "
        "customer_key, product_name, net_amount."
    )
    severity: int = 4

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Rename columns with inconsistent casing based on intensity."""
        df = df.copy()

        # Determine how many columns to transform
        n_cols = max(1, int(len(df.columns) * intensity))
        cols_to_transform = random.sample(list(df.columns), n_cols)

        rename_map = {}
        for col in cols_to_transform:
            # Randomly pick a transformation
            transform = random.choice(['upper', 'camel', 'camel_upper', 'abbrev_upper'])

            if transform == 'upper':
                rename_map[col] = col.upper()
            elif transform == 'camel':
                # snake_case to camelCase
                parts = col.split('_')
                rename_map[col] = parts[0] + ''.join(p.title() for p in parts[1:])
            elif transform == 'camel_upper':
                # snake_case to PascalCase
                rename_map[col] = ''.join(p.title() for p in col.split('_'))
            elif transform == 'abbrev_upper':
                # Abbreviate and uppercase
                parts = col.split('_')
                rename_map[col] = ''.join(p[:3].upper() for p in parts)

        return df.rename(columns=rename_map)


@dataclass
class AbbreviationsPattern(AntiPattern):
    """Use cryptic abbreviations without documentation."""

    id: str = "naming_abbreviations"
    category: str = "naming"
    name: str = "Undocumented Abbreviations"
    description: str = "Use abbreviations without documentation (qty, amt, prd, cust)"
    why_it_fails: str = (
        "Abbreviations like 'qty', 'amt', 'prd', 'cust' require domain knowledge "
        "that Genie may not have. Combined with ambiguity (amt of what?), "
        "this leads to misinterpretation."
    )
    real_world_example: str = (
        "Columns named: qty_sld, net_amt, disc_pct, prd_nm, cust_seg, rgn_cd. "
        "No documentation explains these abbreviations."
    )
    fix_reference: str = (
        "Star schema uses full names: quantity_sold, net_amount, discount_percentage, "
        "product_name, customer_segment, region_code."
    )
    severity: int = 4

    abbreviation_map: Dict[str, str] = field(default_factory=lambda: {
        'quantity': 'qty', 'quantity_sold': 'qty_sld', 'units_sold': 'unit_sld',
        'amount': 'amt', 'net_amount': 'net_amt', 'gross_amount': 'gross_amt',
        'discount_amount': 'disc_amt', 'cost_amount': 'cst_amt',
        'profit_amount': 'pft_amt',
        'percentage': 'pct', 'discount_percentage': 'disc_pct',
        'product': 'prd', 'product_name': 'prd_nm', 'product_key': 'prd_key',
        'customer': 'cust', 'customer_name': 'cust_nm', 'customer_key': 'cust_key',
        'segment': 'seg', 'customer_segment': 'cust_seg',
        'region': 'rgn', 'region_code': 'rgn_cd',
        'store': 'str', 'store_key': 'str_key', 'store_name': 'str_nm',
        'date': 'dt', 'date_key': 'dt_key', 'full_date': 'fll_dt',
        'promotion': 'promo', 'promotion_key': 'promo_key',
        'price': 'px', 'unit_price': 'unit_px',
        'cost': 'cst', 'unit_cost': 'unit_cst',
        'year': 'yr', 'month': 'mth', 'day': 'dy', 'quarter': 'qtr',
        'week': 'wk', 'number': 'num', 'code': 'cd',
    })

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Abbreviate column names based on intensity."""
        df = df.copy()

        # Build rename map for columns that exist
        rename_map = {}
        for full_name, abbrev in self.abbreviation_map.items():
            if full_name in df.columns:
                if random.random() < intensity:
                    rename_map[full_name] = abbrev

        return df.rename(columns=rename_map)


@dataclass
class AmbiguousNamesPattern(AntiPattern):
    """Use generic, ambiguous column names."""

    id: str = "naming_ambiguous"
    category: str = "naming"
    name: str = "Ambiguous Names"
    description: str = "Use generic names (flg1, val, amt, cnt, type) without context"
    why_it_fails: str = (
        "Columns named 'flg1', 'val', 'amt', 'cnt', 'type', 'status' are "
        "impossible to interpret without documentation. Genie cannot know "
        "what 'val' represents or what 'flg1' indicates."
    )
    real_world_example: str = (
        "Table has: flg1, flg2, flg3, cd1, code_2, type, status_cd, attr1, attr2, "
        "val, amt, cnt - none documented."
    )
    fix_reference: str = (
        "Star schema uses specific names: is_seasonal (not flg1), "
        "order_status (not status_cd), discount_amount (not amt)."
    )
    severity: int = 5

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add ambiguous columns with unclear names."""
        df = df.copy()

        # Calculate how many ambiguous columns to add
        n_cols = max(1, int(5 * intensity))  # Up to 5 ambiguous columns

        ambiguous_cols = [
            ('flg1', lambda: random.choice([0, 1])),
            ('flg2', lambda: random.choice(['Y', 'N'])),
            ('flg3', lambda: str(random.choice([True, False]))),
            ('cd1', lambda: random.choice(['A', 'B', 'C', 'D'])),
            ('code_2', lambda: random.randint(1, 10)),
            ('type', lambda: random.choice([1, 2, 3])),
            ('status_cd', lambda: random.choice([1, 2, 3, 4, 5])),
            ('attr1', lambda: random.choice(['X', 'Y', 'Z'])),
            ('attr2', lambda: round(random.uniform(0, 100), 2)),
            ('val', lambda: round(random.uniform(0, 1000), 2)),
            ('amt', lambda: round(random.uniform(0, 500), 2)),
            ('cnt', lambda: random.randint(1, 100)),
        ]

        for col_name, gen_fn in ambiguous_cols[:n_cols]:
            if col_name not in df.columns:
                df[col_name] = [gen_fn() for _ in range(len(df))]

        return df


# =============================================================================
# CATEGORY 2: REDUNDANCY ANTI-PATTERNS
# =============================================================================


@dataclass
class DuplicateColumnsPattern(AntiPattern):
    """Create multiple columns with the same data."""

    id: str = "redundancy_duplicate_columns"
    category: str = "redundancy"
    name: str = "Duplicate Columns"
    description: str = "Multiple columns containing the same data with different names"
    why_it_fails: str = (
        "When 'net_amt', 'net_sales', 'NET', 'net_revenue', 'revenue', 'REVENUE', "
        "'REV' all exist, Genie cannot determine which is the canonical source. "
        "Users asking 'what is our revenue?' get ambiguous results."
    )
    real_world_example: str = (
        "Revenue stored 7 ways: net_amt, net_sales, NET, net_revenue, revenue, "
        "REVENUE, REV. Cost stored as: cost_amt, total_cost, COGS."
    )
    fix_reference: str = (
        "Star schema has exactly one column: fact_sales.net_amount. "
        "No synonyms, no duplicates, single source of truth."
    )
    severity: int = 5

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add duplicate columns with different naming conventions."""
        df = df.copy()

        # Mapping of source columns to their duplicates
        duplicate_specs = {
            'net_amount': ['net_amt', 'net_sales', 'NET', 'net_revenue', 'revenue', 'REVENUE', 'REV'],
            'gross_amount': ['gross_amt', 'gross_sales', 'GROSS', 'gross_revenue'],
            'cost_amount': ['cost_amt', 'total_cost', 'COGS'],
            'profit_amount': ['profit', 'profit_amt', 'PROFIT', 'gross_profit', 'margin', 'GP'],
            'quantity_sold': ['qty', 'quantity', 'QTY_SOLD', 'units_sold', 'unit_sold'],
            'unit_price': ['UP', 'px', 'price', 'UNIT_PX'],
            'unit_cost': ['UC', 'cost_per_unit', 'COGS_UNIT'],
            'discount_amount': ['disc_amt', 'discount_amount', 'DISC_$'],
        }

        for source_col, duplicates in duplicate_specs.items():
            if source_col in df.columns:
                # Calculate how many duplicates to add based on intensity
                n_dups = max(1, int(len(duplicates) * intensity))
                selected_dups = random.sample(duplicates, n_dups)

                for dup_name in selected_dups:
                    if dup_name not in df.columns:
                        df[dup_name] = df[source_col]

        return df


@dataclass
class DuplicateIdsPattern(AntiPattern):
    """Create multiple ID columns for the same entity."""

    id: str = "redundancy_duplicate_ids"
    category: str = "redundancy"
    name: str = "Duplicate IDs"
    description: str = "Multiple ID columns for the same entity with different formats"
    why_it_fails: str = (
        "When 'txn_id', 'transaction_id', 'sale_id', 'order_number', 'OrderNum' "
        "all exist, Genie cannot determine which to use for lookups or joins. "
        "Worse, they might not even match!"
    )
    real_world_example: str = (
        "Transaction identified by: txn_id (int), transaction_id (int), "
        "sale_id (int), order_number (ORD-00000001), OrderNum (ORD-00000001)."
    )
    fix_reference: str = (
        "Star schema uses single surrogate key: sale_key. "
        "Natural key stored once as sale_id."
    )
    severity: int = 4

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add duplicate ID columns."""
        df = df.copy()

        id_duplicates = {
            'sale_key': [
                ('txn_id', lambda x: x),
                ('transaction_id', lambda x: x),
                ('sale_id', lambda x: x),
                ('order_number', lambda x: f'ORD-{x:08d}'),
                ('OrderNum', lambda x: f'ORD-{x:08d}'),
            ],
            'product_key': [
                ('prod_id', lambda x: x),
                ('PRDCD', lambda x: f'SKU-{x}'),
                ('product_code', lambda x: f'SKU-{x}'),
            ],
            'customer_key': [
                ('cust_id', lambda x: x),
                ('customer_id', lambda x: f'CUST-{x:05d}'),
                ('CUSTID', lambda x: x),
            ],
            'store_key': [
                ('loc_id', lambda x: x),
                ('store_id', lambda x: x),
                ('dc_code', lambda x: f'DC-{x:03d}'),
            ],
        }

        for source_col, duplicates in id_duplicates.items():
            if source_col in df.columns:
                n_dups = max(1, int(len(duplicates) * intensity))
                selected_dups = random.sample(duplicates, n_dups)

                for dup_name, transform in selected_dups:
                    if dup_name not in df.columns:
                        df[dup_name] = df[source_col].apply(transform)

        return df


@dataclass
class CalculatedStoredPattern(AntiPattern):
    """Store calculated fields alongside their source data."""

    id: str = "redundancy_calculated_stored"
    category: str = "redundancy"
    name: str = "Calculated Fields Stored"
    description: str = "Store gross, discount, net, profit all as columns"
    why_it_fails: str = (
        "When gross_amount, discount_amount, net_amount, and profit are all stored, "
        "Genie doesn't know if values are pre-calculated or need computation. "
        "Rounding errors between calculated and stored values cause confusion."
    )
    real_world_example: str = (
        "Table has: qty, unit_price, gross_amt (should = qty*unit_price), "
        "disc_pct, disc_amt, net_amt, unit_cost, cost_amt, profit. "
        "All calculations pre-stored, potentially inconsistent."
    )
    fix_reference: str = (
        "Star schema stores atomic measures (quantity, unit_price, discount_pct). "
        "Aggregations are computed at query time or in semantic layer."
    )
    severity: int = 3

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add calculated fields with slight variations to create inconsistencies."""
        df = df.copy()

        # Check if we have the necessary base columns
        has_qty = 'quantity_sold' in df.columns or 'qty' in df.columns
        has_price = 'unit_price' in df.columns
        has_net = 'net_amount' in df.columns
        has_cost = 'cost_amount' in df.columns

        if has_qty and has_price:
            qty_col = 'quantity_sold' if 'quantity_sold' in df.columns else 'qty'

            # Add margin percentage calculations
            if has_net and has_cost and 'margin_pct' not in df.columns:
                # Introduce slight rounding variations based on intensity
                if intensity > 0.5:
                    df['margin_pct'] = ((df['net_amount'] - df['cost_amount']) / df['net_amount'] * 100).round(2)
                    df['gm_%'] = ((df['net_amount'] - df['cost_amount']) / df['net_amount'] * 100).round(1)  # Different precision
                    df['profit_margin'] = ((df['net_amount'] - df['cost_amount']) / df['net_amount'] * 100).round(2)

        return df


# =============================================================================
# CATEGORY 3: TYPE ANTI-PATTERNS
# =============================================================================


@dataclass
class MixedBooleansPattern(AntiPattern):
    """Mix different boolean representations."""

    id: str = "type_mixed_booleans"
    category: str = "type"
    name: str = "Mixed Boolean Formats"
    description: str = "Mix 0/1, Y/N, True/False, Active/Inactive representations"
    why_it_fails: str = (
        "When 'is_seasonal' contains 0, 1, 'Y', 'N', True, False as strings, "
        "Genie cannot reliably filter. SQL like WHERE is_seasonal = 1 "
        "misses rows with 'Y' or 'True'."
    )
    real_world_example: str = (
        "is_seasonal: 0, 1, 'Y', 'N', True, False (all as strings). "
        "active: 1, 0, 'A', 'I'. status: 'ACTIVE', 'INACTIVE', 'A', 'I', 'D'."
    )
    fix_reference: str = (
        "Star schema uses native boolean type: is_seasonal BOOLEAN. "
        "Consistent values: true/false only."
    )
    severity: int = 4

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Transform boolean columns to use mixed representations."""
        df = df.copy()

        bool_columns = [col for col in df.columns if df[col].dtype == bool or
                       col.startswith('is_') or col.startswith('has_')]

        bool_representations = [0, 1, 'Y', 'N', 'True', 'False', True, False]

        for col in bool_columns:
            if random.random() < intensity:
                # Convert to mixed representations
                df[col] = df[col].apply(
                    lambda x: random.choice(bool_representations) if random.random() < intensity
                    else ('Y' if x else 'N')
                )
                # Convert to string to ensure type mixing
                df[col] = df[col].astype(str)

        # Add explicit mixed boolean columns
        if intensity > 0.3 and 'seasonal_flg' not in df.columns:
            df['seasonal_flg'] = [random.choice(['Y', 'N']) for _ in range(len(df))]

        if intensity > 0.5 and 'active' not in df.columns:
            df['active'] = [str(random.choice([1, 0, 'A', 'I'])) for _ in range(len(df))]

        if intensity > 0.7 and 'status' not in df.columns:
            df['status'] = [random.choice(['ACTIVE', 'INACTIVE', 'DISCONTINUED', 'A', 'I', 'D'])
                          for _ in range(len(df))]

        return df


@dataclass
class InconsistentDatesPattern(AntiPattern):
    """Mix different date formats."""

    id: str = "type_inconsistent_dates"
    category: str = "type"
    name: str = "Inconsistent Date Formats"
    description: str = "Mix date objects, MM/DD/YYYY, YYYYMMDD, ISO formats"
    why_it_fails: str = (
        "When sale_date is a date object but SaleDate is '01/15/2024' string "
        "and trans_dt is 20240115 integer, Genie must guess formats. "
        "Date filtering becomes unreliable."
    )
    real_world_example: str = (
        "sale_date (date), SaleDate ('01/15/2024'), trans_dt (20240115), "
        "order_date_iso ('2024-01-15T00:00:00'), dt ('15-Jan-2024')."
    )
    fix_reference: str = (
        "Star schema uses DATE type consistently. Date dimension provides "
        "all needed attributes (year, month, quarter) as separate columns."
    )
    severity: int = 5

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add date columns in various formats."""
        df = df.copy()

        # Find date columns
        date_cols = [col for col in df.columns if 'date' in col.lower() or col == 'full_date']

        for col in date_cols:
            if df[col].dtype == 'object' or pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    dates = pd.to_datetime(df[col])
                except (ValueError, TypeError):
                    continue

                # Add various format variations based on intensity
                if intensity > 0.2 and f'{col}_us' not in df.columns:
                    df[f'{col}_us'] = dates.dt.strftime('%m/%d/%Y')  # US format

                if intensity > 0.4 and f'{col}_int' not in df.columns:
                    df[f'{col}_int'] = dates.dt.strftime('%Y%m%d')  # Integer-like

                if intensity > 0.6 and f'{col}_iso' not in df.columns:
                    df[f'{col}_iso'] = dates.apply(lambda x: x.isoformat() if pd.notna(x) else None)

                if intensity > 0.8 and f'{col}_dmy' not in df.columns:
                    df[f'{col}_dmy'] = dates.dt.strftime('%d-%b-%Y')  # DD-Mon-YYYY

        # Add decomposed date columns at high intensity
        if intensity > 0.5:
            for col in date_cols[:1]:  # Just the first date column
                try:
                    dates = pd.to_datetime(df[col])
                    if 'yr' not in df.columns:
                        df['yr'] = dates.dt.year
                    if 'mth' not in df.columns:
                        df['mth'] = dates.dt.month
                    if 'mn' not in df.columns:
                        df['mn'] = dates.dt.month  # Duplicate!
                    if 'dy' not in df.columns:
                        df['dy'] = dates.dt.day
                    if 'dow' not in df.columns:
                        df['dow'] = dates.dt.dayofweek
                    if 'wk' not in df.columns:
                        df['wk'] = dates.dt.isocalendar().week
                    if 'qtr' not in df.columns:
                        df['qtr'] = dates.dt.quarter
                    if 'Q' not in df.columns:
                        df['Q'] = dates.dt.quarter.apply(lambda x: f'Q{x}')
                except (ValueError, TypeError):
                    pass

        return df


@dataclass
class NullVariationsPattern(AntiPattern):
    """Mix different null/missing value representations."""

    id: str = "type_null_variations"
    category: str = "type"
    name: str = "Null Value Variations"
    description: str = "Mix NULL, None, '', 'N/A', -1, 0 representations for missing data"
    why_it_fails: str = (
        "When missing values are represented as NULL, None, empty string, 'N/A', "
        "-1, or 0, Genie's null handling becomes inconsistent. "
        "COUNT(*) vs COUNT(col) gives unexpected results."
    )
    real_world_example: str = (
        "promotion_id: NULL for no promo. promo_cd: '' for no promo. "
        "discount_pct: 0 or -1 for no discount. region: 'N/A' for unknown."
    )
    fix_reference: str = (
        "Star schema uses proper NULL values consistently. "
        "Dimensions have explicit 'Unknown' or 'Not Applicable' rows with key=0."
    )
    severity: int = 4

    null_representations: List[Any] = field(default_factory=lambda: [
        None, '', 'N/A', 'NA', 'NULL', 'null', '-', '--', 'UNKNOWN', 'UNK'
    ])

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Introduce varied null representations."""
        df = df.copy()

        # Find columns with actual nulls - only apply string nulls to object/string columns
        null_cols = [col for col in df.columns if df[col].isna().any()]
        object_cols = df.select_dtypes(include=['object', 'string']).columns

        for col in null_cols:
            if col in object_cols and random.random() < intensity:
                # Replace some nulls with string representations (only for string columns)
                null_mask = df[col].isna()
                null_indices = df[null_mask].index

                for idx in null_indices:
                    if random.random() < intensity:
                        df.at[idx, col] = random.choice(self.null_representations)

        # Introduce nulls as specific values in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if 'key' not in col.lower() and 'id' not in col.lower():
                if random.random() < intensity * 0.5:
                    try:
                        # Mark some values as "missing" using -1, 0, or -999
                        # For unsigned int types, only use 0 to avoid overflow
                        sample_size = max(1, int(len(df) * intensity * 0.05))
                        sample_idx = df.sample(n=sample_size).index

                        if pd.api.types.is_unsigned_integer_dtype(df[col]):
                            df.loc[sample_idx, col] = 0
                        else:
                            df.loc[sample_idx, col] = random.choice([-1, 0, -999])
                    except (ValueError, TypeError):
                        continue

        return df


# =============================================================================
# CATEGORY 4: STRUCTURAL ANTI-PATTERNS
# =============================================================================


@dataclass
class DenormalizationPattern(AntiPattern):
    """Flatten all dimensions into fact table."""

    id: str = "structural_denormalization"
    category: str = "structural"
    name: str = "Denormalization"
    description: str = "Flatten all dimensional attributes into the fact table"
    why_it_fails: str = (
        "When product, customer, store attributes are all flattened into the "
        "fact table, Genie sees 100+ columns. Context window fills with column "
        "names, leaving no room for actual data understanding."
    )
    real_world_example: str = (
        "Super table with: product_name, category, subcategory, brand, "
        "customer_name, segment, region, store_name, store_type... "
        "all in one 120-column table."
    )
    fix_reference: str = (
        "Star schema separates concerns: fact_sales (8 columns) joins to "
        "dim_product, dim_customer, dim_store. Each table focused and manageable."
    )
    severity: int = 5

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """This pattern is applied during data generation, not transformation."""
        # Denormalization happens at generation time, not as a transform
        # This method is a placeholder for consistency
        return df


@dataclass
class ConflictingValuesPattern(AntiPattern):
    """Create columns with same concept but potentially different values."""

    id: str = "structural_conflicting_values"
    category: str = "structural"
    name: str = "Conflicting Values"
    description: str = "Same concept stored multiple times with potentially different values"
    why_it_fails: str = (
        "When credit_limit and cr_lmt exist but have different values for "
        "the same row, Genie cannot determine which is correct. "
        "Data integrity is compromised."
    )
    real_world_example: str = (
        "credit_limit: 50000, cr_lmt: 45000 (same customer, different update times). "
        "prod_id: 1042, product_code: SKU-1047 (mismatch!)."
    )
    fix_reference: str = (
        "Star schema has single source of truth: dim_customer.credit_limit. "
        "No duplicate columns means no conflicts."
    )
    severity: int = 5

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add columns with potentially conflicting values."""
        df = df.copy()

        # Pairs of columns where values might conflict
        conflict_specs = [
            ('credit_limit', 'cr_lmt', lambda x: x * random.choice([0.9, 0.95, 1.0, 1.05, 1.1])),
            ('payment_terms_days', 'pmt_terms', lambda x: x + random.choice([-5, 0, 0, 0, 5])),
            ('product_name', 'prd_nm', lambda x: f'Product {random.randint(1, 150)}'),  # Often mismatches!
            ('region', 'region_name', lambda x: {'Northeast': 'NE', 'Southeast': 'SE', 'Midwest': 'MW', 'Southwest': 'SW', 'West': 'W'}.get(x, x)),
            ('city', 'cty', lambda x: {'New York': 'NYC', 'Boston': 'BOS', 'Miami': 'MIA', 'Chicago': 'CHI', 'Dallas': 'DAL', 'Los Angeles': 'LAX', 'Seattle': 'SEA'}.get(x, x[:3].upper())),
        ]

        for source_col, conflict_col, transform in conflict_specs:
            if source_col in df.columns and random.random() < intensity:
                if conflict_col not in df.columns:
                    # Apply transform which might create conflicts
                    df[conflict_col] = df[source_col].apply(transform)

        return df


@dataclass
class OrphanKeysPattern(AntiPattern):
    """Create foreign keys that don't match dimension keys."""

    id: str = "structural_orphan_keys"
    category: str = "structural"
    name: str = "Orphan Keys"
    description: str = "Foreign keys that reference non-existent dimension records"
    why_it_fails: str = (
        "When fact_sales.product_key references a product_key that doesn't "
        "exist in dim_product, joins fail silently. Genie may return "
        "incomplete results without warning."
    )
    real_world_example: str = (
        "Sales record references product_key=9999 but dim_product only goes "
        "to 1200. Customer merged, old customer_key orphaned."
    )
    fix_reference: str = (
        "Star schema enforces referential integrity. "
        "ETL processes validate all foreign keys before loading."
    )
    severity: int = 4

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Introduce orphan key references."""
        df = df.copy()

        key_columns = [col for col in df.columns if col.endswith('_key')]

        for col in key_columns:
            if random.random() < intensity:
                try:
                    # Only apply to numeric key columns
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        continue

                    # Get max existing key
                    max_key = pd.to_numeric(df[col], errors='coerce').max()
                    if pd.isna(max_key):
                        continue

                    # Introduce some orphan keys
                    n_orphans = max(1, int(len(df) * intensity * 0.02))
                    orphan_indices = df.sample(n=n_orphans).index

                    for idx in orphan_indices:
                        # Set to a key that likely doesn't exist
                        df.loc[idx, col] = int(max_key) + random.randint(1000, 9999)
                except (TypeError, ValueError):
                    # Skip columns that can't be processed
                    continue

        return df


# =============================================================================
# CATEGORY 5: METADATA ANTI-PATTERNS
# =============================================================================


@dataclass
class NoDescriptionsPattern(AntiPattern):
    """Tables and columns without descriptions."""

    id: str = "metadata_no_descriptions"
    category: str = "metadata"
    name: str = "No Descriptions"
    description: str = "Remove/don't add column descriptions or table documentation"
    why_it_fails: str = (
        "Without column descriptions, Genie relies entirely on column names "
        "for semantic understanding. Names like 'amt', 'val', 'flg1' "
        "provide no context."
    )
    real_world_example: str = (
        "Unity Catalog table with 120 columns, no descriptions. "
        "Genie cannot understand what gm_% means without documentation."
    )
    fix_reference: str = (
        "Star schema includes rich metadata: column descriptions, "
        "business definitions, example values, valid ranges."
    )
    severity: int = 3

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """This pattern affects metadata, not data. Placeholder for consistency."""
        # This pattern is enforced at catalog/schema level, not DataFrame level
        return df


@dataclass
class UndocumentedCodesPattern(AntiPattern):
    """Status codes and flags without lookup documentation."""

    id: str = "metadata_undocumented_codes"
    category: str = "metadata"
    name: str = "Undocumented Codes"
    description: str = "Status codes (1, 2, 3, 4, 5) without lookup table or documentation"
    why_it_fails: str = (
        "When status_cd contains 1-5 with no documentation, Genie can "
        "filter and count but cannot explain meaning. User asks "
        "'how many pending orders?' and Genie doesn't know which code is pending."
    )
    real_world_example: str = (
        "status_cd: 1=Pending, 2=Shipped, 3=Delivered, 4=Returned, 5=Cancelled. "
        "Nowhere documented. Only tribal knowledge."
    )
    fix_reference: str = (
        "Star schema has dim_status with readable names. "
        "Or uses enum types with meaningful values: 'Pending', 'Shipped', etc."
    )
    severity: int = 4

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add undocumented status code columns."""
        df = df.copy()

        if intensity > 0.3 and 'status_cd' not in df.columns:
            df['status_cd'] = [random.choice([1, 2, 3, 4, 5]) for _ in range(len(df))]

        if intensity > 0.5 and 'priority_cd' not in df.columns:
            df['priority_cd'] = [random.choice([1, 2, 3]) for _ in range(len(df))]

        if intensity > 0.7 and 'approval_cd' not in df.columns:
            df['approval_cd'] = [random.choice(['A', 'P', 'R', 'H']) for _ in range(len(df))]

        return df


@dataclass
class HiddenLogicPattern(AntiPattern):
    """Embed business logic without documentation."""

    id: str = "metadata_hidden_logic"
    category: str = "metadata"
    name: str = "Hidden Business Logic"
    description: str = "Embed business logic (fiscal calendar, calculations) without documentation"
    why_it_fails: str = (
        "When fiscal_year starts in February (beverage industry standard) "
        "but this is undocumented, Genie assumes calendar year. "
        "Queries about 'last fiscal year' return wrong data."
    )
    real_world_example: str = (
        "fy column uses Feb-Jan fiscal year. fq column is fiscal quarter. "
        "margin calculated as (net-cost)/net but could be /gross. Undocumented."
    )
    fix_reference: str = (
        "Star schema documents all business logic. dim_date has clear "
        "fiscal_year, fiscal_quarter columns with descriptions explaining the Feb start."
    )
    severity: int = 4

    def apply(self, df: pd.DataFrame, intensity: float = 1.0) -> pd.DataFrame:
        """Add columns with hidden business logic."""
        df = df.copy()

        # Find date columns to add fiscal calculations
        date_cols = [col for col in df.columns if 'date' in col.lower()]

        if date_cols and intensity > 0.3:
            try:
                dates = pd.to_datetime(df[date_cols[0]])

                # Add fiscal year (Feb start) without documentation
                if 'fy' not in df.columns:
                    df['fy'] = dates.apply(lambda d: d.year if d.month >= 2 else d.year - 1)

                # Add fiscal quarter without documentation
                if 'fq' not in df.columns:
                    df['fq'] = dates.apply(lambda d: ((d.month - 2) % 12) // 3 + 1)

            except (ValueError, TypeError):
                pass

        return df


# =============================================================================
# ANTI-PATTERN REGISTRY
# =============================================================================


class AntiPatternRegistry:
    """
    Registry of all available anti-patterns.

    Provides methods to retrieve patterns by ID, category, or cleanliness level.
    """

    def __init__(self) -> None:
        """Initialize the registry with all built-in patterns."""
        self._patterns: Dict[str, AntiPattern] = {}
        self._register_all_patterns()

    def _register_all_patterns(self) -> None:
        """Register all built-in anti-patterns."""
        patterns = [
            # Naming patterns
            CrypticCodesPattern(),
            InconsistentCasePattern(),
            AbbreviationsPattern(),
            AmbiguousNamesPattern(),
            # Redundancy patterns
            DuplicateColumnsPattern(),
            DuplicateIdsPattern(),
            CalculatedStoredPattern(),
            # Type patterns
            MixedBooleansPattern(),
            InconsistentDatesPattern(),
            NullVariationsPattern(),
            # Structural patterns
            DenormalizationPattern(),
            ConflictingValuesPattern(),
            OrphanKeysPattern(),
            # Metadata patterns
            NoDescriptionsPattern(),
            UndocumentedCodesPattern(),
            HiddenLogicPattern(),
        ]

        for pattern in patterns:
            self._patterns[pattern.id] = pattern

    def register(self, pattern: AntiPattern) -> None:
        """
        Register a custom anti-pattern.

        Args:
            pattern: Anti-pattern instance to register
        """
        self._patterns[pattern.id] = pattern

    def get(self, pattern_id: str) -> AntiPattern:
        """
        Get pattern by ID.

        Args:
            pattern_id: Unique pattern identifier

        Returns:
            AntiPattern instance

        Raises:
            KeyError: If pattern ID not found
        """
        if pattern_id not in self._patterns:
            raise KeyError(f"Pattern '{pattern_id}' not found. Available: {list(self._patterns.keys())}")
        return self._patterns[pattern_id]

    def get_by_category(self, category: str) -> List[AntiPattern]:
        """
        Get all patterns in a category.

        Args:
            category: Category name ('naming', 'redundancy', 'type', 'structural', 'metadata')

        Returns:
            List of AntiPattern instances in that category
        """
        return [p for p in self._patterns.values() if p.category == category]

    def get_all(self) -> List[AntiPattern]:
        """
        Get all registered patterns.

        Returns:
            List of all AntiPattern instances
        """
        return list(self._patterns.values())

    def get_active_patterns(self, cleanliness: int) -> List[str]:
        """
        Get pattern IDs that should be active at given cleanliness level.

        Higher severity patterns activate at higher cleanliness thresholds:
        - severity 5: activates below cleanliness 80
        - severity 4: activates below cleanliness 65
        - severity 3: activates below cleanliness 50
        - severity 2: activates below cleanliness 35
        - severity 1: activates below cleanliness 20

        Args:
            cleanliness: Cleanliness level (0-100)

        Returns:
            List of pattern IDs that should be active
        """
        severity_thresholds = {
            5: 80,  # Most severe - activates when cleanliness drops below 80
            4: 65,
            3: 50,
            2: 35,
            1: 20,  # Least severe - only at very low cleanliness
        }

        active = []
        for pattern_id, pattern in self._patterns.items():
            threshold = severity_thresholds.get(pattern.severity, 50)
            if cleanliness < threshold:
                active.append(pattern_id)

        return active

    def calculate_intensity(self, cleanliness: int, severity: int) -> float:
        """
        Calculate pattern intensity based on cleanliness and severity.

        Args:
            cleanliness: Cleanliness level (0-100)
            severity: Pattern severity (1-5)

        Returns:
            Intensity value (0.0-1.0)
        """
        # Base intensity from cleanliness (inverted: lower cleanliness = higher intensity)
        base_intensity = (100 - cleanliness) / 100

        # Severity multiplier (higher severity = applied more strongly)
        severity_multiplier = severity / 5

        # Combined intensity
        intensity = base_intensity * severity_multiplier

        # Ensure bounds
        return max(0.0, min(1.0, intensity))

    def apply_by_cleanliness(
        self,
        df: pd.DataFrame,
        cleanliness: int,
        categories: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Apply anti-patterns based on cleanliness level.

        Lower cleanliness levels activate more patterns with higher intensity.

        Args:
            df: Input DataFrame
            cleanliness: Cleanliness level (0-100)
            categories: Optional list of categories to include. If None, all categories.
            exclude_patterns: Optional list of pattern IDs to exclude

        Returns:
            DataFrame with anti-patterns applied
        """
        df = df.copy()
        exclude_patterns = exclude_patterns or []

        active_pattern_ids = self.get_active_patterns(cleanliness)

        for pattern_id in active_pattern_ids:
            if pattern_id in exclude_patterns:
                continue

            pattern = self._patterns[pattern_id]

            # Filter by category if specified
            if categories and pattern.category not in categories:
                continue

            # Calculate intensity for this pattern
            intensity = self.calculate_intensity(cleanliness, pattern.severity)

            # Apply the pattern
            try:
                df = pattern.apply(df, intensity)
            except Exception as e:
                # Log but don't fail - patterns should be resilient
                print(f"Warning: Pattern '{pattern_id}' failed to apply: {e}")

        return df

    def describe_active_patterns(self, cleanliness: int) -> str:
        """
        Generate a description of what patterns are active at a cleanliness level.

        Args:
            cleanliness: Cleanliness level (0-100)

        Returns:
            Formatted string describing active patterns
        """
        active_ids = self.get_active_patterns(cleanliness)

        if not active_ids:
            return f"At cleanliness {cleanliness}, no anti-patterns are active (pristine data)."

        lines = [f"Active anti-patterns at cleanliness {cleanliness}:"]
        lines.append("-" * 60)

        # Group by category
        by_category: Dict[str, List[AntiPattern]] = {}
        for pattern_id in active_ids:
            pattern = self._patterns[pattern_id]
            if pattern.category not in by_category:
                by_category[pattern.category] = []
            by_category[pattern.category].append(pattern)

        for category in ['naming', 'redundancy', 'type', 'structural', 'metadata']:
            if category in by_category:
                lines.append(f"\n{category.upper()}:")
                for pattern in by_category[category]:
                    intensity = self.calculate_intensity(cleanliness, pattern.severity)
                    lines.append(f"  - {pattern.name} (severity: {pattern.severity}, intensity: {intensity:.1%})")
                    lines.append(f"    Why it fails: {pattern.why_it_fails[:80]}...")

        return "\n".join(lines)


# Module-level singleton for convenience
_registry: Optional[AntiPatternRegistry] = None


def get_registry() -> AntiPatternRegistry:
    """
    Get the singleton anti-pattern registry.

    Returns:
        AntiPatternRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AntiPatternRegistry()
    return _registry
