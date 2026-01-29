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
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .utils import (
    generate_vehicle_data,
    generate_person_name,
    generate_email,
    generate_dates_with_seasonality,
    scale_count,
    inject_nulls,
    get_null_rate,
)


def generate_salespersons(n: int = 50, cleanliness: int = 100) -> pd.DataFrame:
    """
    Generate salesperson dimension table.

    Args:
        n: Number of salespersons to generate
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)

    Returns:
        DataFrame with salesperson data
    """
    regions = ['Northeast', 'Southeast', 'Midwest', 'Southwest', 'West', 'Pacific Northwest']
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

        records.append({
            'salesperson_id': f'SP-{i:04d}',
            'first_name': first_name,
            'last_name': last_name,
            'name': f'{first_name} {last_name}',
            'email': generate_email(first_name, last_name),
            'hire_date': hire_date.date(),
            'region': region,
            'quota': quota,
            'commission_rate': commission_rate,
        })

    df = pd.DataFrame(records)

    # Apply NULL injection based on cleanliness
    null_rate = get_null_rate(cleanliness, base_rate=0.10)
    if null_rate > 0:
        df = inject_nulls(df, 'email', null_rate)

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
        ('New', 0.60),
        ('Certified Pre-Owned', 0.25),
        ('Used', 0.15),
    ]

    statuses = [
        ('Available', 0.70),
        ('Reserved', 0.10),
        ('Sold', 0.15),
        ('In Transit', 0.05),
    ]

    records = []
    for i in range(1, n + 1):
        vehicle_data = generate_vehicle_data(use_extended=use_extended)

        # Condition selection
        condition_names, condition_weights = zip(*conditions)
        condition = random.choices(condition_names, weights=condition_weights)[0]

        # Mileage based on condition
        if condition == 'New':
            mileage = random.randint(0, 50)
        elif condition == 'Certified Pre-Owned':
            mileage = random.randint(10000, 45000)
        else:
            mileage = random.randint(25000, 120000)

        # Adjust MSRP based on condition and mileage
        if condition == 'Certified Pre-Owned':
            price_factor = 0.80 - (mileage / 200000)
        elif condition == 'Used':
            price_factor = 0.65 - (mileage / 150000)
        else:
            price_factor = 1.0

        adjusted_msrp = int(vehicle_data['msrp'] * max(price_factor, 0.40))

        # Status selection
        status_names, status_weights = zip(*statuses)
        status = random.choices(status_names, weights=status_weights)[0]

        records.append({
            'vehicle_id': f'VH-{i:06d}',
            'vin': vehicle_data['vin'],
            'make': vehicle_data['make'],
            'model': vehicle_data['model'],
            'year': vehicle_data['year'],
            'trim': vehicle_data['trim'],
            'color': vehicle_data['color'],
            'msrp': adjusted_msrp,
            'condition': condition,
            'mileage': mileage,
            'status': status,
        })

    return pd.DataFrame(records)


