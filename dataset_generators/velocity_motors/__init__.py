"""
Velocity Motors Dataset Generator
=================================

A fictional automotive company dataset with 12 tables across 3 domains:

**Sales Domain:**
- salespersons: Sales team members
- vehicles: Vehicle inventory
- orders: Customer orders
- order_items: Line items for each order

**CRM Domain:**
- customer_segments: Customer segment definitions
- customers: Customer master data
- interactions: Customer interaction history
- leads: Sales leads (converted and unconverted)

**Operations Domain:**
- warehouse_locations: Distribution centers and warehouses
- suppliers: Parts and equipment suppliers
- parts_inventory: Parts stock levels
- service_orders: Vehicle service/maintenance orders

**Cleanliness Parameter:**
All domain generators accept a `cleanliness` parameter (0-100):
- 100 (default): Pristine data with no NULL injection or messy patterns
- 90-99: Minor imperfections (extended vehicle makes/service types appear)
- 50-89: Moderate messiness (NULL injection in optional fields)
- 0-49: Messy data (higher NULL rates, more variation in notes fields)

The cleanliness parameter NEVER breaks FK integrity - foreign keys always
reference valid IDs. NULL injection is only applied to allowlisted fields.

Usage:
    from velocity_motors import (
        generate_sales_domain,
        generate_crm_domain,
        generate_operations_domain,
        set_random_seed,
    )

    # Set seed for reproducibility
    set_random_seed(42)

    # Generate with cleanliness parameter
    # IMPORTANT: To fix FK circular dependency, generate in this order:
    # 1. Salespersons first (independent)
    # 2. CRM with salesperson_ids
    # 3. Sales with customer_ids from CRM
    # 4. Operations with customer_ids and vehicle_ids

    from velocity_motors.sales import generate_salespersons, generate_vehicles
    from velocity_motors.utils import scale_count

    salespersons = generate_salespersons(n=50, cleanliness=80)
    salesperson_ids = salespersons['salesperson_id'].tolist()

    crm_data = generate_crm_domain(
        scale=1.0,
        cleanliness=80,
        salesperson_ids=salesperson_ids
    )
    customer_ids = crm_data['customers']['customer_id'].tolist()

    sales_data = generate_sales_domain(
        scale=1.0,
        cleanliness=80,
        customer_ids=customer_ids  # Pass valid customer IDs
    )

    ops_data = generate_operations_domain(
        scale=1.0,
        cleanliness=80,
        customer_ids=customer_ids,
        vehicle_ids=sales_data['vehicles']['vehicle_id'].tolist()
    )
"""

from .utils import (
    set_random_seed,
    scale_count,
    inject_nulls,
    get_null_rate,
    calculate_cleanliness_intensity,
    apply_case_inconsistency,
)
from .sales import generate_sales_domain
from .customers import generate_crm_domain
from .operations import generate_operations_domain

__all__ = [
    'set_random_seed',
    'scale_count',
    'inject_nulls',
    'get_null_rate',
    'calculate_cleanliness_intensity',
    'apply_case_inconsistency',
    'generate_sales_domain',
    'generate_crm_domain',
    'generate_operations_domain',
]
