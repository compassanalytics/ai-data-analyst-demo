"""
Velocity Motors Dataset - CRM Domain
=====================================

Generates CRM-related tables:
- customer_segments: Customer segment definitions
- customers: Customer master data
- interactions: Customer interaction history
- leads: Sales leads (converted and unconverted)
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .utils import (
    fake,
    generate_customer_address,
    generate_dates_with_seasonality,
    generate_email,
    generate_person_name,
    get_null_rate,
    inject_nulls,
    scale_count,
)


def generate_customer_segments() -> pd.DataFrame:
    """
    Generate fixed customer segment dimension table.

    Returns:
        DataFrame with 3 customer segments
    """
    segments = [
        {
            "segment_id": "SEG-001",
            "segment_name": "Individual",
            "description": "Individual retail customers purchasing for personal use",
            "discount_tier": "Standard",
            "credit_limit_default": 50000,
            "payment_terms_days": 30,
        },
        {
            "segment_id": "SEG-002",
            "segment_name": "Fleet",
            "description": "Business customers managing vehicle fleets (5+ vehicles)",
            "discount_tier": "Volume",
            "credit_limit_default": 500000,
            "payment_terms_days": 45,
        },
        {
            "segment_id": "SEG-003",
            "segment_name": "Dealer",
            "description": "Authorized dealers and resellers purchasing for resale",
            "discount_tier": "Dealer",
            "credit_limit_default": 1000000,
            "payment_terms_days": 60,
        },
    ]

    return pd.DataFrame(segments)


def generate_customers(n: int = 50000, cleanliness: int = 100) -> pd.DataFrame:
    """
    Generate customer table with 70/20/10 segment distribution.

    Args:
        n: Number of customers to generate
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)

    Returns:
        DataFrame with customer data
    """
    # Segment distribution: 70% Individual, 20% Fleet, 10% Dealer
    segment_weights = [0.70, 0.20, 0.10]
    segment_ids = ["SEG-001", "SEG-002", "SEG-003"]
    segment_names = ["Individual", "Fleet", "Dealer"]

    # Credit scores distribution
    credit_score_ranges = {
        "Individual": (580, 850),
        "Fleet": (650, 850),
        "Dealer": (700, 850),
    }

    records = []
    for i in range(1, n + 1):
        # Select segment
        segment_idx = random.choices(range(3), weights=segment_weights)[0]
        segment_id = segment_ids[segment_idx]
        segment_name = segment_names[segment_idx]

        # Generate name based on segment
        if segment_name == "Individual":
            first_name, last_name = generate_person_name()
            company_name = None
            customer_name = f"{first_name} {last_name}"
        elif segment_name == "Fleet":
            first_name, last_name = generate_person_name()
            company_name = fake.company()
            customer_name = company_name
        else:  # Dealer
            first_name, last_name = generate_person_name()
            dealer_suffix = random.choice(["Motors", "Auto", "Automotive", "Cars", "Auto Group"])
            company_name = f"{last_name} {dealer_suffix}"
            customer_name = company_name

        # Generate address
        address = generate_customer_address()

        # Customer since date
        years_ago = np.random.exponential(scale=4)
        years_ago = min(years_ago, 20)
        customer_since = datetime.now() - timedelta(days=int(years_ago * 365))

        # Credit score based on segment
        min_score, max_score = credit_score_ranges[segment_name]
        credit_score = random.randint(min_score, max_score)

        # Lifetime value - correlated with segment and tenure
        base_ltv = {
            "Individual": random.randint(30000, 150000),
            "Fleet": random.randint(200000, 2000000),
            "Dealer": random.randint(500000, 10000000),
        }[segment_name]
        tenure_factor = min(years_ago / 10, 1.5)
        lifetime_value = int(base_ltv * tenure_factor)

        # Is active - higher churn for older accounts
        is_active = random.random() > (years_ago * 0.02)

        records.append(
            {
                "customer_id": f"CUST-{i:05d}",
                "segment_id": segment_id,
                "customer_name": customer_name,
                "first_name": first_name,
                "last_name": last_name,
                "company_name": company_name,
                "email": generate_email(first_name, last_name),
                "phone": fake.phone_number(),
                "street_address": address["street"],
                "city": address["city"],
                "state": address["state"],
                "zip_code": address["zip_code"],
                "country": address["country"],
                "customer_since": customer_since.date(),
                "credit_score": credit_score,
                "lifetime_value": lifetime_value,
                "is_active": is_active,
            }
        )

    df = pd.DataFrame(records)

    # Apply NULL injection based on cleanliness
    null_rate = get_null_rate(cleanliness, base_rate=0.15)
    if null_rate > 0:
        df = inject_nulls(df, "email", null_rate)
        df = inject_nulls(df, "phone", null_rate)
        df = inject_nulls(df, "street_address", null_rate * 0.5)  # Less likely to be missing

    return df


def generate_interactions(customers_df: pd.DataFrame, cleanliness: int = 100) -> pd.DataFrame:
    """
    Generate customer interaction history correlated with LTV.

    Higher LTV customers have more interactions.

    Args:
        customers_df: DataFrame with customer data including lifetime_value
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)

    Returns:
        DataFrame with interaction records
    """
    interaction_types = [
        ("Phone Call", 0.25),
        ("Email", 0.35),
        ("In-Person Visit", 0.15),
        ("Test Drive", 0.10),
        ("Service Appointment", 0.10),
        ("Website Chat", 0.05),
    ]
    type_names, type_weights = zip(*interaction_types)

    outcomes = [
        ("Resolved", 0.45),
        ("Follow-up Required", 0.25),
        ("Information Provided", 0.20),
        ("Escalated", 0.05),
        ("No Answer", 0.05),
    ]
    outcome_names, outcome_weights = zip(*outcomes)

    sentiments = [
        ("Positive", 0.40),
        ("Neutral", 0.45),
        ("Negative", 0.15),
    ]
    sentiment_names, sentiment_weights = zip(*sentiments)

    records = []
    interaction_id = 1

    for _, customer in customers_df.iterrows():
        customer_id = customer["customer_id"]
        ltv = customer["lifetime_value"]
        customer_since = pd.to_datetime(customer["customer_since"])

        # Number of interactions correlated with LTV
        # Base: 1-5 for low LTV, 10-50 for high LTV
        ltv_factor = min(ltv / 500000, 1.0)
        min_interactions = max(1, int(1 + ltv_factor * 5))
        max_interactions = max(min_interactions + 1, int(5 + ltv_factor * 45))
        num_interactions = random.randint(min_interactions, max_interactions)

        # Generate interaction dates since customer creation
        end_date = datetime.now()
        start_date = max(customer_since, datetime.now() - timedelta(days=730))

        if start_date >= end_date:
            start_date = end_date - timedelta(days=30)

        interaction_dates = generate_dates_with_seasonality(num_interactions, start_date, end_date)

        for int_date in interaction_dates:
            interaction_type = random.choices(type_names, weights=type_weights)[0]
            outcome = random.choices(outcome_names, weights=outcome_weights)[0]
            sentiment = random.choices(sentiment_names, weights=sentiment_weights)[0]

            # Duration based on interaction type
            if interaction_type == "Phone Call":
                duration_minutes = random.randint(5, 45)
            elif interaction_type == "In-Person Visit":
                duration_minutes = random.randint(30, 180)
            elif interaction_type == "Test Drive":
                duration_minutes = random.randint(20, 60)
            elif interaction_type == "Service Appointment":
                duration_minutes = random.randint(60, 240)
            else:
                duration_minutes = random.randint(2, 20)

            # Generate notes based on cleanliness (more notes at lower cleanliness = messier data)
            # At cleanliness=100, notes are always None
            # At cleanliness=0, ~30% of interactions have notes
            notes = None
            notes_rate = (100 - cleanliness) / 100 * 0.3
            if random.random() < notes_rate:
                note_templates = [
                    f"Customer called about {interaction_type.lower()}",
                    f"Follow-up needed for {outcome.lower()}",
                    f"Sentiment was {sentiment.lower()} during interaction",
                    "See attached documentation",
                    "Transferred to manager",
                    "Customer requested callback",
                ]
                notes = random.choice(note_templates)

            records.append(
                {
                    "interaction_id": f"INT-{interaction_id:08d}",
                    "customer_id": customer_id,
                    "interaction_type": interaction_type,
                    "interaction_date": int_date,
                    "duration_minutes": duration_minutes,
                    "outcome": outcome,
                    "sentiment": sentiment,
                    "notes": notes,
                }
            )
            interaction_id += 1

    df = pd.DataFrame(records)

    # Apply NULL injection to duration_minutes based on cleanliness
    null_rate = get_null_rate(cleanliness, base_rate=0.10)
    if null_rate > 0:
        df = inject_nulls(df, "duration_minutes", null_rate)

    return df


def generate_leads(
    customers_df: pd.DataFrame,
    salesperson_ids: list[str] | None = None,
    conversion_rate: float = 0.20,
    cleanliness: int = 100,
) -> pd.DataFrame:
    """
    Generate sales leads including unconverted leads.

    Converted leads link to existing customers. Unconverted leads
    are standalone prospects.

    Args:
        customers_df: DataFrame with customer data
        salesperson_ids: List of valid salesperson IDs
        conversion_rate: Proportion of leads that convert (~20%)
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)

    Returns:
        DataFrame with lead data
    """
    # Lead sources
    sources = [
        ("Website", 0.35),
        ("Phone Inquiry", 0.20),
        ("Walk-In", 0.15),
        ("Referral", 0.12),
        ("Social Media", 0.08),
        ("Auto Show", 0.05),
        ("Partner", 0.05),
    ]
    source_names, source_weights = zip(*sources)

    # Lead statuses for unconverted
    unconverted_statuses = [
        ("Cold", 0.30),
        ("Contacted", 0.25),
        ("Qualified", 0.20),
        ("Proposal", 0.10),
        ("Lost", 0.15),
    ]
    unconv_status_names, unconv_status_weights = zip(*unconverted_statuses)

    # Interest levels
    interest_levels = [
        ("High", 0.25),
        ("Medium", 0.50),
        ("Low", 0.25),
    ]
    interest_names, interest_weights = zip(*interest_levels)

    # Vehicle interests
    vehicle_interests = ["Sedan", "SUV", "Truck", "Sports Car", "Luxury", "Electric", "Hybrid"]

    records = []
    lead_id = 1

    # Generate converted leads (linked to customers)
    customer_ids = customers_df["customer_id"].tolist()
    num_converted = int(len(customer_ids) * conversion_rate / (1 - conversion_rate))

    # Some customers came from leads
    customers_from_leads = random.sample(customer_ids, min(num_converted, len(customer_ids)))

    for customer_id in customers_from_leads:
        customer = customers_df[customers_df["customer_id"] == customer_id].iloc[0]
        customer_since = pd.to_datetime(customer["customer_since"])

        # Lead date is before customer creation
        days_before = random.randint(7, 90)
        lead_date = customer_since - timedelta(days=days_before)

        source = random.choices(source_names, weights=source_weights)[0]
        salesperson_id = random.choice(salesperson_ids) if salesperson_ids else f"SP-{random.randint(1, 50):04d}"

        records.append(
            {
                "lead_id": f"LEAD-{lead_id:07d}",
                "customer_id": customer_id,
                "first_name": customer["first_name"],
                "last_name": customer["last_name"],
                "email": customer["email"],
                "phone": customer["phone"],
                "source": source,
                "status": "Converted",
                "interest_level": "High",
                "vehicle_interest": random.choice(vehicle_interests),
                "salesperson_id": salesperson_id,
                "created_date": lead_date,
                "last_contact_date": customer_since - timedelta(days=random.randint(1, 7)),
                "converted_date": customer_since,
                "is_converted": True,
            }
        )
        lead_id += 1

    # Generate unconverted leads
    num_unconverted = int(len(customers_from_leads) / conversion_rate * (1 - conversion_rate))

    for _ in range(num_unconverted):
        first_name, last_name = generate_person_name()

        # Lead date within last 2 years
        days_ago = random.randint(1, 730)
        lead_date = datetime.now() - timedelta(days=days_ago)

        source = random.choices(source_names, weights=source_weights)[0]
        status = random.choices(unconv_status_names, weights=unconv_status_weights)[0]
        interest_level = random.choices(interest_names, weights=interest_weights)[0]
        salesperson_id = random.choice(salesperson_ids) if salesperson_ids else f"SP-{random.randint(1, 50):04d}"

        # Last contact based on status
        if status in ("Cold", "Lost"):
            last_contact_days = random.randint(30, 365)
        else:
            last_contact_days = random.randint(1, 30)
        last_contact = lead_date + timedelta(days=min(last_contact_days, days_ago))

        records.append(
            {
                "lead_id": f"LEAD-{lead_id:07d}",
                "customer_id": None,
                "first_name": first_name,
                "last_name": last_name,
                "email": generate_email(first_name, last_name),
                "phone": fake.phone_number(),
                "source": source,
                "status": status,
                "interest_level": interest_level,
                "vehicle_interest": random.choice(vehicle_interests),
                "salesperson_id": salesperson_id,
                "created_date": lead_date,
                "last_contact_date": last_contact,
                "converted_date": None,
                "is_converted": False,
            }
        )
        lead_id += 1

    df = pd.DataFrame(records)

    # Apply NULL injection based on cleanliness
    null_rate = get_null_rate(cleanliness, base_rate=0.15)
    if null_rate > 0:
        df = inject_nulls(df, "phone", null_rate)
        df = inject_nulls(df, "last_contact_date", null_rate * 0.5)

    return df


def generate_crm_domain(
    scale: float = 1.0,
    cleanliness: int = 100,
    salesperson_ids: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Generate all CRM domain tables.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)
        salesperson_ids: List of valid salesperson IDs from sales domain

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    print("  Generating customer_segments...")
    customer_segments = generate_customer_segments()

    print("  Generating customers...")
    customers = generate_customers(n=scale_count(50000, scale), cleanliness=cleanliness)

    print("  Generating interactions...")
    interactions = generate_interactions(customers, cleanliness=cleanliness)

    print("  Generating leads...")
    leads = generate_leads(
        customers,
        salesperson_ids=salesperson_ids,
        conversion_rate=0.20,
        cleanliness=cleanliness,
    )

    return {
        "customer_segments": customer_segments,
        "customers": customers,
        "interactions": interactions,
        "leads": leads,
    }
