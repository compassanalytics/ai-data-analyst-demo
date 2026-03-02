"""
Velocity Motors Dataset - Shared Utilities
==========================================

Provides shared utilities for generating consistent, realistic automotive data.
"""

import random
from collections.abc import Callable
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# Initialize faker with US locale
fake = Faker("en_US")


# NULLABLE_FIELDS allowlist - fields that can safely be NULLed
NULLABLE_FIELDS: dict[str, set[str]] = {
    "customers": {"email", "phone", "street_address", "company_name"},
    "interactions": {"notes", "duration_minutes"},
    "service_orders": {"notes", "customer_rating"},
    "leads": {"phone", "last_contact_date"},
    "salespersons": {"email", "manager_id"},  # manager_id NULL for top-level
    "territories": set(),  # No nullable fields
    "features": set(),
    "vehicle_features": set(),
    "price_history": {"end_date"},  # end_date is NULL for current
    "orders": {"discount_amount"},  # Some orders have no discount
}


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
    "1FA": "Ford",
    "2T1": "Toyota",
    "1HG": "Honda",
    "3GN": "Chevrolet",
    "WBA": "BMW",
    "WDD": "Mercedes-Benz",
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
    vin_chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"

    # Vehicle descriptor section (positions 4-9)
    vds = "".join(random.choices(vin_chars, k=6))

    # Model year code (position 10) - simplified
    year_codes = "ABCDEFGHJKLMNPRSTVWXY123456789"
    year_code = random.choice(year_codes)

    # Plant code (position 11)
    plant_code = random.choice(vin_chars)

    # Sequential number (positions 12-17)
    seq_num = "".join(random.choices("0123456789", k=6))

    return f"{wmi}{vds}{year_code}{plant_code}{seq_num}"


# Vehicle makes with their models and available trims
VEHICLE_MAKES_MODELS: dict[str, list[tuple[str, list[str]]]] = {
    "Ford": [
        ("F-150", ["XL", "XLT", "Lariat", "King Ranch", "Platinum", "Limited"]),
        ("Mustang", ["EcoBoost", "GT", "Mach 1", "Shelby GT500"]),
        ("Explorer", ["Base", "XLT", "Limited", "ST", "Platinum"]),
        ("Escape", ["S", "SE", "SEL", "Titanium"]),
        ("Bronco", ["Base", "Big Bend", "Outer Banks", "Badlands", "Wildtrak"]),
    ],
    "Toyota": [
        ("Camry", ["LE", "SE", "XLE", "XSE", "TRD"]),
        ("Corolla", ["L", "LE", "SE", "XLE", "XSE"]),
        ("RAV4", ["LE", "XLE", "XLE Premium", "Adventure", "Limited", "TRD Off-Road"]),
        ("Tacoma", ["SR", "SR5", "TRD Sport", "TRD Off-Road", "Limited", "TRD Pro"]),
        ("Highlander", ["L", "LE", "XLE", "Limited", "Platinum"]),
    ],
    "Honda": [
        ("Civic", ["LX", "Sport", "EX", "Touring", "Si", "Type R"]),
        ("Accord", ["LX", "Sport", "EX-L", "Sport 2.0T", "Touring"]),
        ("CR-V", ["LX", "EX", "EX-L", "Touring"]),
        ("Pilot", ["LX", "EX", "EX-L", "Touring", "Elite", "TrailSport"]),
        ("HR-V", ["LX", "Sport", "EX-L"]),
    ],
    "Chevrolet": [
        ("Silverado", ["WT", "Custom", "LT", "RST", "LTZ", "High Country"]),
        ("Equinox", ["LS", "LT", "RS", "Premier"]),
        ("Tahoe", ["LS", "LT", "Z71", "Premier", "High Country"]),
        ("Camaro", ["1LS", "1LT", "2LT", "1SS", "2SS", "ZL1"]),
        ("Colorado", ["WT", "LT", "Z71", "ZR2"]),
    ],
    "BMW": [
        ("3 Series", ["330i", "330i xDrive", "M340i", "M340i xDrive"]),
        ("5 Series", ["530i", "530i xDrive", "540i", "540i xDrive", "M550i xDrive"]),
        ("X3", ["sDrive30i", "xDrive30i", "M40i"]),
        ("X5", ["sDrive40i", "xDrive40i", "xDrive45e", "M50i"]),
        ("7 Series", ["740i", "740i xDrive", "760i xDrive"]),
    ],
    "Mercedes-Benz": [
        ("C-Class", ["C 300", "C 300 4MATIC", "AMG C 43", "AMG C 63"]),
        ("E-Class", ["E 350", "E 350 4MATIC", "E 450", "AMG E 53", "AMG E 63 S"]),
        ("GLC", ["GLC 300", "GLC 300 4MATIC", "AMG GLC 43", "AMG GLC 63"]),
        ("GLE", ["GLE 350", "GLE 350 4MATIC", "GLE 450", "AMG GLE 53", "AMG GLE 63 S"]),
        ("S-Class", ["S 500", "S 500 4MATIC", "S 580", "S 580 4MATIC", "AMG S 63"]),
    ],
}


