"""
Healthcare Dataset - Shared Utilities
=====================================

Provides shared utilities for generating consistent, realistic healthcare data.
"""

import random
from datetime import datetime, timedelta

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


def generate_mrn() -> str:
    """
    Generate a Medical Record Number in MRN-XXXXXX format.

    Returns:
        MRN string in format MRN-XXXXXX
    """
    return f"MRN-{random.randint(100000, 999999)}"


def generate_npi() -> str:
    """
    Generate a 10-digit National Provider Identifier starting with 1 or 2.

    Note: This does not implement the Luhn check-digit algorithm.
    The generated NPIs are for demonstration purposes only.

    Returns:
        10-digit NPI string
    """
    first_digit = random.choice(["1", "2"])
    remaining = "".join(random.choices("0123456789", k=9))
    return f"{first_digit}{remaining}"


def generate_fictional_ssn() -> str:
    """
    Generate a clearly fictional SSN using the 000-XX-XXXX pattern.

    The 000 area number is never used by SSA, making these clearly fake.

    Returns:
        Fictional SSN string in format 000-XX-XXXX
    """
    group = random.randint(10, 99)
    serial = random.randint(1000, 9999)
    return f"000-{group:02d}-{serial}"


def generate_insurance_member_id(payer_type: str) -> str:
    """
    Generate a payer-specific member ID format.

    Args:
        payer_type: Name of the insurance payer

    Returns:
        Member ID string in payer-specific format
    """
    payer_prefixes = {
        "Medicare": "1EG4",
        "Medicaid": "MCD",
        "Blue Cross Blue Shield": "XYZ",
        "United Healthcare": "U",
        "Aetna": "W",
        "Cigna": "CGN",
        "Humana": "H",
        "Self-Pay": "SELF",
        "Workers Compensation": "WC",
    }

    prefix = payer_prefixes.get(payer_type, "MEM")

    if payer_type == "Medicare":
        # Medicare format: prefix + alphanumeric
        suffix = "".join(random.choices("0123456789", k=7))
        letter = random.choice("ABCDEFGHJKLMNPQRSTUVWXY")
        return f"{prefix}{suffix}{letter}"
    elif payer_type == "Medicaid":
        return f"{prefix}{random.randint(100000000, 999999999)}"
    elif payer_type == "Self-Pay":
        return f"{prefix}-{random.randint(10000, 99999)}"
    else:
        # Standard format: prefix + 9 digits
        return f"{prefix}{random.randint(100000000, 999999999)}"


def generate_patient_demographics() -> dict:
    """
    Generate realistic patient demographics with age skewed toward elderly.

    Returns:
        Dictionary with patient demographic information including:
        - first_name, last_name
        - dob, age, gender
        - address, city, state, zip_code
        - phone, email
    """
    # Age distribution skewed toward elderly (healthcare population)
    age_weights = [
        (0, 17, 0.10),  # Pediatric
        (18, 39, 0.15),  # Young adult
        (40, 54, 0.20),  # Middle age
        (55, 64, 0.20),  # Pre-retirement
        (65, 74, 0.20),  # Young elderly
        (75, 89, 0.12),  # Elderly
        (90, 100, 0.03),  # Very elderly
    ]

    # Select age range based on weights
    ranges, weights = [], []
    for min_age, max_age, weight in age_weights:
        ranges.append((min_age, max_age))
        weights.append(weight)

    selected_range = random.choices(ranges, weights=weights)[0]
    age = random.randint(selected_range[0], selected_range[1])

    # Calculate DOB from age
    today = datetime.now()
    birth_year = today.year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)  # Safe for all months
    dob = datetime(birth_year, birth_month, birth_day).date()

    # Gender distribution (slight female skew for healthcare)
    gender = random.choices(["Male", "Female"], weights=[0.48, 0.52])[0]

    # Generate name based on gender
    if gender == "Male":
        first_name = fake.first_name_male()
    else:
        first_name = fake.first_name_female()

    last_name = fake.last_name()

    # US States with population-based weights
    us_states = [
        ("CA", 0.12),
        ("TX", 0.09),
        ("FL", 0.07),
        ("NY", 0.06),
        ("PA", 0.04),
        ("IL", 0.04),
        ("OH", 0.04),
        ("GA", 0.03),
        ("NC", 0.03),
        ("MI", 0.03),
        ("NJ", 0.03),
        ("VA", 0.03),
        ("WA", 0.02),
        ("AZ", 0.02),
        ("MA", 0.02),
        ("TN", 0.02),
        ("IN", 0.02),
        ("MO", 0.02),
        ("MD", 0.02),
        ("WI", 0.02),
        ("CO", 0.02),
        ("MN", 0.02),
        ("SC", 0.02),
        ("AL", 0.01),
        ("LA", 0.01),
    ]
    states, state_weights = zip(*us_states)
    state = random.choices(states, weights=state_weights)[0]

    return {
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "age": age,
        "gender": gender,
        "address": fake.street_address(),
        "city": fake.city(),
        "state": state,
        "zip_code": fake.zipcode(),
        "phone": fake.phone_number(),
        "email": f"{first_name.lower()}.{last_name.lower()}@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com'])}",
    }


