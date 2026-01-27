"""
Velocity Motors Dataset - Operations Domain
============================================

Generates operations-related tables:
- warehouse_locations: Distribution centers and warehouses
- suppliers: Parts and equipment suppliers
- parts_inventory: Parts stock levels
- service_orders: Vehicle service/maintenance orders
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from .utils import (
    generate_part_number,
    generate_customer_address,
    scale_count,
    get_weighted_state,
    fake,
)


def generate_warehouse_locations(n: int = 10) -> pd.DataFrame:
    """
    Generate warehouse/distribution center table.

    Args:
        n: Number of warehouses to generate

    Returns:
        DataFrame with warehouse data
    """
    warehouse_types = [
        ('Distribution Center', 0.30),
        ('Regional Warehouse', 0.40),
        ('Parts Depot', 0.30),
    ]
    type_names, type_weights = zip(*warehouse_types)

    records = []
    for i in range(1, n + 1):
        state = get_weighted_state()
        city = fake.city()

        warehouse_type = random.choices(type_names, weights=type_weights)[0]

        # Capacity based on type
        if warehouse_type == 'Distribution Center':
            capacity = random.randint(50000, 100000)
        elif warehouse_type == 'Regional Warehouse':
            capacity = random.randint(20000, 50000)
        else:
            capacity = random.randint(5000, 20000)

        # Current utilization (60-95%)
        utilization = random.uniform(0.60, 0.95)

        records.append({
            'warehouse_id': f'WH-{i:03d}',
            'warehouse_name': f'{city} {warehouse_type}',
            'warehouse_type': warehouse_type,
            'street_address': fake.street_address(),
            'city': city,
            'state': state,
            'zip_code': fake.zipcode(),
            'capacity_sqft': capacity,
            'current_utilization': round(utilization, 2),
            'manager_name': f'{fake.first_name()} {fake.last_name()}',
            'phone': fake.phone_number(),
            'is_active': True,
        })

    return pd.DataFrame(records)


def generate_suppliers(n: int = 50) -> pd.DataFrame:
    """
    Generate supplier table with ratings and lead times.

    Args:
        n: Number of suppliers to generate

    Returns:
        DataFrame with supplier data
    """
    supplier_types = [
        ('OEM', 0.20),
        ('Aftermarket', 0.40),
        ('Specialty', 0.20),
        ('Wholesale', 0.20),
    ]
    type_names, type_weights = zip(*supplier_types)

    # Categories each supplier type tends to specialize in
    type_specializations = {
        'OEM': ['ENG', 'TRN', 'ELE'],
        'Aftermarket': ['BRK', 'SUS', 'BOD'],
        'Specialty': ['ELE', 'ENG'],
        'Wholesale': ['BRK', 'BOD', 'SUS'],
    }

    records = []
    for i in range(1, n + 1):
        supplier_type = random.choices(type_names, weights=type_weights)[0]

        # Company name generation
        company_suffix = random.choice(['Parts', 'Supply', 'Components', 'Industries', 'Corp', 'Inc', 'LLC'])
        company_name = f'{fake.last_name()} {random.choice(["Auto", "Motor", "Vehicle", "Car"])} {company_suffix}'

        # Rating (3.0 - 5.0, weighted toward higher)
        rating = round(random.triangular(3.0, 5.0, 4.5), 1)

        # Lead time in days (OEM longer, wholesale shorter)
        lead_time_ranges = {
            'OEM': (7, 21),
            'Aftermarket': (3, 14),
            'Specialty': (5, 30),
            'Wholesale': (1, 7),
        }
        min_lt, max_lt = lead_time_ranges[supplier_type]
        lead_time_days = random.randint(min_lt, max_lt)

        # Specializations
        specializations = type_specializations[supplier_type]
        primary_category = random.choice(specializations)

        # Contract start date
        years_ago = random.uniform(1, 10)
        contract_start = datetime.now() - timedelta(days=int(years_ago * 365))

        # Is active based on rating
        is_active = rating >= 3.0 or random.random() < 0.1

        address = generate_customer_address()

        records.append({
            'supplier_id': f'SUP-{i:04d}',
            'supplier_name': company_name,
            'supplier_type': supplier_type,
            'primary_category': primary_category,
            'contact_name': f'{fake.first_name()} {fake.last_name()}',
            'contact_email': fake.company_email(),
            'contact_phone': fake.phone_number(),
            'street_address': address['street'],
            'city': address['city'],
            'state': address['state'],
            'zip_code': address['zip_code'],
            'country': address['country'],
            'rating': rating,
            'lead_time_days': lead_time_days,
            'contract_start_date': contract_start.date(),
            'payment_terms_days': random.choice([15, 30, 45, 60]),
            'is_active': is_active,
        })

    return pd.DataFrame(records)


def generate_parts_inventory(
    n: int = 2000,
    supplier_ids: Optional[List[str]] = None,
    warehouse_ids: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Generate parts inventory with inverse popularity correlation.

    More popular/common parts have higher stock levels.

    Args:
        n: Number of parts to generate
        supplier_ids: List of valid supplier IDs
        warehouse_ids: List of valid warehouse IDs

    Returns:
        DataFrame with parts inventory data
    """
    # Part popularity tiers (affects stock levels)
    popularity_tiers = [
        ('High Demand', 0.20, (100, 500)),      # Common parts, high stock
        ('Standard', 0.50, (25, 100)),          # Normal parts, medium stock
        ('Low Demand', 0.20, (5, 25)),          # Specialty parts, low stock
        ('Rare', 0.10, (1, 10)),                # Rare/obsolete parts, minimal stock
    ]

    records = []
    for i in range(1, n + 1):
        part_number, category, part_name = generate_part_number()

        # Select popularity tier
        tier_names = [t[0] for t in popularity_tiers]
        tier_weights = [t[1] for t in popularity_tiers]
        tier_stock_ranges = {t[0]: t[2] for t in popularity_tiers}

        popularity = random.choices(tier_names, weights=tier_weights)[0]
        min_stock, max_stock = tier_stock_ranges[popularity]

        # Stock quantity
        quantity = random.randint(min_stock, max_stock)

        # Reorder point based on popularity
        reorder_points = {
            'High Demand': random.randint(50, 100),
            'Standard': random.randint(20, 50),
            'Low Demand': random.randint(5, 20),
            'Rare': random.randint(1, 5),
        }
        reorder_point = reorder_points[popularity]

        # Cost based on category
        cost_ranges = {
            'ENG': (50, 2000),
            'BRK': (30, 500),
            'ELE': (20, 1500),
            'BOD': (100, 3000),
            'SUS': (40, 800),
            'TRN': (100, 2500),
        }
        min_cost, max_cost = cost_ranges.get(category, (20, 500))
        unit_cost = round(random.uniform(min_cost, max_cost), 2)

        # Foreign keys
        supplier_id = random.choice(supplier_ids) if supplier_ids else f'SUP-{random.randint(1, 50):04d}'
        warehouse_id = random.choice(warehouse_ids) if warehouse_ids else f'WH-{random.randint(1, 10):03d}'

        # Last restocked date
        days_ago = random.randint(1, 180)
        last_restocked = datetime.now() - timedelta(days=days_ago)

        # Status based on quantity vs reorder point
        if quantity == 0:
            status = 'Out of Stock'
        elif quantity <= reorder_point * 0.5:
            status = 'Critical Low'
        elif quantity <= reorder_point:
            status = 'Below Reorder'
        else:
            status = 'In Stock'

        records.append({
            'part_id': f'PART-{i:06d}',
            'part_number': part_number,
            'part_name': part_name,
            'category': category,
            'supplier_id': supplier_id,
            'warehouse_id': warehouse_id,
            'quantity_on_hand': quantity,
            'reorder_point': reorder_point,
            'unit_cost': unit_cost,
            'popularity_tier': popularity,
            'status': status,
            'last_restocked_date': last_restocked.date(),
        })

    return pd.DataFrame(records)


