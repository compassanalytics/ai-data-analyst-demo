"""
Finance Banking Dataset - Dirty Super Table Generator
======================================================

Generates a denormalized "super table" with intentional anti-patterns
to demonstrate why proper data engineering matters for AI/BI tools.

FAILURE SCENARIOS DEMONSTRATED:
-------------------------------

1. **Ambiguous Transaction Amounts**
   - 8 different amount columns: amt, amount, AMT, amount_usd, amount_local,
     local_amt, trans_amt, TRANS_AMT
   - AI cannot determine which to use for revenue calculations

2. **Duplicate IDs with Different Formats**
   - 6 transaction ID columns, 6 account columns, 6 customer columns
   - Breaks JOIN logic and deduplication

3. **Inconsistent Date Formats**
   - 10+ date columns with formats: date, MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, DD-Mon-YYYY
   - Separate yr, mth, dy columns that don't align
   - Calendar vs Fiscal quarter confusion

4. **Cryptic Codes vs Readable Values**
   - Segment: 'R' vs 'Retail', 'MA' vs 'Mass Affluent'
   - Risk: 'L' vs 'Low', 'MH' vs 'Medium-High'
   - Type: numeric 1-6 vs code vs name
   - Channel: numeric vs name

5. **Inconsistent Boolean Formats**
   - is_pending: mix of 0, 1, 'Y', 'N', True, False
   - Breaks filter logic

6. **Balance Confusion**
   - 12 balance columns with overlapping semantics
   - current_balance, curr_bal, BAL, available_balance, avail_bal, etc.

7. **Mystery Columns**
   - cd1, cd2, val, cnt, attr1, flg1, flg2
   - No documentation, unclear meaning
"""

import os
import random
from datetime import datetime, timedelta
import uuid

import pandas as pd
from faker import Faker

fake = Faker('en_US')

# Failure scenario documentation
FINANCE_FAILURE_SCENARIOS = """
FINANCE BANKING DATASET - FAILURE SCENARIOS
============================================

1. AMBIGUOUS TRANSACTION AMOUNTS
   - Question: "What was total transaction volume last month?"
   - Problem: 8 different amount columns exist
   - Columns: amt, amount, AMT, amount_usd, amount_local, local_amt, trans_amt, TRANS_AMT
   - Result: AI picks wrong column, gets wrong answer

2. DUPLICATE/INCONSISTENT IDS
   - Question: "How many unique customers do we have?"
   - Problem: 6 different customer ID columns with different formats
   - Columns: cust_id (CUST-000001), customer_id (numeric), CUSTID (uppercase),
              party_id (PTY-xxx), client_id (CLT-xxx), tax_id (masked)
   - Result: Different counts depending on column used

3. DATE FORMAT CHAOS
   - Question: "What was Q1 revenue?"
   - Problem: Uses calendar Q1 when data has fiscal Q1 (starts Feb)
   - Columns: trans_date (date), transaction_date (MM/DD/YYYY), posting_date (YYYY-MM-DD),
              effective_date (YYYYMMDD), settle_dt (DD-Mon-YYYY), separate yr/mth/dy
   - Result: Wrong quarter boundaries, incorrect totals

4. CRYPTIC SEGMENT CODES
   - Question: "Show transactions by customer segment"
   - Problem: Returns codes like 'R', 'MA', 'HNW' instead of readable names
   - Columns: seg (code), segment (name), SEGMENT_CD (code), cust_seg (mixed)
   - Result: Meaningless output, user confusion

5. BOOLEAN INCONSISTENCY
   - Question: "Show only pending transactions"
   - Problem: is_pending contains: 0, 1, 'Y', 'N', True, False, 'Yes', 'No'
   - Result: Partial matches, missed records, incorrect filtering

6. BALANCE AMBIGUITY
   - Question: "What is the total balance across all accounts?"
   - Problem: 12 balance columns with overlapping/confusing semantics
   - Columns: balance, bal, BAL, current_balance, curr_bal, available_balance,
              avail_bal, ledger_balance, ldgr_bal, memo_balance, hold_amount, hold_amt
   - Result: AI may sum related columns, double-counting
"""


