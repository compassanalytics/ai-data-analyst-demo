"""
Velocity Motors Dataset Generator
=================================

A fictional automotive company dataset with 16 tables across 3 domains:

**Sales Domain:**
- territories: Sales territory hierarchy (division > region > territory)
- salespersons: Sales team members with territory and manager hierarchy
- vehicles: Vehicle inventory
- features: Vehicle feature catalog (Safety, Comfort, Technology, etc.)
- vehicle_features: Junction table (many-to-many vehicle-feature mappings)
- price_history: SCD Type 2 price tracking per vehicle
- orders: Customer orders with totals and discounts
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
    # 1. Territories first (independent)
    # 2. Salespersons with territory_ids
    # 3. CRM with salesperson_ids
    # 4. Sales with customer_ids from CRM
    # 5. Operations with customer_ids and vehicle_ids

    from velocity_motors.sales import (
        generate_territories,
        generate_salespersons,
        generate_vehicles,
        generate_features,
        generate_vehicle_features,
        generate_price_history,
    )
    from velocity_motors.utils import scale_count

    territories = generate_territories(cleanliness=80)
    territory_ids = territories['territory_id'].tolist()

    salespersons = generate_salespersons(n=50, cleanliness=80, territory_ids=territory_ids)
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
        customer_ids=customer_ids,  # Pass valid customer IDs
        territory_ids=territory_ids  # Pass valid territory IDs
    )

    ops_data = generate_operations_domain(
        scale=1.0,
        cleanliness=80,
        customer_ids=customer_ids,
        vehicle_ids=sales_data['vehicles']['vehicle_id'].tolist()
    )
"""

from .customers import generate_crm_domain
from .operations import generate_operations_domain
from .sales import (
    add_order_totals,
    generate_features,
    generate_price_history,
    generate_sales_domain,
    generate_territories,
    generate_vehicle_features,
)
from .utils import (
    apply_case_inconsistency,
    calculate_cleanliness_intensity,
    get_null_rate,
    inject_nulls,
    scale_count,
    set_random_seed,
)

__all__ = [
    "set_random_seed",
    "scale_count",
    "inject_nulls",
    "get_null_rate",
    "calculate_cleanliness_intensity",
    "apply_case_inconsistency",
    "generate_sales_domain",
    "generate_crm_domain",
    "generate_operations_domain",
    "generate_territories",
    "generate_features",
    "generate_vehicle_features",
    "generate_price_history",
    "add_order_totals",
]
