"""
Velocity Motors Dataset - Sales Domain
=======================================

Generates sales-related tables:
- salespersons: Sales team members
- vehicles: Vehicle inventory
- orders: Customer orders
- order_items: Line items for each order
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .utils import (
    FEATURE_CATEGORIES,
    PRICE_CHANGE_REASONS,
    TERRITORY_DIVISIONS,
    TERRITORY_REGIONS,
    generate_dates_with_seasonality,
    generate_email,
    generate_person_name,
    generate_vehicle_data,
    get_null_rate,
    inject_nulls,
    scale_count,
)


def generate_territories() -> pd.DataFrame:
    """
    Generate territories table with flat hierarchy (division > region > territory).

    Returns:
        DataFrame with ~18 territories (2 per region, 3 regions per division)
    """
    records = []
    territory_id = 1

    for division in TERRITORY_DIVISIONS:
        for region in TERRITORY_REGIONS[division]:
            # 2 territories per region
            for i in range(2):
                suffix = "North" if i == 0 else "South"
                records.append(
                    {
                        "territory_id": f"TER-{territory_id:03d}",
                        "territory_name": f"{region} {suffix}",
                        "region_name": region,
                        "division_name": division,
                        "is_active": random.random() > 0.05,  # 95% active
                    }
                )
                territory_id += 1

    return pd.DataFrame(records)


def generate_salespersons(
    n: int = 50,
    cleanliness: int = 100,
    territory_ids: list[str] | None = None,
) -> pd.DataFrame:
    """
    Generate salesperson dimension table.

    Args:
        n: Number of salespersons to generate
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)
        territory_ids: List of valid territory IDs for FK references

    Returns:
        DataFrame with salesperson data
    """
    regions = ["Northeast", "Southeast", "Midwest", "Southwest", "West", "Pacific Northwest"]
    region_weights = [0.20, 0.18, 0.17, 0.15, 0.20, 0.10]

    records = []
    for i in range(1, n + 1):
        first_name, last_name = generate_person_name()

        # Hire date distribution - more recent hires more common
        years_ago = np.random.exponential(scale=3)
        years_ago = min(years_ago, 15)  # Cap at 15 years
        hire_date = datetime.now() - timedelta(days=int(years_ago * 365))

        # Quota and commission based on seniority
        seniority_factor = min(years_ago / 10, 1.0)
        base_quota = random.randint(80000, 150000)
        quota = int(base_quota * (1 + seniority_factor * 0.5))

        # Commission rate: 1.5% - 4% based on seniority
        commission_rate = round(0.015 + (seniority_factor * 0.025), 3)

        region = random.choices(regions, weights=region_weights)[0]

        # Territory assignment - distribute evenly if provided
        if territory_ids:
            territory_id = territory_ids[i % len(territory_ids)]
        else:
            territory_id = f"TER-{(i % 18) + 1:03d}"

        records.append(
            {
                "salesperson_id": f"SP-{i:04d}",
                "first_name": first_name,
                "last_name": last_name,
                "name": f"{first_name} {last_name}",
                "email": generate_email(first_name, last_name),
                "hire_date": hire_date.date(),
                "region": region,
                "territory_id": territory_id,
                "quota": quota,
                "commission_rate": commission_rate,
                "manager_id": None,  # Placeholder, will be filled below
            }
        )

    df = pd.DataFrame(records)

    # Build org hierarchy - top 10% are managers with NULL manager_id
    # Remaining 90% point to one of the managers
    n_managers = max(1, int(n * 0.10))
    manager_ids = df.iloc[:n_managers]["salesperson_id"].tolist()

    # Managers have NULL manager_id (they are top-level)
    # Non-managers point to a random manager
    manager_id_values: list[str | None] = []
    for i in range(n):
        if i < n_managers:
            manager_id_values.append(None)
        else:
            manager_id_values.append(random.choice(manager_ids))
    df["manager_id"] = manager_id_values

    # Apply NULL injection based on cleanliness
    null_rate = get_null_rate(cleanliness, base_rate=0.10)
    if null_rate > 0:
        df = inject_nulls(df, "email", null_rate)

    return df


def generate_vehicles(n: int = 5000, cleanliness: int = 100, use_extended: bool = False) -> pd.DataFrame:
    """
    Generate vehicle inventory table.

    Args:
        n: Number of vehicles to generate
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)
        use_extended: If True, include extended vehicle makes (more variety)

    Returns:
        DataFrame with vehicle inventory data
    """
    conditions = [
        ("New", 0.60),
        ("Certified Pre-Owned", 0.25),
        ("Used", 0.15),
    ]

    statuses = [
        ("Available", 0.70),
        ("Reserved", 0.10),
        ("Sold", 0.15),
        ("In Transit", 0.05),
    ]

    records = []
    for i in range(1, n + 1):
        vehicle_data = generate_vehicle_data(use_extended=use_extended)

        # Condition selection
        condition_names, condition_weights = zip(*conditions)
        condition = random.choices(condition_names, weights=condition_weights)[0]

        # Mileage based on condition
        if condition == "New":
            mileage = random.randint(0, 50)
        elif condition == "Certified Pre-Owned":
            mileage = random.randint(10000, 45000)
        else:
            mileage = random.randint(25000, 120000)

        # Adjust MSRP based on condition and mileage
        if condition == "Certified Pre-Owned":
            price_factor = 0.80 - (mileage / 200000)
        elif condition == "Used":
            price_factor = 0.65 - (mileage / 150000)
        else:
            price_factor = 1.0

        adjusted_msrp = int(vehicle_data["msrp"] * max(price_factor, 0.40))

        # Status selection
        status_names, status_weights = zip(*statuses)
        status = random.choices(status_names, weights=status_weights)[0]

        records.append(
            {
                "vehicle_id": f"VH-{i:06d}",
                "vin": vehicle_data["vin"],
                "make": vehicle_data["make"],
                "model": vehicle_data["model"],
                "year": vehicle_data["year"],
                "trim": vehicle_data["trim"],
                "color": vehicle_data["color"],
                "msrp": adjusted_msrp,
                "condition": condition,
                "mileage": mileage,
                "status": status,
            }
        )

    return pd.DataFrame(records)


def generate_orders(
    n: int = 100000,
    customer_ids: list[str] | None = None,
    vehicle_ids: list[str] | None = None,
    salesperson_ids: list[str] | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    cleanliness: int = 100,
) -> pd.DataFrame:
    """
    Generate orders table with seasonal date distribution.

    Args:
        n: Number of orders to generate
        customer_ids: List of valid customer IDs (REQUIRED for FK integrity)
        vehicle_ids: List of valid vehicle IDs
        salesperson_ids: List of valid salesperson IDs
        start_date: Start of date range (default: 2 years ago)
        end_date: End of date range (default: today)
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)

    Returns:
        DataFrame with order data
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=730)
    if end_date is None:
        end_date = datetime.now()

    # Generate seasonal dates
    order_dates = generate_dates_with_seasonality(n, start_date, end_date)
    order_dates.sort()

    # Order statuses
    statuses = [
        ("Completed", 0.85),
        ("Pending", 0.05),
        ("Processing", 0.05),
        ("Cancelled", 0.05),
    ]
    status_names, status_weights = zip(*statuses)

    # Payment methods
    payment_methods = [
        ("Financing", 0.55),
        ("Cash", 0.20),
        ("Lease", 0.15),
        ("Trade-In + Financing", 0.10),
    ]
    payment_names, payment_weights = zip(*payment_methods)

    records = []
    for i in range(1, n + 1):
        order_date = order_dates[i - 1]

        # Select foreign keys
        customer_id = random.choice(customer_ids) if customer_ids else f"CUST-{random.randint(1, 50000):05d}"
        vehicle_id = random.choice(vehicle_ids) if vehicle_ids else f"VH-{random.randint(1, 5000):06d}"
        salesperson_id = random.choice(salesperson_ids) if salesperson_ids else f"SP-{random.randint(1, 50):04d}"

        status = random.choices(status_names, weights=status_weights)[0]
        payment_method = random.choices(payment_names, weights=payment_weights)[0]

        records.append(
            {
                "order_id": f"ORD-{i:08d}",
                "customer_id": customer_id,
                "vehicle_id": vehicle_id,
                "salesperson_id": salesperson_id,
                "order_date": order_date,
                "status": status,
                "payment_method": payment_method,
            }
        )

    return pd.DataFrame(records)