# Extended vehicle makes with models and trims (for lower cleanliness levels)
VEHICLE_MAKES_MODELS_EXTENDED: dict[str, dict[str, list[str]]] = {
    "Nissan": {
        "models": ["Altima", "Sentra", "Maxima", "Rogue", "Murano", "Pathfinder", "Armada", "Frontier", "Titan"],
        "trims": ["S", "SV", "SL", "Platinum"],
    },
    "Hyundai": {
        "models": ["Elantra", "Sonata", "Tucson", "Santa Fe", "Palisade", "Kona", "Venue"],
        "trims": ["SE", "SEL", "Limited", "Calligraphy"],
    },
    "Kia": {
        "models": ["Forte", "K5", "Sportage", "Sorento", "Telluride", "Seltos", "Soul"],
        "trims": ["LX", "S", "EX", "SX"],
    },
    "Subaru": {
        "models": ["Impreza", "Legacy", "Outback", "Forester", "Crosstrek", "Ascent", "WRX"],
        "trims": ["Base", "Premium", "Limited", "Touring"],
    },
    "Mazda": {
        "models": ["Mazda3", "Mazda6", "CX-30", "CX-5", "CX-50", "CX-9", "MX-5 Miata"],
        "trims": ["Base", "Select", "Preferred", "Premium", "Turbo"],
    },
    "Volkswagen": {
        "models": ["Jetta", "Passat", "Tiguan", "Atlas", "Taos", "ID.4", "Golf GTI"],
        "trims": ["S", "SE", "SEL", "R-Line"],
    },
    "Audi": {
        "models": ["A3", "A4", "A6", "Q3", "Q5", "Q7", "e-tron"],
        "trims": ["Premium", "Premium Plus", "Prestige", "S Line"],
    },
    "Lexus": {"models": ["ES", "IS", "LS", "NX", "RX", "GX", "LX"], "trims": ["Base", "Premium", "Luxury", "F Sport"]},
    "Acura": {"models": ["ILX", "TLX", "RDX", "MDX", "Integra"], "trims": ["Base", "Technology", "A-Spec", "Advance"]},
}


# MSRP ranges for extended makes (min, max) in dollars
MSRP_RANGES_EXTENDED: dict[str, tuple[int, int]] = {
    "Nissan": (22000, 65000),
    "Hyundai": (20000, 55000),
    "Kia": (19000, 52000),
    "Subaru": (23000, 48000),
    "Mazda": (24000, 42000),
    "Volkswagen": (22000, 55000),
    "Audi": (35000, 95000),
    "Lexus": (40000, 110000),
    "Acura": (32000, 75000),
}


# MSRP ranges by make (min, max) in dollars
MSRP_RANGES: dict[str, tuple[int, int]] = {
    "Ford": (28000, 85000),
    "Toyota": (22000, 70000),
    "Honda": (24000, 55000),
    "Chevrolet": (26000, 90000),
    "BMW": (45000, 150000),
    "Mercedes-Benz": (48000, 180000),
}


