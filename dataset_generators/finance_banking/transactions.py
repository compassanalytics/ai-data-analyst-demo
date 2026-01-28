"""
Finance Banking Dataset - Transactions Domain
==============================================

Generates fact tables:
- fact_transaction: Transaction records
- fact_account_balance: Daily account balance snapshots
"""

import random
from datetime import datetime
from typing import Dict, List, Optional
import uuid

import numpy as np
import pandas as pd

from .utils import (
    scale_count,
    weighted_choice,
    TRANSACTION_TYPES,
    CHANNELS,
    CURRENCIES,
)


def generate_fact_transaction(
    n: int = 500000,
    date_keys: Optional[List[int]] = None,
    account_keys: Optional[List[int]] = None,
    customer_keys: Optional[List[int]] = None,
    branch_keys: Optional[List[int]] = None,
    employee_keys: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Generate transaction fact table.

    Args:
        n: Number of transactions to generate
        date_keys: List of valid date keys
        account_keys: List of valid account keys
        customer_keys: List of valid customer keys
        branch_keys: List of valid branch keys
        employee_keys: List of valid employee keys

    Returns:
        DataFrame with transaction data
    """
    # Validate FK lists
    assert date_keys and len(date_keys) > 0, "date_keys must not be empty"
    assert account_keys and len(account_keys) > 0, "account_keys must not be empty"
    assert customer_keys and len(customer_keys) > 0, "customer_keys must not be empty"
    assert branch_keys and len(branch_keys) > 0, "branch_keys must not be empty"
    assert employee_keys and len(employee_keys) > 0, "employee_keys must not be empty"

    # Filter to business days (date_keys that are likely weekdays)
    # For simplicity, we'll weight dates - business days are more common
    # We'll use the date_keys directly since we don't have the full date info here

    # Transaction type extraction
    tx_codes = [t[0] for t in TRANSACTION_TYPES]
    tx_names = [t[1] for t in TRANSACTION_TYPES]
    tx_weights = [t[2] for t in TRANSACTION_TYPES]

    records = []

    for i in range(1, n + 1):
        # Select date key - weight toward more recent dates
        # Use exponential distribution to weight toward end of list (assuming sorted)
        date_idx = int(np.random.exponential(scale=len(date_keys) / 3))
        date_idx = min(date_idx, len(date_keys) - 1)
        # Flip to get more recent dates (higher indices)
        date_idx = len(date_keys) - 1 - date_idx
        date_key = date_keys[date_idx]

        # Convert date_key to datetime for transaction_date
        year = date_key // 10000
        month = (date_key % 10000) // 100
        day = date_key % 100

        # Add time component - business hours weighted (9am-6pm more likely)
        if random.random() < 0.85:
            hour = random.randint(9, 18)
        else:
            hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        try:
            transaction_date = datetime(year, month, day, hour, minute, second)
        except ValueError:
            # Handle invalid dates gracefully
            transaction_date = datetime(year, month, 1, hour, minute, second)

        # Select account and customer
        account_key = random.choice(account_keys)
        customer_key = random.choice(customer_keys)

        # Select channel
        channel = weighted_choice(CHANNELS)

        # Employee only for Branch transactions
        if channel == 'Branch':
            branch_key = random.choice(branch_keys)
            employee_key = random.choice(employee_keys)
        else:
            branch_key = random.choice(branch_keys)  # Still assign branch for reporting
            employee_key = None

        # Transaction type
        tx_idx = random.choices(range(len(tx_codes)), weights=tx_weights)[0]
        transaction_type_code = tx_codes[tx_idx]
        transaction_type = tx_names[tx_idx]

        # Amount using lognormal distribution (median ~400, cap at 50K)
        # lognormvariate(mu, sigma) - mu=6, sigma=1.5 gives median around exp(6)~400
        amount = random.lognormvariate(6, 1.5)
        amount = min(amount, 50000)  # Cap at 50K
        amount = round(amount, 2)

        # For withdrawals and payments, amount is negative (outflow)
        if transaction_type_code in ('WD', 'PYM', 'FEE', 'CHG'):
            amount = -amount

        # Currency (mostly USD)
        currency_code = weighted_choice(CURRENCIES)

        # Reference number
        reference_number = str(uuid.uuid4()).upper()[:12]

        records.append({
            'transaction_key': i,
            'date_key': date_key,
            'transaction_date': transaction_date,
            'account_key': account_key,
            'customer_key': customer_key,
            'branch_key': branch_key,
            'employee_key': employee_key,
            'transaction_type_code': transaction_type_code,
            'transaction_type': transaction_type,
            'amount': amount,
            'currency_code': currency_code,
            'channel': channel,
            'reference_number': reference_number,
        })

    return pd.DataFrame(records)


def generate_fact_account_balance(
    date_keys: Optional[List[int]] = None,
    account_keys: Optional[List[int]] = None,
    sample_rate: float = 0.1,
) -> pd.DataFrame:
    """
    Generate account balance fact table (daily snapshots).

    For performance, samples a subset of date/account combinations.

    Args:
        date_keys: List of valid date keys
        account_keys: List of valid account keys
        sample_rate: Proportion of date/account combinations to generate (default 0.1)

    Returns:
        DataFrame with account balance data
    """
    # Validate FK lists
    assert date_keys and len(date_keys) > 0, "date_keys must not be empty"
    assert account_keys and len(account_keys) > 0, "account_keys must not be empty"

    records = []
    balance_key = 1

    # Generate a base balance for each account (used for realistic progression)
    account_base_balances = {}
    for account_key in account_keys:
        # Base balance using lognormal distribution
        base_balance = random.lognormvariate(9, 2)  # Median around exp(9) ~ 8000
        base_balance = min(base_balance, 1000000)  # Cap at 1M
        account_base_balances[account_key] = base_balance

    # Sample date/account combinations
    total_combinations = len(date_keys) * len(account_keys)
    n_samples = int(total_combinations * sample_rate)

    # Create sampled combinations
    sampled = set()
    while len(sampled) < n_samples:
        date_key = random.choice(date_keys)
        account_key = random.choice(account_keys)
        sampled.add((date_key, account_key))

    # Sort by date for more realistic balance progression
    sampled = sorted(sampled, key=lambda x: (x[1], x[0]))  # Sort by account, then date

    # Track balance per account for progression
    account_last_balance = {}

    for date_key, account_key in sampled:
        base = account_base_balances[account_key]

        # Get last known balance or start from base
        if account_key in account_last_balance:
            last_balance = account_last_balance[account_key]
            # Add some daily variation (-5% to +5%)
            variation = random.uniform(-0.05, 0.05)
            current_balance = last_balance * (1 + variation)
        else:
            # First record for this account - use base with some variation
            current_balance = base * random.uniform(0.8, 1.2)

        current_balance = round(max(0, current_balance), 2)

        # Hold amount (small percentage of balance, or 0)
        if random.random() < 0.15:  # 15% of balances have holds
            hold_amount = round(current_balance * random.uniform(0.01, 0.10), 2)
        else:
            hold_amount = 0.0

        # Available balance = current - hold
        available_balance = round(current_balance - hold_amount, 2)

        # Ledger balance (slightly different from current due to pending transactions)
        ledger_diff = random.uniform(-0.02, 0.02) * current_balance
        ledger_balance = round(max(0, current_balance + ledger_diff), 2)

        records.append({
            'balance_key': balance_key,
            'date_key': date_key,
            'account_key': account_key,
            'current_balance': current_balance,
            'available_balance': available_balance,
            'ledger_balance': ledger_balance,
            'hold_amount': hold_amount,
        })

        account_last_balance[account_key] = current_balance
        balance_key += 1

    return pd.DataFrame(records)


def generate_transaction_facts(
    scale: float,
    dim_date: pd.DataFrame,
    dim_account: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_branch: pd.DataFrame,
    dim_employee: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """
    Generate all transaction fact tables.

    Args:
        scale: Scale factor for record counts
        dim_date: Date dimension DataFrame
        dim_account: Account dimension DataFrame
        dim_customer: Customer dimension DataFrame
        dim_branch: Branch dimension DataFrame
        dim_employee: Employee dimension DataFrame

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    # Extract keys from dimension tables
    date_keys = dim_date['date_key'].tolist()
    account_keys = dim_account['account_key'].tolist()
    customer_keys = dim_customer['customer_key'].tolist()
    branch_keys = dim_branch['branch_key'].tolist()
    employee_keys = dim_employee['employee_key'].tolist()

    print("  Generating fact_transaction...")
    fact_transaction = generate_fact_transaction(
        n=scale_count(500000, scale),
        date_keys=date_keys,
        account_keys=account_keys,
        customer_keys=customer_keys,
        branch_keys=branch_keys,
        employee_keys=employee_keys,
    )

    print("  Generating fact_account_balance...")
    fact_account_balance = generate_fact_account_balance(
        date_keys=date_keys,
        account_keys=account_keys,
        sample_rate=0.1,
    )

    return {
        'fact_transaction': fact_transaction,
        'fact_account_balance': fact_account_balance,
    }
