"""
Finance Banking Dataset - Shared Utilities
===========================================

Provides shared utilities for generating consistent, realistic banking data.
"""

import random

import numpy as np
from faker import Faker

# Initialize faker with US locale
fake = Faker("en_US")


def set_random_seed(seed: int) -> None:
    """
    Set random seed for reproducibility across all random number generators.

    Args:
        seed: Integer seed value
    """
    random.seed(seed)
    np.random.seed(seed)
    Faker.seed(seed)


def scale_count(base: int, scale: float) -> int:
    """
    Apply scale factor to a base count, ensuring minimum of 1.

    Args:
        base: Base count
        scale: Scale factor (e.g., 0.1 for 10%)

    Returns:
        Scaled count, minimum 1
    """
    return max(1, int(base * scale))


def weighted_choice(options: list[tuple[str, float]]) -> str:
    """
    Select a random item from weighted options.

    Args:
        options: List of (value, weight) tuples

    Returns:
        Selected value
    """
    values, weights = zip(*options)
    return random.choices(values, weights=weights)[0]


def generate_account_number() -> str:
    """
    Generate a 10-digit account number.

    Returns:
        10-digit account number string
    """
    return "".join([str(random.randint(0, 9)) for _ in range(10)])


def generate_routing_number() -> str:
    """
    Generate a 9-digit routing number.

    Returns:
        9-digit routing number string
    """
    return "".join([str(random.randint(0, 9)) for _ in range(9)])


# Account Types with weights
ACCOUNT_TYPES: list[tuple[str, float]] = [
    ("Checking", 0.35),
    ("Savings", 0.30),
    ("Money Market", 0.10),
    ("CD", 0.08),
    ("Credit Card", 0.12),
    ("Loan", 0.05),
]

# Account Statuses with weights
ACCOUNT_STATUSES: list[tuple[str, float]] = [
    ("Active", 0.85),
    ("Dormant", 0.08),
    ("Frozen", 0.03),
    ("Closed", 0.04),
]

# Currencies with weights
CURRENCIES: list[tuple[str, float]] = [
    ("USD", 0.75),
    ("EUR", 0.10),
    ("GBP", 0.08),
    ("CAD", 0.05),
    ("CHF", 0.02),
]

# Customer Segments with weights
CUSTOMER_SEGMENTS: list[tuple[str, float]] = [
    ("Retail", 0.50),
    ("Mass Affluent", 0.25),
    ("High Net Worth", 0.15),
    ("Private Banking", 0.07),
    ("Institutional", 0.03),
]

# Risk Ratings with weights
RISK_RATINGS: list[tuple[str, float]] = [
    ("Low", 0.40),
    ("Medium", 0.35),
    ("Medium-High", 0.15),
    ("High", 0.10),
]

# KYC Statuses with weights
KYC_STATUSES: list[tuple[str, float]] = [
    ("Verified", 0.80),
    ("Pending", 0.10),
    ("Expired", 0.05),
    ("Enhanced Due Diligence", 0.05),
]

# Transaction Types: (code, name, weight)
TRANSACTION_TYPES: list[tuple[str, str, float]] = [
    ("DEP", "Deposit", 0.25),
    ("WD", "Withdrawal", 0.20),
    ("TRF", "Transfer", 0.25),
    ("PYM", "Payment", 0.15),
    ("FEE", "Fee", 0.05),
    ("INT", "Interest", 0.05),
    ("CHG", "Charge", 0.03),
    ("REF", "Refund", 0.02),
]

# Channels with weights
CHANNELS: list[tuple[str, float]] = [
    ("Online Banking", 0.40),
    ("Mobile App", 0.30),
    ("ATM", 0.12),
    ("Branch", 0.10),
    ("Wire", 0.05),
    ("ACH", 0.03),
]

# Regions with weights
REGIONS: list[tuple[str, float]] = [
    ("Northeast", 0.25),
    ("Southeast", 0.20),
    ("Midwest", 0.18),
    ("Southwest", 0.17),
    ("West", 0.20),
]

# Branch Types with weights
BRANCH_TYPES: list[tuple[str, float]] = [
    ("Full Service", 0.50),
    ("Express", 0.30),
    ("Private Banking Center", 0.10),
    ("Commercial Center", 0.10),
]

# Employee Roles with weights
EMPLOYEE_ROLES: list[tuple[str, float]] = [
    ("Teller", 0.35),
    ("Personal Banker", 0.25),
    ("Relationship Manager", 0.15),
    ("Branch Manager", 0.05),
    ("Loan Officer", 0.10),
    ("Financial Advisor", 0.10),
]