# Vehicle model trend profiles: (make, model) -> trend type
# Determines how each model's popularity changes over Q1 2024 - Q4 2025
MODEL_TREND_PROFILES: dict[tuple[str, str], str] = {
    # Sharp decline — compact SUVs losing ground
    ("Ford", "Escape"): "sharp_decline",
    ("Honda", "HR-V"): "sharp_decline",
    # Declining — luxury sedans and sports cars fading
    ("Chevrolet", "Camaro"): "declining",
    ("BMW", "7 Series"): "declining",
    ("Mercedes-Benz", "S-Class"): "declining",
    # Growing — mid-size SUVs gaining
    ("Toyota", "RAV4"): "growing",
    ("Ford", "Bronco"): "growing",
    ("Chevrolet", "Equinox"): "growing",
    # Surging — specific hot models
    ("Toyota", "Tacoma"): "surging",
    ("BMW", "X3"): "surging",
    # Flat — everything else (20 models)
    ("Ford", "F-150"): "flat",
    ("Ford", "Mustang"): "flat",
    ("Ford", "Explorer"): "flat",
    ("Toyota", "Camry"): "flat",
    ("Toyota", "Corolla"): "flat",
    ("Toyota", "Highlander"): "flat",
    ("Honda", "Civic"): "flat",
    ("Honda", "Accord"): "flat",
    ("Honda", "CR-V"): "flat",
    ("Honda", "Pilot"): "flat",
    ("Chevrolet", "Silverado"): "flat",
    ("Chevrolet", "Tahoe"): "flat",
    ("Chevrolet", "Colorado"): "flat",
    ("BMW", "3 Series"): "flat",
    ("BMW", "5 Series"): "flat",
    ("BMW", "X5"): "flat",
    ("Mercedes-Benz", "C-Class"): "flat",
    ("Mercedes-Benz", "E-Class"): "flat",
    ("Mercedes-Benz", "GLC"): "flat",
    ("Mercedes-Benz", "GLE"): "flat",
}

# Quarter-based weight multipliers for each trend profile
# 8 quarters: Q1 2024 (index 0) through Q4 2025 (index 7)
TREND_MULTIPLIERS: dict[str, list[float]] = {
    "surging": [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.15, 1.25],
    "growing": [0.90, 0.92, 0.95, 0.98, 1.00, 1.03, 1.08, 1.12],
    "flat": [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    "declining": [1.10, 1.05, 1.00, 0.95, 0.90, 0.85, 0.80, 0.75],
    "sharp_decline": [1.15, 1.10, 1.00, 0.90, 0.80, 0.70, 0.55, 0.45],
}


def get_quarter_index(date: datetime) -> int:
    """
    Map a date to quarter index 0-7 (Q1 2024 through Q4 2025).

    Clamps to 0 for dates before Q1 2024 and 7 for dates after Q4 2025.

    Args:
        date: Datetime to map

    Returns:
        Integer index 0-7
    """
    q = (date.year - 2024) * 4 + (date.month - 1) // 3
    return max(0, min(7, q))


# Salesperson performance tiers with order volume weights and population fractions
SALESPERSON_PERFORMANCE_TIERS: dict[str, dict[str, float]] = {
    "star": {"weight": 2.00, "fraction": 0.10},
    "above_average": {"weight": 1.40, "fraction": 0.20},
    "average": {"weight": 1.00, "fraction": 0.40},
    "below_average": {"weight": 0.65, "fraction": 0.20},
    "underperformer": {"weight": 0.35, "fraction": 0.10},
}


# Common vehicle colors with their popularity weights
VEHICLE_COLORS = [
    ("White", 0.23),
    ("Black", 0.22),
    ("Gray", 0.18),
    ("Silver", 0.15),
    ("Blue", 0.10),
    ("Red", 0.08),
    ("Green", 0.02),
    ("Brown", 0.01),
    ("Orange", 0.01),
]


def generate_vehicle_data(use_extended: bool = False) -> dict:
    """
    Generate a complete vehicle data dictionary with realistic attributes.

    Args:
        use_extended: If True, include extended makes (9 additional makes).
                      Used at lower cleanliness levels for more variety.

    Returns:
        Dictionary with make, model, year, trim, color, msrp, vin
    """
    # Decide whether to use base makes or extended makes
    use_extended_make = use_extended and random.random() < 0.4  # 40% chance for extended

    if use_extended_make:
        make = random.choice(list(VEHICLE_MAKES_MODELS_EXTENDED.keys()))
        make_data = VEHICLE_MAKES_MODELS_EXTENDED[make]
        model = random.choice(make_data["models"])
        trim = random.choice(make_data["trims"])
        min_msrp, max_msrp = MSRP_RANGES_EXTENDED[make]
    else:
        make = random.choice(list(VEHICLE_MAKES_MODELS.keys()))
        model, trims = random.choice(VEHICLE_MAKES_MODELS[make])
        trim = random.choice(trims)
        min_msrp, max_msrp = MSRP_RANGES[make]

    # Luxury trims tend to be more expensive
    if any(
        x in trim.lower()
        for x in [
            "platinum",
            "limited",
            "touring",
            "high country",
            "amg",
            "shelby",
            "prestige",
            "calligraphy",
            "f sport",
        ]
    ):
        msrp = random.randint(int(max_msrp * 0.7), max_msrp)
    elif any(x in trim.lower() for x in ["lx", "l", "base", "wt", "ls", "xl", "s", "se"]):
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
        "make": make,
        "model": model,
        "year": year,
        "trim": trim,
        "color": color,
        "msrp": msrp,
        "vin": generate_vin(),
    }