def generate_encounter_dates(encounter_type: str) -> tuple[datetime, datetime]:
    """
    Generate admit and discharge dates with realistic length of stay based on encounter type.

    Args:
        encounter_type: Type of encounter (Outpatient, Inpatient, Emergency, Observation, Telehealth)

    Returns:
        Tuple of (admit_datetime, discharge_datetime)
    """
    # Generate a date within the last 3 years
    days_ago = random.randint(0, 1095)  # ~3 years
    admit_date = datetime.now() - timedelta(days=days_ago)

    # Add time of day (business hours more common)
    if random.random() < 0.75:
        hour = random.randint(7, 18)
    else:
        hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    admit_datetime = admit_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Length of stay based on encounter type
    los_config = {
        "Outpatient": (0, 0, 0.5),  # Same day, 0-0.5 hours (visits measured in hours)
        "Telehealth": (0, 0, 0.25),  # Same day, 0-0.25 hours
        "Emergency": (0, 0, 6),  # Same day, 0-6 hours average
        "Observation": (0, 1, 24),  # 0-1 days, up to 24 hours
        "Inpatient": (1, 7, None),  # 1-7 days typical
    }

    min_days, max_days, hours = los_config.get(encounter_type, (0, 1, 4))

    if hours is not None and max_days == 0:
        # Same-day encounters - add hours
        los_hours = random.uniform(0.25, hours)
        discharge_datetime = admit_datetime + timedelta(hours=los_hours)
    else:
        # Multi-day encounters
        los_days = random.randint(min_days, max_days)
        # Add some randomness to the discharge time
        discharge_hour = random.randint(10, 18)  # Discharges typically during the day
        discharge_datetime = admit_datetime + timedelta(days=los_days)
        discharge_datetime = discharge_datetime.replace(hour=discharge_hour, minute=random.randint(0, 59))

    # Ensure discharge is after admit
    if discharge_datetime <= admit_datetime:
        discharge_datetime = admit_datetime + timedelta(hours=1)

    return admit_datetime, discharge_datetime


def generate_claim_amounts(encounter_type: str) -> dict[str, float]:
    """
    Generate realistic claim amounts based on encounter type.

    Args:
        encounter_type: Type of encounter

    Returns:
        Dictionary with billed_amount, allowed_amount, paid_amount, patient_responsibility
    """
    # Base amounts by encounter type
    amount_ranges = {
        "Outpatient": (150, 500),
        "Telehealth": (75, 200),
        "Emergency": (500, 5000),
        "Observation": (1000, 4000),
        "Inpatient": (5000, 50000),
    }

    min_amt, max_amt = amount_ranges.get(encounter_type, (100, 1000))
    billed_amount = round(random.uniform(min_amt, max_amt), 2)

    # Allowed amount is typically 40-70% of billed
    allowed_pct = random.uniform(0.40, 0.70)
    allowed_amount = round(billed_amount * allowed_pct, 2)

    # Insurance pays 70-95% of allowed amount
    paid_pct = random.uniform(0.70, 0.95)
    paid_amount = round(allowed_amount * paid_pct, 2)

    # Patient responsibility is the remainder
    patient_responsibility = round(allowed_amount - paid_amount, 2)

    return {
        "billed_amount": billed_amount,
        "allowed_amount": allowed_amount,
        "paid_amount": paid_amount,
        "patient_responsibility": patient_responsibility,
    }


