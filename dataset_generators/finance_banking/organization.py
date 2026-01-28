"""
Finance Banking Dataset - Organization Domain
==============================================

Generates organization-related dimension tables:
- dim_branch: Bank branch locations
- dim_employee: Bank employees
- dim_date: Date dimension with fiscal calendar
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .utils import (
    generate_person_name,
    scale_count,
    weighted_choice,
    fake,
    REGIONS,
    BRANCH_TYPES,
    EMPLOYEE_ROLES,
    DEPARTMENTS,
    CITIES,
)


def generate_dim_branch(n: int = 50) -> pd.DataFrame:
    """
    Generate branch dimension table.

    Args:
        n: Number of branches to generate

    Returns:
        DataFrame with branch data
    """
    records = []

    for i in range(1, n + 1):
        region = weighted_choice(REGIONS)
        branch_type = weighted_choice(BRANCH_TYPES)

        # Get city and state for this region
        city, state = random.choice(CITIES[region])

        # Generate address
        address = fake.street_address()
        zip_code = fake.zipcode()
        phone = fake.phone_number()

        # Generate manager name
        first_name, last_name = generate_person_name()
        manager_name = f'{first_name} {last_name}'

        # Branch name based on location and type
        if branch_type == 'Private Banking Center':
            branch_name = f'{city} Private Banking'
        elif branch_type == 'Commercial Center':
            branch_name = f'{city} Commercial Banking'
        else:
            branch_name = f'{city} {address.split()[0]} Branch'

        # Is active - most branches are active
        is_active = random.random() < 0.95

        records.append({
            'branch_key': i,
            'branch_code': f'BR-{i:04d}',
            'branch_name': branch_name,
            'branch_type': branch_type,
            'region': region,
            'city': city,
            'state': state,
            'address': address,
            'zip_code': zip_code,
            'phone': phone,
            'manager_name': manager_name,
            'is_active': is_active,
        })

    return pd.DataFrame(records)


def generate_dim_employee(
    n: int = 200,
    branch_keys: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Generate employee dimension table.

    Args:
        n: Number of employees to generate
        branch_keys: List of valid branch keys

    Returns:
        DataFrame with employee data
    """
    records = []

    for i in range(1, n + 1):
        first_name, last_name = generate_person_name()
        full_name = f'{first_name} {last_name}'

        role = weighted_choice(EMPLOYEE_ROLES)
        department = weighted_choice(DEPARTMENTS)

        # Assign to branch
        if branch_keys:
            branch_key = random.choice(branch_keys)
        else:
            branch_key = random.randint(1, 50)

        # Hire date - exponential distribution, more recent hires more common
        years_ago = np.random.exponential(scale=4)
        years_ago = min(years_ago, 20)  # Cap at 20 years
        hire_date = datetime.now() - timedelta(days=int(years_ago * 365))

        # Is active - older employees slightly more likely to have left
        churn_prob = min(0.01 + (years_ago * 0.008), 0.12)
        is_active = random.random() > churn_prob

        # Generate email (corporate)
        email = f'{first_name.lower()}.{last_name.lower()}@firstnationalbank.com'

        records.append({
            'employee_key': i,
            'employee_id': f'EMP-{i:05d}',
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'email': email,
            'role': role,
            'department': department,
            'branch_key': branch_key,
            'hire_date': hire_date.date(),
            'is_active': is_active,
        })

    return pd.DataFrame(records)


def generate_dim_date(
    start_date: str = "2023-01-01",
    end_date: str = "2025-12-31",
) -> pd.DataFrame:
    """
    Generate date dimension table with fiscal calendar.

    Fiscal year starts February 1st.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        DataFrame with date dimension data
    """
    # US federal holidays (fixed dates)
    federal_holidays = [
        (1, 1),   # New Year's Day
        (7, 4),   # Independence Day
        (12, 25), # Christmas Day
    ]

    # Create date range
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    records = []
    current = start

    while current <= end:
        year = current.year
        month = current.month
        day = current.day

        # Date key as integer YYYYMMDD
        date_key = int(current.strftime('%Y%m%d'))

        # Day of week (0=Monday, 6=Sunday)
        day_of_week = current.weekday()
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = day_names[day_of_week]

        # Month name
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        month_name = month_names[month - 1]

        # Week of year
        week_of_year = current.isocalendar()[1]

        # Calendar quarter
        quarter = (month - 1) // 3 + 1

        # Fiscal year and quarter (fiscal year starts February 1)
        if month >= 2:
            fiscal_year = year
            fiscal_month = month - 1  # Feb = 1, Mar = 2, ..., Jan = 12
        else:
            fiscal_year = year - 1
            fiscal_month = month + 11  # Jan = 12

        fiscal_quarter = (fiscal_month - 1) // 3 + 1
        fiscal_quarter_name = f'FY{fiscal_year} Q{fiscal_quarter}'

        # Is weekend
        is_weekend = day_of_week >= 5

        # Is holiday (simplified - just fixed holidays)
        is_holiday = (month, day) in federal_holidays

        # Is business day
        is_business_day = not is_weekend and not is_holiday

        # Is month end
        next_day = current + timedelta(days=1)
        is_month_end = next_day.month != month

        records.append({
            'date_key': date_key,
            'full_date': current.date(),
            'year': year,
            'month': month,
            'month_name': month_name,
            'day_of_month': day,
            'day_of_week': day_of_week,
            'day_name': day_name,
            'week_of_year': week_of_year,
            'quarter': quarter,
            'fiscal_year': fiscal_year,
            'fiscal_quarter': fiscal_quarter,
            'fiscal_quarter_name': fiscal_quarter_name,
            'is_weekend': is_weekend,
            'is_holiday': is_holiday,
            'is_business_day': is_business_day,
            'is_month_end': is_month_end,
        })

        current += timedelta(days=1)

    return pd.DataFrame(records)


def generate_operations_domain(scale: float = 1.0) -> Dict[str, pd.DataFrame]:
    """
    Generate all organization-related dimension tables.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    print("  Generating dim_branch...")
    dim_branch = generate_dim_branch(n=scale_count(50, scale))

    print("  Generating dim_employee...")
    dim_employee = generate_dim_employee(
        n=scale_count(200, scale),
        branch_keys=dim_branch['branch_key'].tolist(),
    )

    print("  Generating dim_date...")
    dim_date = generate_dim_date()

    return {
        'dim_branch': dim_branch,
        'dim_employee': dim_employee,
        'dim_date': dim_date,
    }
