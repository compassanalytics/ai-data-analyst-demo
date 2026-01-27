"""
Velocity Motors Dataset - Shared Utilities
==========================================

Provides shared utilities for generating consistent, realistic automotive data.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
from faker import Faker

# Initialize faker with US locale
fake = Faker('en_US')


def set_random_seed(seed: int) -> None:
    """
    Set random seed for reproducibility across all random number generators.

    Args:
        seed: Integer seed value
    """
    random.seed(seed)
    np.random.seed(seed)
    Faker.seed(seed)


# Valid WMI (World Manufacturer Identifier) codes for common makes
WMI_CODES = {
    '1FA': 'Ford',
    '2T1': 'Toyota',
    '1HG': 'Honda',
    '3GN': 'Chevrolet',
    'WBA': 'BMW',
    'WDD': 'Mercedes-Benz',
}


def generate_vin() -> str:
    """
    Generate a 17-character VIN with valid WMI code.

    The VIN follows a simplified format:
    - Positions 1-3: WMI (World Manufacturer Identifier)
    - Positions 4-9: Vehicle descriptor section
    - Position 10: Model year (simplified)
    - Positions 11-17: Serial number

    Note: This does not include proper check digit calculation.

    Returns:
        17-character VIN string
    """
    wmi = random.choice(list(WMI_CODES.keys()))

    # Valid VIN characters (no I, O, Q to avoid confusion)
    vin_chars = '0123456789ABCDEFGHJKLMNPRSTUVWXYZ'

    # Vehicle descriptor section (positions 4-9)
    vds = ''.join(random.choices(vin_chars, k=6))

    # Model year code (position 10) - simplified
    year_codes = 'ABCDEFGHJKLMNPRSTVWXY123456789'
    year_code = random.choice(year_codes)

    # Plant code (position 11)
    plant_code = random.choice(vin_chars)

    # Sequential number (positions 12-17)
    seq_num = ''.join(random.choices('0123456789', k=6))

    return f"{wmi}{vds}{year_code}{plant_code}{seq_num}"


# Vehicle makes with their models and available trims
VEHICLE_MAKES_MODELS: Dict[str, List[Tuple[str, List[str]]]] = {
    'Ford': [
        ('F-150', ['XL', 'XLT', 'Lariat', 'King Ranch', 'Platinum', 'Limited']),
        ('Mustang', ['EcoBoost', 'GT', 'Mach 1', 'Shelby GT500']),
        ('Explorer', ['Base', 'XLT', 'Limited', 'ST', 'Platinum']),
        ('Escape', ['S', 'SE', 'SEL', 'Titanium']),
        ('Bronco', ['Base', 'Big Bend', 'Outer Banks', 'Badlands', 'Wildtrak']),
    ],
    'Toyota': [
        ('Camry', ['LE', 'SE', 'XLE', 'XSE', 'TRD']),
        ('Corolla', ['L', 'LE', 'SE', 'XLE', 'XSE']),
        ('RAV4', ['LE', 'XLE', 'XLE Premium', 'Adventure', 'Limited', 'TRD Off-Road']),
        ('Tacoma', ['SR', 'SR5', 'TRD Sport', 'TRD Off-Road', 'Limited', 'TRD Pro']),
        ('Highlander', ['L', 'LE', 'XLE', 'Limited', 'Platinum']),
    ],
    'Honda': [
        ('Civic', ['LX', 'Sport', 'EX', 'Touring', 'Si', 'Type R']),
        ('Accord', ['LX', 'Sport', 'EX-L', 'Sport 2.0T', 'Touring']),
        ('CR-V', ['LX', 'EX', 'EX-L', 'Touring']),
        ('Pilot', ['LX', 'EX', 'EX-L', 'Touring', 'Elite', 'TrailSport']),
        ('HR-V', ['LX', 'Sport', 'EX-L']),
    ],
    'Chevrolet': [
        ('Silverado', ['WT', 'Custom', 'LT', 'RST', 'LTZ', 'High Country']),
        ('Equinox', ['LS', 'LT', 'RS', 'Premier']),
        ('Tahoe', ['LS', 'LT', 'Z71', 'Premier', 'High Country']),
        ('Camaro', ['1LS', '1LT', '2LT', '1SS', '2SS', 'ZL1']),
        ('Colorado', ['WT', 'LT', 'Z71', 'ZR2']),
    ],
    'BMW': [
        ('3 Series', ['330i', '330i xDrive', 'M340i', 'M340i xDrive']),
        ('5 Series', ['530i', '530i xDrive', '540i', '540i xDrive', 'M550i xDrive']),
        ('X3', ['sDrive30i', 'xDrive30i', 'M40i']),
        ('X5', ['sDrive40i', 'xDrive40i', 'xDrive45e', 'M50i']),
        ('7 Series', ['740i', '740i xDrive', '760i xDrive']),
    ],
    'Mercedes-Benz': [
        ('C-Class', ['C 300', 'C 300 4MATIC', 'AMG C 43', 'AMG C 63']),
        ('E-Class', ['E 350', 'E 350 4MATIC', 'E 450', 'AMG E 53', 'AMG E 63 S']),
        ('GLC', ['GLC 300', 'GLC 300 4MATIC', 'AMG GLC 43', 'AMG GLC 63']),
        ('GLE', ['GLE 350', 'GLE 350 4MATIC', 'GLE 450', 'AMG GLE 53', 'AMG GLE 63 S']),
        ('S-Class', ['S 500', 'S 500 4MATIC', 'S 580', 'S 580 4MATIC', 'AMG S 63']),
    ],
}


# MSRP ranges by make (min, max) in dollars
MSRP_RANGES: Dict[str, Tuple[int, int]] = {
    'Ford': (28000, 85000),
    'Toyota': (22000, 70000),
    'Honda': (24000, 55000),
    'Chevrolet': (26000, 90000),
    'BMW': (45000, 150000),
    'Mercedes-Benz': (48000, 180000),
}


# Common vehicle colors with their popularity weights
VEHICLE_COLORS = [
    ('White', 0.23),
    ('Black', 0.22),
    ('Gray', 0.18),
    ('Silver', 0.15),
    ('Blue', 0.10),
    ('Red', 0.08),
    ('Green', 0.02),
    ('Brown', 0.01),
    ('Orange', 0.01),
]


def generate_vehicle_data() -> Dict:
    """
    Generate a complete vehicle data dictionary with realistic attributes.

    Returns:
        Dictionary with make, model, year, trim, color, msrp, vin
    """
    make = random.choice(list(VEHICLE_MAKES_MODELS.keys()))
    model, trims = random.choice(VEHICLE_MAKES_MODELS[make])
    trim = random.choice(trims)

    # Get MSRP based on make range
    min_msrp, max_msrp = MSRP_RANGES[make]
    # Luxury trims tend to be more expensive
    if any(x in trim.lower() for x in ['platinum', 'limited', 'touring', 'high country', 'amg', 'shelby']):
        msrp = random.randint(int(max_msrp * 0.7), max_msrp)
    elif any(x in trim.lower() for x in ['lx', 'l', 'base', 'wt', 'ls', 'xl']):
        msrp = random.randint(min_msrp, int(min_msrp * 1.3))
    else:
        msrp = random.randint(int(min_msrp * 1.1), int(max_msrp * 0.8))

    # Year distribution - more recent years more common
    current_year = datetime.now().year
    year_weights = [0.35, 0.30, 0.20, 0.10, 0.05]
    years = list(range(current_year, current_year - 5, -1))
    year = random.choices(years, weights=year_weights)[0]

    # Color selection with weights
    colors, weights = zip(*VEHICLE_COLORS)
    color = random.choices(colors, weights=weights)[0]

    return {
        'make': make,
        'model': model,
        'year': year,
        'trim': trim,
        'color': color,
        'msrp': msrp,
        'vin': generate_vin(),
    }


# Part categories with prefix and part names
PART_CATEGORIES: Dict[str, List[str]] = {
    'ENG': [
        'Oil Filter', 'Air Filter', 'Spark Plug', 'Timing Belt', 'Water Pump',
        'Fuel Pump', 'Alternator', 'Starter Motor', 'Radiator', 'Thermostat',
        'Engine Mount', 'Valve Cover Gasket', 'Head Gasket', 'Crankshaft Seal',
    ],
    'BRK': [
        'Brake Pad Set - Front', 'Brake Pad Set - Rear', 'Brake Rotor - Front',
        'Brake Rotor - Rear', 'Brake Caliper', 'Brake Line', 'Brake Fluid',
        'Brake Master Cylinder', 'ABS Sensor', 'Parking Brake Cable',
    ],
    'ELE': [
        'Battery', 'Headlight Assembly', 'Taillight Assembly', 'Fuse Box',
        'Ignition Coil', 'Oxygen Sensor', 'Mass Air Flow Sensor', 'Wiring Harness',
        'Instrument Cluster', 'Power Window Motor', 'Door Lock Actuator',
    ],
    'BOD': [
        'Front Bumper', 'Rear Bumper', 'Hood', 'Fender', 'Door Panel',
        'Side Mirror', 'Windshield', 'Rear Window', 'Grille', 'Spoiler',
        'Roof Rack', 'Running Board', 'Mud Flap', 'Wheel Well Liner',
    ],
    'SUS': [
        'Shock Absorber - Front', 'Shock Absorber - Rear', 'Strut Assembly',
        'Control Arm', 'Ball Joint', 'Tie Rod End', 'Sway Bar Link',
        'Wheel Bearing', 'CV Axle', 'Steering Rack', 'Power Steering Pump',
    ],
    'TRN': [
        'Transmission Fluid', 'Clutch Kit', 'Flywheel', 'Torque Converter',
        'Transmission Mount', 'Shift Cable', 'Differential Fluid',
        'Drive Shaft', 'U-Joint', 'Transfer Case',
    ],
}


def generate_part_number() -> Tuple[str, str, str]:
    """
    Generate a realistic part number with category and name.

    Format: CAT-####[A-C] where CAT is the category prefix.

    Returns:
        Tuple of (part_number, category_code, part_name)
    """
    category = random.choice(list(PART_CATEGORIES.keys()))
    part_name = random.choice(PART_CATEGORIES[category])

    # Generate part number: CAT-####[A-C]
    num = random.randint(1000, 9999)
    suffix = random.choice('ABC')
    part_number = f"{category}-{num}{suffix}"

    return part_number, category, part_name


# Seasonal multipliers for date generation (1.0 = baseline)
SEASONAL_MULTIPLIERS: Dict[int, float] = {
    1: 0.85,   # January - post-holiday slowdown
    2: 0.90,   # February
    3: 1.00,   # March - tax refunds start
    4: 1.05,   # April - tax refund spending
    5: 1.05,   # May
    6: 1.00,   # June
    7: 0.95,   # July - summer slowdown
    8: 0.90,   # August
    9: 0.95,   # September - back to school
    10: 1.00,  # October
    11: 1.20,  # November - holiday sales begin (Q4 spike)
    12: 1.20,  # December - holiday season (Q4 spike)
}


def generate_dates_with_seasonality(
    n: int,
    start_date: datetime,
    end_date: datetime,
) -> List[datetime]:
    """
    Generate dates with seasonal weighting (Q4 has higher volume).

    Args:
        n: Number of dates to generate
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of datetime objects with seasonal distribution
    """
    # Generate all dates in range
    date_range = []
    current = start_date
    while current <= end_date:
        date_range.append(current)
        current += timedelta(days=1)

    # Calculate weights based on seasonal multipliers
    weights = []
    for d in date_range:
        weight = SEASONAL_MULTIPLIERS.get(d.month, 1.0)
        weights.append(weight)

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Sample dates with weights
    selected_dates = random.choices(date_range, weights=weights, k=n)

    # Add random time component
    result = []
    for d in selected_dates:
        # Business hours weighted (9am-6pm more likely)
        if random.random() < 0.85:
            hour = random.randint(9, 18)
        else:
            hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        result.append(d.replace(hour=hour, minute=minute, second=second))

    return result


def generate_customer_address() -> Dict:
    """
    Generate a realistic US customer address using Faker.

    Returns:
        Dictionary with street, city, state, zip_code, country
    """
    return {
        'street': fake.street_address(),
        'city': fake.city(),
        'state': fake.state_abbr(),
        'zip_code': fake.zipcode(),
        'country': 'USA',
    }


def generate_person_name() -> Tuple[str, str]:
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
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com', 'aol.com']

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


# US States with population-based weights for realistic distribution
US_STATES_WEIGHTED = [
    ('CA', 0.12), ('TX', 0.09), ('FL', 0.07), ('NY', 0.06), ('PA', 0.04),
    ('IL', 0.04), ('OH', 0.04), ('GA', 0.03), ('NC', 0.03), ('MI', 0.03),
    ('NJ', 0.03), ('VA', 0.03), ('WA', 0.02), ('AZ', 0.02), ('MA', 0.02),
    ('TN', 0.02), ('IN', 0.02), ('MO', 0.02), ('MD', 0.02), ('WI', 0.02),
    ('CO', 0.02), ('MN', 0.02), ('SC', 0.02), ('AL', 0.01), ('LA', 0.01),
    ('KY', 0.01), ('OR', 0.01), ('OK', 0.01), ('CT', 0.01), ('UT', 0.01),
]


def get_weighted_state() -> str:
    """
    Get a US state with population-based weighting.

    Returns:
        Two-letter state abbreviation
    """
    states, weights = zip(*US_STATES_WEIGHTED)
    return random.choices(states, weights=weights)[0]
