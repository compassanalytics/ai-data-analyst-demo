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

Usage:
    from velocity_motors import (
        generate_sales_domain,
        generate_crm_domain,
        generate_operations_domain,
        set_random_seed,
    )

    # Set seed for reproducibility
    set_random_seed(42)

    # Generate each domain
    sales_data = generate_sales_domain(scale=1.0)
    crm_data = generate_crm_domain(
        scale=1.0,
        salesperson_ids=sales_data['salespersons']['salesperson_id'].tolist()
    )
    ops_data = generate_operations_domain(
        scale=1.0,
        customer_ids=crm_data['customers']['customer_id'].tolist(),
        vehicle_ids=sales_data['vehicles']['vehicle_id'].tolist()
    )
"""

from .utils import set_random_seed
from .sales import generate_sales_domain
from .customers import generate_crm_domain
from .operations import generate_operations_domain

__all__ = [
    'set_random_seed',
    'generate_sales_domain',
    'generate_crm_domain',
    'generate_operations_domain',
]