def generate_service_orders(
    n: int = 30000,
    customer_ids: Optional[List[str]] = None,
    vehicle_ids: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Generate service orders correlated with vehicle age.

    Older vehicles have more service orders.

    Args:
        n: Number of service orders to generate
        customer_ids: List of valid customer IDs
        vehicle_ids: List of valid vehicle IDs

    Returns:
        DataFrame with service order data
    """
    # Service types with average cost ranges
    service_types = [
        ('Oil Change', 30, 80, 0.30),
        ('Tire Rotation', 20, 50, 0.15),
        ('Brake Service', 150, 800, 0.12),
        ('Transmission Service', 200, 1500, 0.08),
        ('Engine Repair', 500, 5000, 0.05),
        ('AC Service', 100, 500, 0.08),
        ('Battery Replacement', 100, 300, 0.07),
        ('Alignment', 75, 150, 0.05),
        ('Inspection', 25, 100, 0.08),
        ('Recall Service', 0, 0, 0.02),
    ]

    type_names = [t[0] for t in service_types]
    type_weights = [t[3] for t in service_types]
    type_costs = {t[0]: (t[1], t[2]) for t in service_types}

    # Technician names
    technicians = [f'{fake.first_name()} {fake.last_name()[0]}.' for _ in range(20)]

    # Order statuses
    statuses = [
        ('Completed', 0.80),
        ('In Progress', 0.10),
        ('Scheduled', 0.05),
        ('Waiting for Parts', 0.03),
        ('Cancelled', 0.02),
    ]
    status_names, status_weights = zip(*statuses)

    records = []
    for i in range(1, n + 1):
        service_type = random.choices(type_names, weights=type_weights)[0]

        # Cost based on service type
        min_cost, max_cost = type_costs[service_type]
        if max_cost > 0:
            labor_cost = round(random.uniform(min_cost * 0.4, max_cost * 0.5), 2)
            parts_cost = round(random.uniform(min_cost * 0.3, max_cost * 0.6), 2)
        else:
            labor_cost = 0
            parts_cost = 0

        total_cost = round(labor_cost + parts_cost, 2)

        # Foreign keys
        customer_id = random.choice(customer_ids) if customer_ids else f'CUST-{random.randint(1, 50000):05d}'
        vehicle_id = random.choice(vehicle_ids) if vehicle_ids else f'VH-{random.randint(1, 5000):06d}'

        # Service date with seasonality
        days_ago = random.randint(1, 730)
        service_date = datetime.now() - timedelta(days=days_ago)

        # Duration based on service type
        duration_ranges = {
            'Oil Change': (30, 60),
            'Tire Rotation': (20, 45),
            'Brake Service': (60, 180),
            'Transmission Service': (120, 480),
            'Engine Repair': (240, 960),
            'AC Service': (60, 180),
            'Battery Replacement': (30, 60),
            'Alignment': (45, 90),
            'Inspection': (30, 60),
            'Recall Service': (60, 240),
        }
        min_dur, max_dur = duration_ranges.get(service_type, (30, 120))
        duration_minutes = random.randint(min_dur, max_dur)

        status = random.choices(status_names, weights=status_weights)[0]
        technician = random.choice(technicians)

        # Mileage at service (incrementing based on order)
        base_mileage = random.randint(5000, 150000)

        # Customer rating (only for completed)
        if status == 'Completed' and random.random() < 0.6:
            rating = random.choices([5, 4, 3, 2, 1], weights=[0.50, 0.30, 0.12, 0.05, 0.03])[0]
        else:
            rating = None

        records.append({
            'service_order_id': f'SVC-{i:08d}',
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'service_type': service_type,
            'service_date': service_date,
            'status': status,
            'labor_cost': labor_cost,
            'parts_cost': parts_cost,
            'total_cost': total_cost,
            'duration_minutes': duration_minutes,
            'technician_name': technician,
            'mileage_at_service': base_mileage,
            'customer_rating': rating,
            'notes': None,
        })

    return pd.DataFrame(records)


def generate_operations_domain(
    scale: float = 1.0,
    customer_ids: Optional[List[str]] = None,
    vehicle_ids: Optional[List[str]] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Generate all operations domain tables.

    Args:
        scale: Scale factor for record counts (1.0 = full, 0.1 = 10%)
        customer_ids: List of valid customer IDs from CRM domain
        vehicle_ids: List of valid vehicle IDs from sales domain

    Returns:
        Dictionary with table names as keys and DataFrames as values
    """
    print("  Generating warehouse_locations...")
    warehouses = generate_warehouse_locations(n=scale_count(10, scale))

    print("  Generating suppliers...")
    suppliers = generate_suppliers(n=scale_count(50, scale))

    print("  Generating parts_inventory...")
    parts_inventory = generate_parts_inventory(
        n=scale_count(2000, scale),
        supplier_ids=suppliers['supplier_id'].tolist(),
        warehouse_ids=warehouses['warehouse_id'].tolist(),
    )

    print("  Generating service_orders...")
    service_orders = generate_service_orders(
        n=scale_count(30000, scale),
        customer_ids=customer_ids,
        vehicle_ids=vehicle_ids,
    )

    return {
        'warehouse_locations': warehouses,
        'suppliers': suppliers,
        'parts_inventory': parts_inventory,
        'service_orders': service_orders,
    }