def is_diagnosis_appropriate(code: str, gender: str, age: int) -> bool:
    """
    Check if a diagnosis code is clinically appropriate for the patient demographics.

    Args:
        code: ICD-10 code
        gender: Patient gender ('Male' or 'Female')
        age: Patient age in years

    Returns:
        True if diagnosis is appropriate, False otherwise
    """
    # Pregnancy codes only for females 12-55
    if code.startswith("O") or code.startswith("Z33") or code.startswith("Z34"):
        if gender != "Female" or age < 12 or age > 55:
            return False

    # Prostate conditions only for males
    if code.startswith("N40") or code.startswith("N41") or code.startswith("C61"):
        if gender != "Male":
            return False

    # Pediatric-specific conditions
    pediatric_codes = ["P", "Q"]  # Perinatal and congenital conditions
    if any(code.startswith(p) for p in pediatric_codes):
        if age > 18:
            return False

    # Age-related conditions more common in elderly
    elderly_codes = ["G30", "F03", "R54"]  # Alzheimer's, dementia, age-related debility
    if any(code.startswith(e) for e in elderly_codes):
        if age < 60:
            return False

    return True


def get_age_appropriate_diagnosis(gender: str, age: int, codes: list[tuple[str, str, str]]) -> tuple[str, str, str]:
    """
    Select a diagnosis that is appropriate for the patient demographics.

    Args:
        gender: Patient gender
        age: Patient age in years
        codes: List of (code, description, category) tuples

    Returns:
        Tuple of (code, description, category)
    """
    # Filter codes to those appropriate for this patient
    appropriate_codes = [(code, desc, cat) for code, desc, cat in codes if is_diagnosis_appropriate(code, gender, age)]

    # If no appropriate codes, fall back to symptoms (always appropriate)
    if not appropriate_codes:
        appropriate_codes = [(code, desc, cat) for code, desc, cat in codes if cat == "Symptoms"]

    # If still none, use the full list
    if not appropriate_codes:
        appropriate_codes = codes

    # Weight by age - elderly more likely to have chronic conditions
    if age >= 65:
        # Prefer chronic conditions
        chronic_categories = ["Diabetes", "Cardiovascular", "Respiratory", "Musculoskeletal"]
        chronic_codes = [c for c in appropriate_codes if c[2] in chronic_categories]
        if chronic_codes and random.random() < 0.7:
            return random.choice(chronic_codes)

    return random.choice(appropriate_codes)


def calculate_length_of_stay(admit_date: datetime, discharge_date: datetime) -> int:
    """
    Calculate length of stay in days.

    Args:
        admit_date: Admission datetime
        discharge_date: Discharge datetime

    Returns:
        Length of stay in days (minimum 0 for same-day)
    """
    delta = discharge_date.date() - admit_date.date()
    return max(0, delta.days)


def generate_encounter_id_prefix(encounter_type: str) -> str:
    """
    Generate an encounter ID prefix based on encounter type.

    Args:
        encounter_type: Type of encounter

    Returns:
        2-3 letter prefix string
    """
    prefixes = {
        "Outpatient": "OP",
        "Inpatient": "IP",
        "Emergency": "ED",
        "Observation": "OBS",
        "Telehealth": "TH",
    }
    return prefixes.get(encounter_type, "ENC")


def generate_flu_season_flag(date: datetime) -> bool:
    """
    Determine if a date falls within flu season (October - March).

    Args:
        date: Date to check

    Returns:
        True if date is during flu season
    """
    month = date.month
    return month >= 10 or month <= 3


def weighted_choice(choices: list[tuple[str, float]]) -> str:
    """
    Make a weighted random choice from a list of (value, weight) tuples.

    Args:
        choices: List of (value, weight) tuples

    Returns:
        Selected value
    """
    values, weights = zip(*choices)
    return random.choices(values, weights=weights)[0]