# Departments with weights
DEPARTMENTS: list[tuple[str, float]] = [
    ("Retail Banking", 0.40),
    ("Commercial Banking", 0.20),
    ("Wealth Management", 0.15),
    ("Operations", 0.15),
    ("Risk Management", 0.10),
]

# Product Types: type -> list of (code, name) tuples
PRODUCT_TYPES = {
    "Loan": [
        ("MORT-30Y", "Mortgage 30-Year Fixed"),
        ("MORT-15Y", "Mortgage 15-Year Fixed"),
        ("AUTO-NEW", "Auto Loan - New Vehicle"),
        ("AUTO-USED", "Auto Loan - Used Vehicle"),
        ("PERS-SEC", "Personal Loan - Secured"),
        ("PERS-UNSEC", "Personal Loan - Unsecured"),
        ("HELOC", "Home Equity Line of Credit"),
    ],
    "Card": [
        ("CC-BASIC", "Credit Card - Basic"),
        ("CC-REWARDS", "Credit Card - Rewards"),
        ("CC-PREMIUM", "Credit Card - Premium"),
        ("CC-SECURED", "Credit Card - Secured"),
        ("DEBIT-STD", "Debit Card - Standard"),
        ("DEBIT-PREM", "Debit Card - Premium"),
    ],
    "Deposit": [
        ("CHK-STD", "Checking - Standard"),
        ("CHK-PREM", "Checking - Premium"),
        ("SAV-STD", "Savings - Standard"),
        ("SAV-HY", "Savings - High Yield"),
        ("MM-STD", "Money Market - Standard"),
        ("CD-3M", "Certificate of Deposit - 3 Month"),
        ("CD-12M", "Certificate of Deposit - 12 Month"),
    ],
    "Investment": [
        ("IRA-TRAD", "IRA - Traditional"),
        ("IRA-ROTH", "IRA - Roth"),
        ("BROK-STD", "Brokerage - Standard"),
        ("BROK-MARG", "Brokerage - Margin"),
        ("401K", "401(k) Plan"),
    ],
}

# Cities by region: region -> list of (city, state) tuples
CITIES = {
    "Northeast": [
        ("New York", "NY"),
        ("Boston", "MA"),
        ("Philadelphia", "PA"),
        ("Hartford", "CT"),
        ("Providence", "RI"),
        ("Pittsburgh", "PA"),
        ("Newark", "NJ"),
        ("Buffalo", "NY"),
    ],
    "Southeast": [
        ("Atlanta", "GA"),
        ("Miami", "FL"),
        ("Charlotte", "NC"),
        ("Tampa", "FL"),
        ("Orlando", "FL"),
        ("Nashville", "TN"),
        ("Jacksonville", "FL"),
        ("Raleigh", "NC"),
    ],
    "Midwest": [
        ("Chicago", "IL"),
        ("Detroit", "MI"),
        ("Minneapolis", "MN"),
        ("Cleveland", "OH"),
        ("Columbus", "OH"),
        ("Indianapolis", "IN"),
        ("Milwaukee", "WI"),
        ("Kansas City", "MO"),
    ],
    "Southwest": [
        ("Dallas", "TX"),
        ("Houston", "TX"),
        ("Phoenix", "AZ"),
        ("San Antonio", "TX"),
        ("Austin", "TX"),
        ("Denver", "CO"),
        ("Albuquerque", "NM"),
        ("Tucson", "AZ"),
    ],
    "West": [
        ("Los Angeles", "CA"),
        ("San Francisco", "CA"),
        ("Seattle", "WA"),
        ("San Diego", "CA"),
        ("Portland", "OR"),
        ("Las Vegas", "NV"),
        ("Sacramento", "CA"),
        ("San Jose", "CA"),
    ],
}


def generate_person_name() -> tuple[str, str]:
    """
    Generate a realistic person name.

    Returns:
        Tuple of (first_name, last_name)
    """
    return fake.first_name(), fake.last_name()


def generate_email(first_name: str, last_name: str) -> str:
    """
    Generate a realistic email address based on name.

    Args:
        first_name: Person's first name
        last_name: Person's last name

    Returns:
        Email address string
    """
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"]

    # Various email formats
    formats = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name.lower()}{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}{last_name[0].lower()}",
        f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}",
        f"{first_name.lower()}{random.randint(1, 999)}",
    ]

    username = random.choice(formats)
    domain = random.choice(domains)

    return f"{username}@{domain}"
