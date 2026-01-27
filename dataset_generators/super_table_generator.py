"""
Super Table Dataset Generator - BAD Data Engineering Example
============================================================

This generates a denormalized "super table" that represents common anti-patterns.
Demonstrates what NOT to do when designing data for AI/BI tools.

Anti-patterns included:
1. All data flattened into one massive table (100+ columns)
2. Inconsistent naming conventions
3. Cryptic abbreviations
4. Duplicate/redundant columns
5. Mixed data formats
6. Ambiguous column names
7. No clear relationships
8. Calculated fields stored with raw data
9. Multiple date formats
10. Status codes without lookup

Why Genie will struggle:
- Too many columns to fit in context
- Ambiguous column names require guessing
- No clear business meaning without documentation
- Redundant columns cause confusion
- Inconsistent naming makes pattern matching fail
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)


def generate_super_table(n_rows: int = 50000) -> pd.DataFrame:
    """
    Generate a horribly denormalized super table with all the anti-patterns.
    """

    # Generate base dates
    dates = pd.date_range(start="2023-01-01", end="2025-12-31", freq='D').tolist()

    records = []

    for i in range(1, n_rows + 1):
        sale_date = random.choice(dates)

        # Product info (with terrible naming)
        category_code = random.choice(['BER', 'CID', 'RTD', 'NAB'])
        subcategory = random.choice(['LGR', 'ALE', 'IPA', 'STT', 'APL', 'PER', 'VOD', 'RUM', 'NAB', 'SPA', 'NRG'])

        # Customer info (inconsistent naming)
        cust_segment = random.choice(['ENT', 'MID', 'SMB', 'IND'])
        region_code = random.choice([1, 2, 3, 4, 5])

        # Pricing (multiple redundant columns)
        qty = random.randint(1, 48)
        unit_px = round(random.uniform(1.50, 6.00), 2)
        unit_cst = round(random.uniform(0.80, 3.50), 2)
        disc_pct = random.choice([0, 0, 0, 5, 10, 15, 20])

        gross = qty * unit_px
        disc_amt = gross * (disc_pct / 100)
        net = gross - disc_amt
        cost = qty * unit_cst
        profit = net - cost

        records.append({
            # Transaction IDs (redundant)
            'txn_id': i,
            'transaction_id': i,
            'sale_id': i,
            'order_number': f'ORD-{i:08d}',
            'OrderNum': f'ORD-{i:08d}',  # Duplicate with different name

            # Dates in multiple formats (inconsistent)
            'sale_date': sale_date.date(),
            'SaleDate': sale_date.strftime('%m/%d/%Y'),  # US format string
            'trans_dt': sale_date.strftime('%Y%m%d'),  # YYYYMMDD integer-like
            'order_date_iso': sale_date.isoformat(),
            'dt': sale_date.strftime('%d-%b-%Y'),  # 01-Jan-2024 format
            'yr': sale_date.year,
            'mth': sale_date.month,
            'mn': sale_date.month,  # Duplicate
            'dy': sale_date.day,
            'dow': sale_date.dayofweek,
            'wk': sale_date.isocalendar()[1],
            'qtr': (sale_date.month - 1) // 3 + 1,
            'Q': f'Q{(sale_date.month - 1) // 3 + 1}',  # Another qtr format
            'fy': sale_date.year if sale_date.month >= 2 else sale_date.year - 1,
            'fq': ((sale_date.month - 2) % 12) // 3 + 1,

            # Product columns (cryptic codes)
            'prod_id': random.randint(1000, 1200),
            'PRDCD': f'SKU-{random.randint(1000, 1200)}',
            'product_code': f'SKU-{random.randint(1000, 1200)}',  # May not match!
            'prd_nm': f'Product {random.randint(1, 150)}',
            'product_name': f'Product Name {random.randint(1, 150)}',  # Different!
            'cat': category_code,
            'CAT_CD': category_code,
            'category_code': category_code,
            'category': {'BER': 'Beer', 'CID': 'Cider', 'RTD': 'Ready-to-Drink', 'NAB': 'Non-Alcoholic'}[category_code],
            'CATEGORY': {'BER': 'BEER', 'CID': 'CIDER', 'RTD': 'RTD', 'NAB': 'NA'}[category_code],  # Different again!
            'subcat': subcategory,
            'sub_category': subcategory,
            'brnd': random.choice(['NB', 'MG', 'CS', 'HL', 'OF', 'VC', 'SH', 'PS', 'ZP', 'PF', 'BO']),
            'brand_code': random.choice(['NORTH', 'MOUNT', 'CRAFT', 'HERIT', 'ORCH', 'VALL', 'SOC', 'PARTY', 'ZERO', 'PURE', 'BOOST']),
            'pck_sz': random.choice(['1PK', '6PK', '12PK', '24PK', 'KEG']),
            'pack': random.choice([1, 6, 12, 24, 1]),
            'ctnr': random.choice(['C', 'B', 'D']),  # Can, Bottle, Draft
            'container_type': random.choice(['CAN', 'BTL', 'DFT']),
            'vol_ml': random.choice([355, 473, 500, 650]),
            'abv': 0.0 if category_code == 'NAB' else round(random.uniform(4.0, 8.5), 1),
            'alc_pct': 0.0 if category_code == 'NAB' else round(random.uniform(4.0, 8.5), 1),  # Duplicate
            'is_seasonal': str(random.choice([0, 1, 'Y', 'N', True, False])),  # Inconsistent!
            'seasonal_flg': random.choice(['Y', 'N']),
            'active': str(random.choice([1, 0, 'A', 'I'])),  # Mixed format
            'status': random.choice(['ACTIVE', 'INACTIVE', 'DISCONTINUED', 'A', 'I', 'D']),

            # Customer columns (inconsistent)
            'cust_id': random.randint(1, 500),
            'customer_id': f'CUST-{random.randint(1, 500):05d}',
            'CUSTID': random.randint(1, 500),  # Different format
            'cust_nm': f'Customer {random.randint(1, 500)}',
            'cust_type': random.choice(['BR', 'LS', 'GR', 'CS', 'HT', 'SV']),
            'customer_type': random.choice(['Bar/Restaurant', 'Liquor Store', 'Grocery', 'Convenience', 'Hotel', 'Stadium']),
            'seg': cust_segment,
            'segment': {'ENT': 'Enterprise', 'MID': 'Mid-Market', 'SMB': 'Small Business', 'IND': 'Independent'}[cust_segment],
            'SEGMENT_CODE': cust_segment,
            'chnl': random.choice(['ON', 'OFF', 'EC']),
            'channel': random.choice(['On-Premise', 'Off-Premise', 'E-Commerce']),
            'rgn': region_code,
            'region': {1: 'Northeast', 2: 'Southeast', 3: 'Midwest', 4: 'Southwest', 5: 'West'}[region_code],
            'REGION_CD': region_code,
            'region_name': {1: 'NE', 2: 'SE', 3: 'MW', 4: 'SW', 5: 'W'}[region_code],  # Different!
            'city': random.choice(['New York', 'Boston', 'Miami', 'Chicago', 'Dallas', 'LA', 'Seattle']),
            'cty': random.choice(['NYC', 'BOS', 'MIA', 'CHI', 'DAL', 'LAX', 'SEA']),  # Codes
            'cr_lmt': random.choice([5000, 10000, 25000, 50000, 100000]),
            'credit_limit': random.choice([5000, 10000, 25000, 50000, 100000]),  # May differ!
            'pmt_terms': random.choice([15, 30, 45, 60]),
            'payment_terms_days': random.choice([15, 30, 45, 60]),  # May differ!
            'acct_mgr': f'Rep-{random.randint(1, 20):02d}',
            'rep_id': random.randint(1, 20),

            # Store/Location (cryptic)
            'loc_id': random.randint(1, 80),
            'store_id': random.randint(1, 80),  # May not match!
            'dc_code': f'DC-{random.randint(1, 80):03d}',
            'loc_type': random.choice(['DC', 'RW', 'LD']),
            'facility_type': random.choice(['Distribution Center', 'Regional Warehouse', 'Local Depot']),
            'st': random.choice(['NY', 'CA', 'TX', 'FL', 'IL']),
            'state': random.choice(['New York', 'California', 'Texas', 'Florida', 'Illinois']),
            'sqft': random.randint(10000, 100000),

            # Promotion (ambiguous)
            'promo_id': random.choice([None, random.randint(1, 50)]),
            'promo_cd': random.choice([None, f'PROMO-{random.randint(1, 50):03d}']),
            'has_promo': str(random.choice([0, 1, 'Y', 'N', True, False, ''])),
            'promo_type': random.choice([None, 'PD', 'BOGO', 'BDL', 'LR', 'SS']),
            'disc': disc_pct,
            'discount_pct': disc_pct,
            'disc_%': disc_pct,  # Another format

            # Quantity/Amount columns (many redundant calculations)
            'qty': qty,
            'quantity': qty,
            'QTY_SOLD': qty,
            'units': qty * random.choice([1, 6, 12, 24]),
            'unit_sold': qty,  # Confusing - packs or units?

            'unit_price': unit_px,
            'UP': unit_px,
            'px': unit_px,
            'price': unit_px,
            'UNIT_PX': unit_px,

            'unit_cost': unit_cst,
            'UC': unit_cst,
            'cost_per_unit': unit_cst,
            'COGS_UNIT': unit_cst,

            'gross_amt': round(gross, 2),
            'gross_sales': round(gross, 2),
            'GROSS': round(gross, 2),
            'gross_revenue': round(gross, 2),  # Same thing, different name

            'disc_amt': round(disc_amt, 2),
            'discount_amount': round(disc_amt, 2),
            'DISC_$': round(disc_amt, 2),

            'net_amt': round(net, 2),
            'net_sales': round(net, 2),
            'NET': round(net, 2),
            'net_revenue': round(net, 2),
            'revenue': round(net, 2),  # Which one is THE revenue?
            'REVENUE': round(net, 2),
            'REV': round(net, 2),

            'cost_amt': round(cost, 2),
            'total_cost': round(cost, 2),
            'COGS': round(cost, 2),

            'profit': round(profit, 2),
            'profit_amt': round(profit, 2),
            'PROFIT': round(profit, 2),
            'gross_profit': round(profit, 2),  # Is this gross or net profit?
            'margin': round(profit, 2),
            'GP': round(profit, 2),

            'margin_pct': round((profit / net * 100) if net > 0 else 0, 2),
            'gm_%': round((profit / net * 100) if net > 0 else 0, 2),
            'profit_margin': round((profit / net * 100) if net > 0 else 0, 2),

            # Random flags and codes
            'flg1': random.choice([0, 1]),
            'flg2': random.choice(['Y', 'N']),
            'flg3': str(random.choice([True, False])),
            'cd1': random.choice(['A', 'B', 'C', 'D']),
            'code_2': random.randint(1, 10),
            'type': random.choice([1, 2, 3]),  # Type of what?
            'status_cd': random.choice([1, 2, 3, 4, 5]),  # Meaningless without lookup
            'attr1': random.choice(['X', 'Y', 'Z']),
            'attr2': random.uniform(0, 100),
            'val': random.uniform(0, 1000),  # Value of what?
            'amt': random.uniform(0, 500),  # Amount of what?
            'cnt': random.randint(1, 100),  # Count of what?

            # Timestamps in various formats
            'created_at': (sale_date + timedelta(hours=random.randint(0, 23))).isoformat(),
            'modified_dt': sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            'last_update': sale_date.strftime('%m/%d/%y'),
            'etl_timestamp': datetime.now().isoformat(),
        })

    df = pd.DataFrame(records)

    print(f"\nSuper Table Generated:")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")
    print(f"\nColumn name samples (showing the chaos):")
    print(f"  Revenue columns: net_amt, net_sales, NET, net_revenue, revenue, REVENUE, REV")
    print(f"  Quantity columns: qty, quantity, QTY_SOLD, units, unit_sold")
    print(f"  Date columns: sale_date, SaleDate, trans_dt, order_date_iso, dt")

    return df


def save_super_table(output_dir: str = "./data/super_table"):
    """Save the super table to parquet."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    df = generate_super_table(50000)
    path = os.path.join(output_dir, 'super_table.parquet')
    df.to_parquet(path, index=False)
    print(f"\nSaved to {path}")

    return df