def generate_order_items(orders_df: pd.DataFrame, vehicles_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate order line items (vehicle + optional accessories/services).

    Each order has:
    - 1 vehicle (required)
    - 0-3 accessories
    - 0-2 services

    Args:
        orders_df: Orders DataFrame with order_id and vehicle_id
        vehicles_df: Vehicles DataFrame with pricing info

    Returns:
        DataFrame with order item data
    """
    # Create vehicle price lookup
    vehicle_prices = vehicles_df.set_index("vehicle_id")["msrp"].to_dict()

    # Accessories with price ranges
    accessories = [
        ("Extended Warranty - 3 Year", 1500, 2500),
        ("Extended Warranty - 5 Year", 2500, 4000),
        ("All-Weather Floor Mats", 150, 300),
        ("Cargo Liner", 100, 200),
        ("Roof Rack", 400, 800),
        ("Running Boards", 600, 1200),
        ("Trailer Hitch", 400, 700),
        ("Remote Start", 300, 500),
        ("Window Tinting", 200, 500),
        ("Paint Protection Film", 800, 2000),
        ("Ceramic Coating", 600, 1500),
        ("Wheel Locks", 50, 100),
        ("Cargo Net", 30, 75),
        ("First Aid Kit", 25, 50),
    ]

    # Services with price ranges
    services = [
        ("Pre-Delivery Inspection", 0, 0),
        ("Vehicle Registration", 200, 500),
        ("Documentation Fee", 300, 500),
        ("Delivery Fee", 500, 1500),
        ("Gap Insurance", 400, 800),
        ("Paint Sealant Application", 300, 600),
        ("Nitrogen Tire Fill", 50, 100),
    ]

    records = []
    item_id = 1

    for _, order in orders_df.iterrows():
        order_id = order["order_id"]
        vehicle_id = order["vehicle_id"]

        # Get vehicle price
        vehicle_price = vehicle_prices.get(vehicle_id, random.randint(25000, 60000))

        # Add vehicle line item
        records.append(
            {
                "order_item_id": f"OI-{item_id:010d}",
                "order_id": order_id,
                "item_type": "Vehicle",
                "item_description": f"Vehicle: {vehicle_id}",
                "quantity": 1,
                "unit_price": vehicle_price,
                "total_price": vehicle_price,
            }
        )
        item_id += 1

        # Add random accessories (0-3)
        num_accessories = random.choices([0, 1, 2, 3], weights=[0.3, 0.35, 0.25, 0.1])[0]
        selected_accessories = random.sample(accessories, min(num_accessories, len(accessories)))

        for acc_name, min_price, max_price in selected_accessories:
            price = random.randint(min_price, max_price)
            records.append(
                {
                    "order_item_id": f"OI-{item_id:010d}",
                    "order_id": order_id,
                    "item_type": "Accessory",
                    "item_description": acc_name,
                    "quantity": 1,
                    "unit_price": price,
                    "total_price": price,
                }
            )
            item_id += 1

        # Add services (0-2)
        num_services = random.choices([0, 1, 2], weights=[0.2, 0.5, 0.3])[0]
        selected_services = random.sample(services, min(num_services, len(services)))

        for svc_name, min_price, max_price in selected_services:
            price = random.randint(min_price, max_price) if max_price > 0 else 0
            records.append(
                {
                    "order_item_id": f"OI-{item_id:010d}",
                    "order_id": order_id,
                    "item_type": "Service",
                    "item_description": svc_name,
                    "quantity": 1,
                    "unit_price": price,
                    "total_price": price,
                }
            )
            item_id += 1

    return pd.DataFrame(records)


def generate_features() -> pd.DataFrame:
    """
    Generate features dimension table (catalog of all available features).

    Returns:
        DataFrame with ~35 features across 5 categories
    """
    records = []
    feature_id = 1

    for category, feature_names in FEATURE_CATEGORIES.items():
        for feature_name in feature_names:
            records.append(
                {
                    "feature_id": f"FEAT-{feature_id:03d}",
                    "feature_name": feature_name,
                    "feature_category": category,
                    "description": f"{feature_name} - {category} feature",
                }
            )
            feature_id += 1

    return pd.DataFrame(records)


def generate_vehicle_features(
    vehicles_df: pd.DataFrame,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate vehicle_features junction table (many-to-many).

    Each vehicle gets 3-10 features (weighted toward 5-7).
    Premium trims get more optional features.

    Args:
        vehicles_df: Vehicles DataFrame
        features_df: Features DataFrame

    Returns:
        DataFrame with vehicle-feature mappings
    """
    feature_ids = features_df["feature_id"].tolist()
    records = []
    vf_id = 1

    for _, vehicle in vehicles_df.iterrows():
        vehicle_id = vehicle["vehicle_id"]
        trim = vehicle.get("trim", "Base")

        # Determine number of features (3-10, weighted)
        if trim in ["Limited", "Platinum", "Premium", "High Country", "Elite", "Touring"]:
            num_features = random.choices([6, 7, 8, 9, 10], weights=[0.1, 0.2, 0.3, 0.25, 0.15])[0]
        else:
            num_features = random.choices([3, 4, 5, 6, 7], weights=[0.1, 0.2, 0.35, 0.25, 0.1])[0]

        # Select unique features for this vehicle
        selected_features = random.sample(feature_ids, min(num_features, len(feature_ids)))

        for feature_id in selected_features:
            # ~60% standard, ~40% optional
            is_standard = random.random() < 0.6

            records.append(
                {
                    "vehicle_feature_id": f"VF-{vf_id:08d}",
                    "vehicle_id": vehicle_id,
                    "feature_id": feature_id,
                    "is_standard": is_standard,
                }
            )
            vf_id += 1

    return pd.DataFrame(records)


def generate_price_history(
    vehicles_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate price_history table (SCD Type 2).

    Each vehicle has 1-5 price records.
    - is_current=True only for latest record
    - end_date=None for current record

    Args:
        vehicles_df: Vehicles DataFrame with vehicle_id and msrp

    Returns:
        DataFrame with price history records
    """
    records = []
    ph_id = 1

    for _, vehicle in vehicles_df.iterrows():
        vehicle_id = vehicle["vehicle_id"]
        base_msrp = vehicle["msrp"]

        # Number of price changes (1-5, weighted toward 1-2)
        num_prices = random.choices([1, 2, 3, 4, 5], weights=[0.40, 0.30, 0.15, 0.10, 0.05])[0]

        # Generate dates going back from today
        today = datetime.now().date()
        dates = sorted(
            [today - timedelta(days=random.randint(0, 365)) for _ in range(num_prices)]
        )

        current_price = base_msrp
        for i, effective_date in enumerate(dates):
            is_current = i == len(dates) - 1
            end_date = None if is_current else dates[i + 1] - timedelta(days=1)

            # Price varies by -15% to +5% from previous
            if i > 0:
                change_pct = random.uniform(-0.15, 0.05)
                current_price = current_price * (1 + change_pct)

            records.append(
                {
                    "price_history_id": f"PH-{ph_id:08d}",
                    "vehicle_id": vehicle_id,
                    "price": round(current_price, 2),
                    "effective_date": effective_date,
                    "end_date": end_date,
                    "is_current": is_current,
                    "change_reason": random.choice(PRICE_CHANGE_REASONS),
                }
            )
            ph_id += 1

    return pd.DataFrame(records)


def add_order_totals(
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    cleanliness: int = 100,
) -> pd.DataFrame:
    """
    Add order_total and discount_amount to orders DataFrame.

    Called after order_items are generated to calculate totals.

    Args:
        orders_df: Orders DataFrame
        order_items_df: Order items DataFrame
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)

    Returns:
        Orders DataFrame with order_total and discount_amount columns added
    """
    # Calculate actual totals from order_items
    actual_totals = order_items_df.groupby("order_id")["total_price"].sum().to_dict()

    order_totals = []
    discount_amounts = []

    for _, order in orders_df.iterrows():
        order_id = order["order_id"]
        actual_total = actual_totals.get(order_id, 0)

        # Add ~2% intentional variance (for testing data quality scenarios)
        if cleanliness < 100 and random.random() < 0.02:
            variance = random.uniform(-0.03, 0.03)
            order_total = round(actual_total * (1 + variance), 2)
        else:
            order_total = round(actual_total, 2)

        order_totals.append(order_total)

        # Discount: 0-15% of order_total (weighted toward 0, NULL for some)
        # ~30% no discount (0), ~50% small discount (1-5%), ~15% medium (5-10%), ~5% large (10-15%)
        discount_choice = random.choices(
            ["none", "small", "medium", "large"],
            weights=[0.30, 0.50, 0.15, 0.05],
        )[0]

        if discount_choice == "none":
            discount_amount = None if random.random() < 0.5 else 0.0
        elif discount_choice == "small":
            discount_amount = round(order_total * random.uniform(0.01, 0.05), 2)
        elif discount_choice == "medium":
            discount_amount = round(order_total * random.uniform(0.05, 0.10), 2)
        else:
            discount_amount = round(order_total * random.uniform(0.10, 0.15), 2)

        discount_amounts.append(discount_amount)

    orders_df = orders_df.copy()
    orders_df["order_total"] = order_totals
    orders_df["discount_amount"] = discount_amounts

    return orders_df


def generate_sales_domain(
    scale: float = 1.0,
    cleanliness: int = 100,
    customer_ids: list[str] | None = None,
    territory_ids: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Generate all sales domain tables.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)
        customer_ids: List of valid customer IDs for FK references in orders
        territory_ids: List of valid territory IDs for FK references in salespersons

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    # Determine if we should use extended makes (at cleanliness < 90)
    use_extended = cleanliness < 90

    # Generate territories first (if not provided)
    print("  Generating territories...")
    territories = generate_territories()
    if territory_ids is None:
        territory_ids = territories["territory_id"].tolist()

    print("  Generating salespersons...")
    salespersons = generate_salespersons(
        n=scale_count(50, scale),
        cleanliness=cleanliness,
        territory_ids=territory_ids,
    )

    print("  Generating vehicles...")
    vehicles = generate_vehicles(
        n=scale_count(5000, scale),
        cleanliness=cleanliness,
        use_extended=use_extended,
    )

    # Generate features dimension table
    print("  Generating features...")
    features = generate_features()

    # Generate vehicle_features junction table
    print("  Generating vehicle_features...")
    vehicle_features = generate_vehicle_features(vehicles, features)

    # Generate price_history (SCD Type 2)
    print("  Generating price_history...")
    price_history = generate_price_history(vehicles)

    print("  Generating orders...")
    orders = generate_orders(
        n=scale_count(100000, scale),
        customer_ids=customer_ids,
        vehicle_ids=vehicles["vehicle_id"].tolist(),
        salesperson_ids=salespersons["salesperson_id"].tolist(),
        cleanliness=cleanliness,
    )

    print("  Generating order_items...")
    order_items = generate_order_items(orders, vehicles)

    # Add order totals after order_items are generated
    print("  Adding order totals...")
    orders = add_order_totals(orders, order_items, cleanliness=cleanliness)

    return {
        "territories": territories,
        "salespersons": salespersons,
        "vehicles": vehicles,
        "features": features,
        "vehicle_features": vehicle_features,
        "price_history": price_history,
        "orders": orders,
        "order_items": order_items,
    }