def generate_orders(
    n: int = 100000,
    customer_ids: Optional[List[str]] = None,
    vehicle_ids: Optional[List[str]] = None,
    salesperson_ids: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
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
        ('Completed', 0.85),
        ('Pending', 0.05),
        ('Processing', 0.05),
        ('Cancelled', 0.05),
    ]
    status_names, status_weights = zip(*statuses)

    # Payment methods
    payment_methods = [
        ('Financing', 0.55),
        ('Cash', 0.20),
        ('Lease', 0.15),
        ('Trade-In + Financing', 0.10),
    ]
    payment_names, payment_weights = zip(*payment_methods)

    records = []
    for i in range(1, n + 1):
        order_date = order_dates[i - 1]

        # Select foreign keys
        customer_id = random.choice(customer_ids) if customer_ids else f'CUST-{random.randint(1, 50000):05d}'
        vehicle_id = random.choice(vehicle_ids) if vehicle_ids else f'VH-{random.randint(1, 5000):06d}'
        salesperson_id = random.choice(salesperson_ids) if salesperson_ids else f'SP-{random.randint(1, 50):04d}'

        status = random.choices(status_names, weights=status_weights)[0]
        payment_method = random.choices(payment_names, weights=payment_weights)[0]

        records.append({
            'order_id': f'ORD-{i:08d}',
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'salesperson_id': salesperson_id,
            'order_date': order_date,
            'status': status,
            'payment_method': payment_method,
        })

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
    vehicle_prices = vehicles_df.set_index('vehicle_id')['msrp'].to_dict()

    # Accessories with price ranges
    accessories = [
        ('Extended Warranty - 3 Year', 1500, 2500),
        ('Extended Warranty - 5 Year', 2500, 4000),
        ('All-Weather Floor Mats', 150, 300),
        ('Cargo Liner', 100, 200),
        ('Roof Rack', 400, 800),
        ('Running Boards', 600, 1200),
        ('Trailer Hitch', 400, 700),
        ('Remote Start', 300, 500),
        ('Window Tinting', 200, 500),
        ('Paint Protection Film', 800, 2000),
        ('Ceramic Coating', 600, 1500),
        ('Wheel Locks', 50, 100),
        ('Cargo Net', 30, 75),
        ('First Aid Kit', 25, 50),
    ]

    # Services with price ranges
    services = [
        ('Pre-Delivery Inspection', 0, 0),
        ('Vehicle Registration', 200, 500),
        ('Documentation Fee', 300, 500),
        ('Delivery Fee', 500, 1500),
        ('Gap Insurance', 400, 800),
        ('Paint Sealant Application', 300, 600),
        ('Nitrogen Tire Fill', 50, 100),
    ]

    records = []
    item_id = 1

    for _, order in orders_df.iterrows():
        order_id = order['order_id']
        vehicle_id = order['vehicle_id']

        # Get vehicle price
        vehicle_price = vehicle_prices.get(vehicle_id, random.randint(25000, 60000))

        # Add vehicle line item
        records.append({
            'order_item_id': f'OI-{item_id:010d}',
            'order_id': order_id,
            'item_type': 'Vehicle',
            'item_description': f'Vehicle: {vehicle_id}',
            'quantity': 1,
            'unit_price': vehicle_price,
            'total_price': vehicle_price,
        })
        item_id += 1

        # Add random accessories (0-3)
        num_accessories = random.choices([0, 1, 2, 3], weights=[0.3, 0.35, 0.25, 0.1])[0]
        selected_accessories = random.sample(accessories, min(num_accessories, len(accessories)))

        for acc_name, min_price, max_price in selected_accessories:
            price = random.randint(min_price, max_price)
            records.append({
                'order_item_id': f'OI-{item_id:010d}',
                'order_id': order_id,
                'item_type': 'Accessory',
                'item_description': acc_name,
                'quantity': 1,
                'unit_price': price,
                'total_price': price,
            })
            item_id += 1

        # Add services (0-2)
        num_services = random.choices([0, 1, 2], weights=[0.2, 0.5, 0.3])[0]
        selected_services = random.sample(services, min(num_services, len(services)))

        for svc_name, min_price, max_price in selected_services:
            price = random.randint(min_price, max_price) if max_price > 0 else 0
            records.append({
                'order_item_id': f'OI-{item_id:010d}',
                'order_id': order_id,
                'item_type': 'Service',
                'item_description': svc_name,
                'quantity': 1,
                'unit_price': price,
                'total_price': price,
            })
            item_id += 1

    return pd.DataFrame(records)


def generate_sales_domain(
    scale: float = 1.0,
    cleanliness: int = 100,
    customer_ids: Optional[List[str]] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Generate all sales domain tables.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)
        cleanliness: Data cleanliness level 0-100 (100=pristine, 0=messy)
        customer_ids: List of valid customer IDs for FK references in orders

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    # Determine if we should use extended makes (at cleanliness < 90)
    use_extended = cleanliness < 90

    print("  Generating salespersons...")
    salespersons = generate_salespersons(n=scale_count(50, scale), cleanliness=cleanliness)

    print("  Generating vehicles...")
    vehicles = generate_vehicles(
        n=scale_count(5000, scale),
        cleanliness=cleanliness,
        use_extended=use_extended,
    )

    print("  Generating orders...")
    orders = generate_orders(
        n=scale_count(100000, scale),
        customer_ids=customer_ids,
        vehicle_ids=vehicles['vehicle_id'].tolist(),
        salesperson_ids=salespersons['salesperson_id'].tolist(),
        cleanliness=cleanliness,
    )

    print("  Generating order_items...")
    order_items = generate_order_items(orders, vehicles)

    return {
        'salespersons': salespersons,
        'vehicles': vehicles,
        'orders': orders,
        'order_items': order_items,
    }