# Part categories with prefix and part names
PART_CATEGORIES: dict[str, list[str]] = {
    "ENG": [
        "Oil Filter",
        "Air Filter",
        "Spark Plug",
        "Timing Belt",
        "Water Pump",
        "Fuel Pump",
        "Alternator",
        "Starter Motor",
        "Radiator",
        "Thermostat",
        "Engine Mount",
        "Valve Cover Gasket",
        "Head Gasket",
        "Crankshaft Seal",
    ],
    "BRK": [
        "Brake Pad Set - Front",
        "Brake Pad Set - Rear",
        "Brake Rotor - Front",
        "Brake Rotor - Rear",
        "Brake Caliper",
        "Brake Line",
        "Brake Fluid",
        "Brake Master Cylinder",
        "ABS Sensor",
        "Parking Brake Cable",
    ],
    "ELE": [
        "Battery",
        "Headlight Assembly",
        "Taillight Assembly",
        "Fuse Box",
        "Ignition Coil",
        "Oxygen Sensor",
        "Mass Air Flow Sensor",
        "Wiring Harness",
        "Instrument Cluster",
        "Power Window Motor",
        "Door Lock Actuator",
    ],
    "BOD": [
        "Front Bumper",
        "Rear Bumper",
        "Hood",
        "Fender",
        "Door Panel",
        "Side Mirror",
        "Windshield",
        "Rear Window",
        "Grille",
        "Spoiler",
        "Roof Rack",
        "Running Board",
        "Mud Flap",
        "Wheel Well Liner",
    ],
    "SUS": [
        "Shock Absorber - Front",
        "Shock Absorber - Rear",
        "Strut Assembly",
        "Control Arm",
        "Ball Joint",
        "Tie Rod End",
        "Sway Bar Link",
        "Wheel Bearing",
        "CV Axle",
        "Steering Rack",
        "Power Steering Pump",
    ],
    "TRN": [
        "Transmission Fluid",
        "Clutch Kit",
        "Flywheel",
        "Torque Converter",
        "Transmission Mount",
        "Shift Cable",
        "Differential Fluid",
        "Drive Shaft",
        "U-Joint",
        "Transfer Case",
    ],
}


def generate_part_number() -> tuple[str, str, str]:
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
    suffix = random.choice("ABC")
    part_number = f"{category}-{num}{suffix}"

    return part_number, category, part_name


# Seasonal multipliers for date generation (1.0 = baseline)
SEASONAL_MULTIPLIERS: dict[int, float] = {
    1: 0.85,  # January - post-holiday slowdown
    2: 0.90,  # February
    3: 1.00,  # March - tax refunds start
    4: 1.05,  # April - tax refund spending
    5: 1.05,  # May
    6: 1.00,  # June
    7: 0.95,  # July - summer slowdown
    8: 0.90,  # August
    9: 0.95,  # September - back to school
    10: 1.00,  # October
    11: 1.20,  # November - holiday sales begin (Q4 spike)
    12: 1.20,  # December - holiday season (Q4 spike)
}