def generate_finance_super_table(n_rows: int = 500000) -> pd.DataFrame:
    """
    Generate a denormalized super table with intentional anti-patterns.

    This table demonstrates common data quality issues that cause AI/BI
    tools to fail or produce incorrect results.

    Args:
        n_rows: Number of rows to generate

    Returns:
        DataFrame with anti-patterns embedded
    """
    records = []

    # Pre-generate some reference data for consistency
    regions = ['Northeast', 'Southeast', 'Midwest', 'Southwest', 'West']
    region_codes = ['NE', 'SE', 'MW', 'SW', 'W']

    segments = ['Retail', 'Mass Affluent', 'High Net Worth', 'Private Banking', 'Institutional']
    segment_codes = ['R', 'MA', 'HNW', 'PB', 'INST']

    risk_names = ['Low', 'Medium', 'Medium-High', 'High']
    risk_codes = ['L', 'M', 'MH', 'H']

    kyc_names = ['Verified', 'Pending', 'Expired', 'Enhanced Due Diligence']
    kyc_codes = ['V', 'P', 'X', 'EDD']

    tx_types = [
        ('DEP', 'Deposit', 1),
        ('WD', 'Withdrawal', 2),
        ('TRF', 'Transfer', 3),
        ('PYM', 'Payment', 4),
        ('FEE', 'Fee', 5),
        ('INT', 'Interest', 6),
    ]

    channels = ['Online Banking', 'Mobile App', 'ATM', 'Branch', 'Wire', 'ACH']
    channel_nums = [1, 2, 3, 4, 5, 6]

    # Generate a pool of consistent IDs to reuse
    num_customers = min(n_rows // 10, 50000)
    num_accounts = min(n_rows // 5, 80000)

    customer_ids = [f'CUST-{i:06d}' for i in range(1, num_customers + 1)]
    customer_nums = list(range(1, num_customers + 1))
    party_ids = [f'PTY-{i:08d}' for i in range(100000, 100000 + num_customers)]
    client_ids = [f'CLT-{i:07d}' for i in range(1, num_customers + 1)]

    account_nums = [''.join([str(random.randint(0, 9)) for _ in range(10)]) for _ in range(num_accounts)]

    for i in range(n_rows):
        # Generate base transaction date
        days_ago = random.randint(0, 730)
        tx_date = datetime.now() - timedelta(days=days_ago)

        # Add time component
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        tx_datetime = tx_date.replace(hour=hour, minute=minute, second=second)

        # Select transaction type
        tx_code, tx_name, tx_num = random.choice(tx_types)

        # Generate amount (lognormal, median ~400)
        amount = random.lognormvariate(6, 1.5)
        amount = min(amount, 50000)
        amount = round(amount, 2)

        # FX rate for non-USD
        is_usd = random.random() < 0.75
        if is_usd:
            fx_rate = 1.0
            ccy = 'USD'
            ccy_name = 'US Dollar'
            iso_code = 840
        else:
            fx_rate = round(random.uniform(0.7, 1.5), 4)
            ccy = random.choice(['EUR', 'GBP', 'CAD', 'CHF'])
            ccy_names = {'EUR': 'Euro', 'GBP': 'British Pound', 'CAD': 'Canadian Dollar', 'CHF': 'Swiss Franc'}
            iso_codes = {'EUR': 978, 'GBP': 826, 'CAD': 124, 'CHF': 756}
            ccy_name = ccy_names[ccy]
            iso_code = iso_codes[ccy]

        amount_usd = round(amount * fx_rate, 2)

        # Select customer
        cust_idx = random.randint(0, len(customer_ids) - 1)
        acct_idx = random.randint(0, len(account_nums) - 1)

        # Select segment and risk
        seg_idx = random.choices(range(5), weights=[0.50, 0.25, 0.15, 0.07, 0.03])[0]
        risk_idx = random.choices(range(4), weights=[0.40, 0.35, 0.15, 0.10])[0]
        kyc_idx = random.choices(range(4), weights=[0.80, 0.10, 0.05, 0.05])[0]

        # Select channel and region
        channel_idx = random.choices(range(6), weights=[0.40, 0.30, 0.12, 0.10, 0.05, 0.03])[0]
        region_idx = random.choices(range(5), weights=[0.25, 0.20, 0.18, 0.17, 0.20])[0]

        # Generate balances
        balance = random.lognormvariate(9, 2)
        balance = min(balance, 1000000)
        hold = balance * random.uniform(0, 0.1) if random.random() < 0.15 else 0

        # Generate reference number
        ref_num = str(uuid.uuid4()).upper()[:12]

        # Boolean value - intentionally mixed formats
        bool_formats = [0, 1, 'Y', 'N', True, False, 'Yes', 'No']
        is_pending_val = random.choice(bool_formats) if random.random() < 0.1 else random.choice([0, False, 'N', 'No'])

        record = {
            # Transaction IDs (6 variations)
            'txn_id': f'TXN-{i+1:010d}',
            'transaction_id': i + 1,
            'trans_id': f'T{i+1:012d}',
            'TXN_KEY': i + 1,
            'ref_num': ref_num,
            'reference_number': ref_num,

            # Account numbers (6 variations)
            'acct_num': account_nums[acct_idx],
            'account_number': account_nums[acct_idx],
            'ACCTNO': account_nums[acct_idx],
            'account_id': acct_idx + 1,
            'acct_id': f'ACCT-{acct_idx+1:08d}',
            'acct': account_nums[acct_idx][-4:],  # Last 4 only!

            # Customer IDs (6 variations)
            'cust_id': customer_ids[cust_idx],
            'customer_id': customer_nums[cust_idx],
            'CUSTID': customer_ids[cust_idx].replace('-', ''),
            'party_id': party_ids[cust_idx],
            'client_id': client_ids[cust_idx],
            'tax_id': f'XXX-XX-{random.randint(1000, 9999)}',  # Masked

            # Dates (10+ columns with different formats)
            'trans_date': tx_date.date(),
            'transaction_date': tx_date.strftime('%m/%d/%Y'),
            'posting_date': tx_date.strftime('%Y-%m-%d'),
            'value_date': tx_date.date(),
            'effective_date': int(tx_date.strftime('%Y%m%d')),
            'settle_dt': tx_date.strftime('%d-%b-%Y').upper(),
            'dt': tx_date.date(),
            'yr': tx_date.year,
            'mth': tx_date.month,
            'dy': tx_date.day,

            # Transaction types (4+ variations)
            'trans_type': tx_code,
            'transaction_type': tx_name,
            'TXN_TYPE': tx_code,
            'type_cd': tx_code[0],
            'type': tx_num,

            # Amounts (8 variations)
            'amt': amount,
            'amount': amount,
            'AMT': amount,
            'amount_usd': amount_usd,
            'amount_local': amount,
            'local_amt': amount,
            'trans_amt': amount,
            'TRANS_AMT': amount,

            # Currency (6 variations)
            'ccy': ccy,
            'currency': ccy_name,
            'currency_code': ccy,
            'CCY_CD': iso_code,
            'fx_rate': fx_rate,
            'exchange_rate': fx_rate,

            # Balances (12 variations)
            'balance': round(balance, 2),
            'bal': round(balance, 2),
            'BAL': round(balance, 2),
            'current_balance': round(balance, 2),
            'curr_bal': round(balance, 2),
            'available_balance': round(balance - hold, 2),
            'avail_bal': round(balance - hold, 2),
            'ledger_balance': round(balance * random.uniform(0.98, 1.02), 2),
            'ldgr_bal': round(balance * random.uniform(0.98, 1.02), 2),
            'memo_balance': round(balance * random.uniform(0.95, 1.05), 2),
            'hold_amount': round(hold, 2),
            'hold_amt': round(hold, 2),

            # Segment/Risk (8 variations)
            'seg': segment_codes[seg_idx],
            'segment': segments[seg_idx],
            'SEGMENT_CD': segment_codes[seg_idx],
            'cust_seg': segments[seg_idx] if random.random() < 0.5 else segment_codes[seg_idx],
            'risk_rating': risk_codes[risk_idx],
            'risk': risk_names[risk_idx],
            'kyc_status': kyc_codes[kyc_idx],
            'kyc': kyc_names[kyc_idx],

            # Branch (6 variations)
            'branch_id': random.randint(1, 50),
            'branch_cd': f'BR-{random.randint(1, 50):04d}',
            'BRANCH': f'BR{random.randint(1, 50):04d}',
            'br': random.randint(1, 50),
            'region': region_codes[region_idx],
            'region_name': regions[region_idx],

            # Channel (3 variations)
            'channel': channels[channel_idx],
            'channel_name': channels[channel_idx],
            'chnl': channel_nums[channel_idx],

            # Status flags (6 variations with mixed formats)
            'status': random.choice(['A', 'C', 'P', 'D']),
            'status_desc': random.choice(['Active', 'Completed', 'Pending', 'Declined']),
            'is_pending': is_pending_val,
            'is_reversed': random.choice(bool_formats) if random.random() < 0.02 else 0,
            'flg1': random.choice([0, 1, None]),
            'flg2': random.choice(['Y', 'N', None, '']),

            # Mystery columns (no documentation)
            'cd1': random.choice(['A', 'B', 'C', 'X', 'Z', None]),
            'cd2': random.randint(0, 99) if random.random() < 0.8 else None,
            'val': round(random.uniform(0, 100), 2) if random.random() < 0.7 else None,
            'cnt': random.randint(1, 10) if random.random() < 0.5 else None,
            'attr1': fake.word() if random.random() < 0.3 else None,

            # Timestamps
            'created_at': tx_datetime,
            'modified_dt': (tx_datetime + timedelta(hours=random.randint(0, 48))).strftime('%Y-%m-%d %H:%M:%S'),
            'etl_ts': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'),
        }

        records.append(record)

    return pd.DataFrame(records)


def save_finance_super_table(
    output_dir: str,
    n_rows: int = 500000,
) -> pd.DataFrame:
    """
    Generate and save the finance super table to parquet.

    Args:
        output_dir: Directory to save the parquet file
        n_rows: Number of rows to generate

    Returns:
        The generated DataFrame
    """
    os.makedirs(output_dir, exist_ok=True)

    print("  Generating finance super table with anti-patterns...")
    df = generate_finance_super_table(n_rows=n_rows)

    # Convert mixed-type columns to string for parquet compatibility
    # This preserves the anti-pattern (mixed formats) while allowing serialization
    mixed_type_columns = ['is_pending', 'is_reversed', 'flg1', 'flg2']
    for col in mixed_type_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)

    output_path = os.path.join(output_dir, 'finance_super_table.parquet')
    df.to_parquet(output_path, index=False)
    print(f"    Saved {output_path} ({len(df):,} rows, {len(df.columns)} columns)")

    return df