# Questions that will confuse Genie with the super table
FAILURE_SCENARIOS = """
================================================================================
QUESTIONS THAT WILL CONFUSE GENIE (Super Table Anti-Patterns)
================================================================================

1. AMBIGUOUS COLUMN NAMES
   Question: "What was our total revenue last quarter?"
   Problem: Which column is revenue? net_amt, net_sales, NET, net_revenue,
            revenue, REVENUE, REV all exist. Genie may pick wrong one or ask.

2. DUPLICATE/INCONSISTENT IDS
   Question: "Show me details for transaction 12345"
   Problem: txn_id, transaction_id, sale_id, order_number, OrderNum all exist.
            Some may have different values for same row!

3. CRYPTIC CODES WITHOUT DOCUMENTATION
   Question: "What is the breakdown by customer segment?"
   Problem: 'seg' column has ENT, MID, SMB, IND codes. Without documentation,
            Genie doesn't know ENT = Enterprise.

4. INCONSISTENT BOOLEAN/FLAG FORMATS
   Question: "Show only seasonal products"
   Problem: is_seasonal has mixed values: 0, 1, 'Y', 'N', True, False
            seasonal_flg has 'Y', 'N'. Which to use? How to filter?

5. MULTIPLE DATE FORMATS
   Question: "Show sales from January 2024"
   Problem: sale_date (date), SaleDate ('01/15/2024'), trans_dt ('20240115'),
            order_date_iso ('2024-01-15T00:00:00'), dt ('15-Jan-2024')
            Different formats = different SQL needed.

6. CONFLICTING CALCULATIONS
   Question: "What is our gross margin?"
   Problem: margin, margin_pct, gm_%, profit_margin exist.
            margin = dollar amount, margin_pct = percentage. Confusing!

7. STATUS CODES WITHOUT MEANING
   Question: "How many orders have status code 3?"
   Problem: status_cd has values 1-5 with no documentation.
            Genie can count them but can't explain what status 3 means.

8. AMBIGUOUS AGGREGATION
   Question: "What is our average order value?"
   Problem: Should Genie use qty (pack quantity) or units (individual units)?
            Which amount field? gross_amt, net_amt, revenue?

9. REGIONAL INCONSISTENCY
   Question: "Show sales by region"
   Problem: rgn (1-5), region ('Northeast'), REGION_CD (1-5),
            region_name ('NE') - all different formats/values!

10. PRODUCT HIERARCHY CONFUSION
    Question: "Show sales by brand"
    Problem: brnd ('NB'), brand_code ('NORTH') - which is correct?
             No clear mapping between abbreviated and full names.

================================================================================
WHY STAR SCHEMA FIXES THESE PROBLEMS:
================================================================================

1. Single source of truth for each concept (dim_customer.segment)
2. Clear, documented column names (customer_name, not cust_nm)
3. Consistent data types (all booleans are booleans)
4. Proper relationships via keys (join on customer_key)
5. Business-friendly names (fiscal_quarter_name, not fq)
6. Separated concerns (facts vs dimensions)
7. No redundant columns (one revenue column, not seven)
================================================================================
"""


if __name__ == "__main__":
    df = save_super_table()

    print("\n" + "="*80)
    print("ANTI-PATTERNS IN THIS TABLE:")
    print("="*80)
    print(FAILURE_SCENARIOS)