def economic_downturn_trend(date: datetime) -> float:
    """
    Multiplier encoding a Q4 2025 slowdown and Jan 2026+ market downturn.

    Applied on top of seasonal weights to create a visible economic trend:
    - Before Oct 2025: 1.0 (no effect)
    - Oct-Nov 2025: linear ramp from 1.0 down to 0.75
    - Dec 2025: 0.70
    - Jan 2026+: 0.65

    Args:
        date: Datetime to evaluate

    Returns:
        Multiplier float (0.65 to 1.0)
    """
    if date < datetime(2025, 10, 1):
        return 1.0
    elif date < datetime(2025, 12, 1):
        # Oct-Nov 2025: linear ramp from 1.0 down to 0.75
        days_in = (date - datetime(2025, 10, 1)).days
        return 1.0 - 0.25 * (days_in / 61.0)
    elif date < datetime(2026, 1, 1):
        return 0.70  # Dec 2025
    else:
        return 0.65  # Jan 2026+


def generate_dates_with_seasonality(
    n: int,
    start_date: datetime,
    end_date: datetime,
    trend_fn: Callable[[datetime], float] | None = None,
) -> list[datetime]:
    """
    Generate dates with seasonal weighting (Q4 has higher volume).

    Args:
        n: Number of dates to generate
        start_date: Start of date range
        end_date: End of date range
        trend_fn: Optional callable (date) -> float applied multiplicatively
                  on top of seasonal weights (e.g., economic_downturn_trend)

    Returns:
        List of datetime objects with seasonal distribution
    """
    # Generate all dates in range
    date_range = []
    current = start_date
    while current <= end_date:
        date_range.append(current)
        current += timedelta(days=1)

    # Calculate weights based on seasonal multipliers (and optional trend)
    weights = []
    for d in date_range:
        weight = SEASONAL_MULTIPLIERS.get(d.month, 1.0)
        if trend_fn is not None:
            weight *= trend_fn(d)
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


def generate_customer_address() -> dict:
    """
    Generate a realistic US customer address using Faker.

    Returns:
        Dictionary with street, city, state, zip_code, country
    """
    return {
        "street": fake.street_address(),
        "city": fake.city(),
        "state": fake.state_abbr(),
        "zip_code": fake.zipcode(),
        "country": "USA",
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
    ("KY", 0.01),
    ("OR", 0.01),
    ("OK", 0.01),
    ("CT", 0.01),
    ("UT", 0.01),
]


def get_weighted_state() -> str:
    """
    Get a US state with population-based weighting.

    Returns:
        Two-letter state abbreviation
    """
    states, weights = zip(*US_STATES_WEIGHTED)
    return random.choices(states, weights=weights)[0]


# Extended service types: (type_name, min_labor, max_labor, parts_ratio)
SERVICE_TYPES_EXTENDED: list[tuple[str, int, int, float]] = [
    ("Detailing", 100, 500, 0.05),
    ("State Inspection", 25, 75, 0.02),
    ("Windshield Repair", 50, 400, 0.60),
    ("Key Programming", 75, 300, 0.40),
    ("Suspension Work", 200, 1500, 0.45),
]


# Territory hierarchy
TERRITORY_DIVISIONS = ["East", "West", "Central"]
TERRITORY_REGIONS: dict[str, list[str]] = {
    "East": ["Northeast", "Southeast", "Mid-Atlantic"],
    "West": ["Pacific", "Mountain", "Southwest"],
    "Central": ["Midwest", "Great Plains", "Gulf Coast"],
}

# Per-region economic strength (before North/South split)
_TERRITORY_BASE_STRENGTH: dict[str, float] = {
    # Strong markets
    "Pacific": 1.30,
    "Mid-Atlantic": 1.28,
    "Northeast": 1.22,
    # Baseline markets
    "Southeast": 1.05,
    "Southwest": 1.02,
    "Mountain": 0.98,
    "Midwest": 0.95,
    # Weak markets
    "Great Plains": 0.80,
    "Gulf Coast": 0.78,
}

