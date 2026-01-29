"""
Finance Banking Dataset - Accounts Domain
==========================================

Generates account-related dimension tables:
- dim_customer: Customer master data
- dim_product: Banking product definitions
- dim_account: Customer accounts
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .utils import (
    ACCOUNT_STATUSES,
    ACCOUNT_TYPES,
    CURRENCIES,
    CUSTOMER_SEGMENTS,
    KYC_STATUSES,
    PRODUCT_TYPES,
    RISK_RATINGS,
    fake,
    generate_account_number,
    generate_email,
    generate_person_name,
    scale_count,
    weighted_choice,
)


def generate_dim_customer(n: int = 5000) -> pd.DataFrame:
    """
    Generate customer dimension table.

    Args:
        n: Number of customers to generate

    Returns:
        DataFrame with customer data
    """
    records = []

    for i in range(1, n + 1):
        first_name, last_name = generate_person_name()
        full_name = f"{first_name} {last_name}"

        # Segment selection
        segment = weighted_choice(CUSTOMER_SEGMENTS)

        # Risk rating - correlate slightly with segment
        if segment in ("Private Banking", "Institutional"):
            # Higher-tier customers tend to have lower risk
            risk_options = [
                ("Low", 0.60),
                ("Medium", 0.30),
                ("Medium-High", 0.08),
                ("High", 0.02),
            ]
        elif segment == "High Net Worth":
            risk_options = [
                ("Low", 0.50),
                ("Medium", 0.35),
                ("Medium-High", 0.12),
                ("High", 0.03),
            ]
        else:
            risk_options = RISK_RATINGS
        risk_rating = weighted_choice(risk_options)

        # KYC status
        kyc_status = weighted_choice(KYC_STATUSES)

        # Customer since date - exponential distribution, more recent customers more common
        years_ago = np.random.exponential(scale=5)
        years_ago = min(years_ago, 25)  # Cap at 25 years
        customer_since = datetime.now() - timedelta(days=int(years_ago * 365))

        # Is active - older customers slightly more likely to be inactive
        churn_prob = min(0.02 + (years_ago * 0.005), 0.15)
        is_active = random.random() > churn_prob

        records.append(
            {
                "customer_key": i,
                "customer_id": f"CUST-{i:06d}",
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "email": generate_email(first_name, last_name),
                "phone": fake.phone_number(),
                "segment": segment,
                "risk_rating": risk_rating,
                "kyc_status": kyc_status,
                "customer_since": customer_since.date(),
                "is_active": is_active,
            }
        )

    return pd.DataFrame(records)


def generate_dim_product() -> pd.DataFrame:
    """
    Generate product dimension table with fixed ~25 banking products.

    Returns:
        DataFrame with product definitions
    """
    records = []
    product_key = 1

    for product_type, products in PRODUCT_TYPES.items():
        for product_code, product_name in products:
            # Interest rate for Loan and Deposit products
            if product_type == "Loan":
                # Loan interest rates: 3-15% depending on product
                if "MORT" in product_code:
                    interest_rate = round(random.uniform(5.5, 7.5), 3)
                elif "AUTO" in product_code:
                    interest_rate = round(random.uniform(4.5, 9.0), 3)
                elif "HELOC" in product_code:
                    interest_rate = round(random.uniform(7.0, 10.0), 3)
                else:  # Personal loans
                    interest_rate = round(random.uniform(8.0, 15.0), 3)
            elif product_type == "Deposit":
                # Deposit interest rates: 0.01-5% depending on product
                if "CD" in product_code:
                    interest_rate = round(random.uniform(3.0, 5.0), 3)
                elif "SAV-HY" in product_code:
                    interest_rate = round(random.uniform(3.5, 4.5), 3)
                elif "MM" in product_code:
                    interest_rate = round(random.uniform(2.5, 4.0), 3)
                elif "SAV" in product_code:
                    interest_rate = round(random.uniform(0.5, 2.0), 3)
                else:  # Checking
                    interest_rate = round(random.uniform(0.01, 0.5), 3)
            else:
                interest_rate = None

            records.append(
                {
                    "product_key": product_key,
                    "product_code": product_code,
                    "product_name": product_name,
                    "product_type": product_type,
                    "interest_rate": interest_rate,
                    "is_active": True,
                }
            )
            product_key += 1

    return pd.DataFrame(records)


def generate_dim_account(
    n: int = 8000,
    customer_keys: list[int] | None = None,
) -> pd.DataFrame:
    """
    Generate account dimension table.

    Args:
        n: Number of accounts to generate
        customer_keys: List of valid customer keys

    Returns:
        DataFrame with account data
    """
    records = []

    for i in range(1, n + 1):
        account_type = weighted_choice(ACCOUNT_TYPES)
        status = weighted_choice(ACCOUNT_STATUSES)
        currency_code = weighted_choice(CURRENCIES)

        # Assign customer
        if customer_keys:
            customer_key = random.choice(customer_keys)
        else:
            customer_key = random.randint(1, 5000)

        # Open date - exponential distribution, more recent accounts more common
        years_ago = np.random.exponential(scale=4)
        years_ago = min(years_ago, 20)  # Cap at 20 years
        open_date = datetime.now() - timedelta(days=int(years_ago * 365))

        # Last activity date - depends on status
        if status == "Closed":
            # Closed accounts have older last activity
            days_since_activity = random.randint(180, 730)
        elif status == "Dormant":
            days_since_activity = random.randint(90, 365)
        elif status == "Frozen":
            days_since_activity = random.randint(30, 180)
        else:  # Active
            days_since_activity = random.randint(0, 30)

        last_activity_date = datetime.now() - timedelta(days=days_since_activity)

        # Ensure last activity is after open date
        if last_activity_date < open_date:
            last_activity_date = open_date + timedelta(days=random.randint(1, 30))

        records.append(
            {
                "account_key": i,
                "account_number": generate_account_number(),
                "account_type": account_type,
                "status": status,
                "currency_code": currency_code,
                "customer_key": customer_key,
                "open_date": open_date.date(),
                "last_activity_date": last_activity_date.date(),
            }
        )

    return pd.DataFrame(records)


def generate_accounts_domain(scale: float = 1.0) -> dict[str, pd.DataFrame]:
    """
    Generate all account-related dimension tables.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    print("  Generating dim_customer...")
    dim_customer = generate_dim_customer(n=scale_count(5000, scale))

    print("  Generating dim_product...")
    dim_product = generate_dim_product()

    print("  Generating dim_account...")
    dim_account = generate_dim_account(
        n=scale_count(8000, scale),
        customer_keys=dim_customer["customer_key"].tolist(),
    )

    return {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_account": dim_account,
    }