# Full territory strength mapping — derived from TERRITORY_REGIONS to ensure name consistency
# Adds slight North/South variation (±0.03) for per-territory differentiation
TERRITORY_STRENGTH: dict[str, float] = {}
for _div in TERRITORY_DIVISIONS:
    for _region in TERRITORY_REGIONS[_div]:
        _base = _TERRITORY_BASE_STRENGTH.get(_region, 1.0)
        TERRITORY_STRENGTH[f"{_region} North"] = round(_base + 0.03, 2)
        TERRITORY_STRENGTH[f"{_region} South"] = round(_base - 0.03, 2)


# Vehicle features by category
FEATURE_CATEGORIES: dict[str, list[str]] = {
    "Safety": [
        "Blind Spot Monitor",
        "Lane Departure Warning",
        "Forward Collision Warning",
        "Automatic Emergency Braking",
        "Adaptive Cruise Control",
        "360 Camera",
        "Rear Cross Traffic Alert",
        "Parking Sensors",
    ],
    "Comfort": [
        "Heated Seats",
        "Ventilated Seats",
        "Heated Steering Wheel",
        "Dual Zone Climate",
        "Tri Zone Climate",
        "Panoramic Sunroof",
        "Memory Seats",
        "Power Adjustable Pedals",
    ],
    "Technology": [
        "Navigation System",
        "Premium Audio",
        "Wireless Charging",
        "Apple CarPlay",
        "Android Auto",
        "Head-Up Display",
        "Digital Instrument Cluster",
        "Wi-Fi Hotspot",
    ],
    "Exterior": [
        "LED Headlights",
        "Power Liftgate",
        "Running Boards",
        "Roof Rack",
        "Tow Package",
        "Chrome Package",
    ],
    "Interior": [
        "Leather Seats",
        "Premium Interior",
        "Ambient Lighting",
        "Second Row Captain Chairs",
        "Third Row Seating",
    ],
}

PRICE_CHANGE_REASONS = [
    "Initial Pricing",
    "Market Adjustment",
    "Seasonal Promotion",
    "Inventory Clearance",
    "Model Year Update",
    "Demand Increase",
]


def inject_nulls(df: pd.DataFrame, column: str, rate: float, seed: int | None = None) -> pd.DataFrame:
    """
    Inject NULL values into a column at specified rate.

    Args:
        df: DataFrame to modify (modified in place)
        column: Column name to inject NULLs into
        rate: Fraction of rows to set to NULL (0.0 to 1.0)
        seed: Random seed for reproducibility

    Returns:
        Modified DataFrame
    """
    if column not in df.columns:
        return df
    if rate <= 0:
        return df

    rng = np.random.default_rng(seed)
    mask = rng.random(len(df)) < rate
    df.loc[mask, column] = None
    return df


def apply_case_inconsistency(value: str, intensity: float, rng: np.random.Generator) -> str:
    """
    Apply random case variations based on intensity.

    Args:
        value: String to potentially modify
        intensity: 0.0-1.0, probability of applying variation
        rng: Random number generator

    Returns:
        Possibly modified string
    """
    if not isinstance(value, str) or rng.random() > intensity:
        return value

    variation = rng.choice(["lower", "upper", "title", "original"])
    if variation == "lower":
        return value.lower()
    elif variation == "upper":
        return value.upper()
    elif variation == "title":
        return value.title()
    return value


def calculate_cleanliness_intensity(cleanliness: int, threshold: int) -> float:
    """
    Calculate pattern intensity from cleanliness level.

    Args:
        cleanliness: Current cleanliness level (0-100)
        threshold: Threshold below which pattern activates

    Returns:
        Intensity value (0.0-1.0), 0 if cleanliness >= threshold
    """
    if cleanliness >= threshold:
        return 0.0
    return (threshold - cleanliness) / threshold


def get_null_rate(cleanliness: int, base_rate: float = 0.15) -> float:
    """
    Calculate NULL injection rate based on cleanliness.

    At cleanliness=100, rate=0
    At cleanliness=0, rate=base_rate

    Args:
        cleanliness: Current cleanliness level (0-100)
        base_rate: Maximum NULL rate at cleanliness=0

    Returns:
        NULL injection rate (0.0 to base_rate)
    """
    if cleanliness >= 100:
        return 0.0
    return base_rate * (100 - cleanliness) / 100
