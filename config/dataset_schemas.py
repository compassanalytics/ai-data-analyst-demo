"""Dataset schemas with column descriptions for Unity Catalog.

These descriptions are used to add COMMENT metadata to columns,
which enables Genie AI to understand the business meaning of each field.
"""

from typing import Dict

# Type alias for nested column description dictionaries
# Structure: {schema: {table: {column: description}}}
ColumnDescriptions = Dict[str, Dict[str, Dict[str, str]]]


# =============================================================================
# Velocity Motors Dataset Schemas
# =============================================================================
# Source: dataset_generators/data/velocity_motors/README.md

VELOCITY_MOTORS_SCHEMAS: ColumnDescriptions = {
    "sales": {
        "salespersons": {
            "salesperson_id": "Primary key (SP-####)",
            "first_name": "First name",
            "last_name": "Last name",
            "name": "Full name",
            "email": "Email address",
            "hire_date": "Date hired",
            "region": "Sales region (Northeast, Southeast, Midwest, Southwest, West, Pacific Northwest)",
            "quota": "Annual sales quota in USD",
            "commission_rate": "Commission rate (0.015 - 0.04)",
        },
        "vehicles": {
            "vehicle_id": "Primary key (VH-######)",
            "vin": "17-character VIN with valid WMI codes",
            "make": "Vehicle manufacturer (Ford, Toyota, Honda, Chevrolet, BMW, Mercedes-Benz)",
            "model": "Vehicle model",
            "year": "Model year (current year - 4 to current)",
            "trim": "Trim level",
            "color": "Exterior color",
            "msrp": "Manufacturer''s suggested retail price",
            "condition": "New (60%), Certified Pre-Owned (25%), Used (15%)",
            "mileage": "Odometer reading",
            "status": "Available (70%), Reserved (10%), Sold (15%), In Transit (5%)",
        },
        "orders": {
            "order_id": "Primary key (ORD-########)",
            "customer_id": "FK to customers",
            "vehicle_id": "FK to vehicles",
            "salesperson_id": "FK to salespersons",
            "order_date": "Order timestamp",
            "status": "Completed (85%), Pending (5%), Processing (5%), Cancelled (5%)",
            "payment_method": "Financing (55%), Cash (20%), Lease (15%), Trade-In + Financing (10%)",
        },
        "order_items": {
            "order_item_id": "Primary key (OI-##########)",
            "order_id": "FK to orders",
            "item_type": "Vehicle, Accessory, or Service",
            "item_description": "Item name/description",
            "quantity": "Quantity (always 1 for vehicles)",
            "unit_price": "Price per unit",
            "total_price": "Line item total",
        },
    },
    "crm": {
        "customer_segments": {
            "segment_id": "Primary key (SEG-###)",
            "segment_name": "Individual, Fleet, or Dealer",
            "description": "Segment description",
            "discount_tier": "Standard, Volume, or Dealer",
            "credit_limit_default": "Default credit limit",
            "payment_terms_days": "Default payment terms",
        },
        "customers": {
            "customer_id": "Primary key (CUST-#####)",
            "segment_id": "FK to customer_segments",
            "customer_name": "Display name (person or company)",
            "first_name": "Contact first name",
            "last_name": "Contact last name",
            "company_name": "Company name (null for Individual)",
            "email": "Email address",
            "phone": "Phone number",
            "street_address": "Street address",
            "city": "City",
            "state": "State abbreviation",
            "zip_code": "ZIP code",
            "country": "Country (USA)",
            "customer_since": "Account creation date",
            "credit_score": "Credit score (580-850)",
            "lifetime_value": "Customer lifetime value in USD",
            "is_active": "Active status",
        },
        "interactions": {
            "interaction_id": "Primary key (INT-########)",
            "customer_id": "FK to customers",
            "interaction_type": "Phone Call, Email, In-Person Visit, Test Drive, Service Appointment, Website Chat",
            "interaction_date": "Interaction timestamp",
            "duration_minutes": "Duration in minutes",
            "outcome": "Resolved, Follow-up Required, Information Provided, Escalated, No Answer",
            "sentiment": "Positive (40%), Neutral (45%), Negative (15%)",
            "notes": "Interaction notes",
        },
        "leads": {
            "lead_id": "Primary key (LEAD-#######)",
            "customer_id": "FK to customers (null if unconverted)",
            "first_name": "Lead first name",
            "last_name": "Lead last name",
            "email": "Email address",
            "phone": "Phone number",
            "source": "Website (35%), Phone Inquiry (20%), Walk-In (15%), Referral (12%), Social Media (8%), Auto Show (5%), Partner (5%)",
            "status": "Converted, Cold, Contacted, Qualified, Proposal, Lost",
            "interest_level": "High, Medium, Low",
            "vehicle_interest": "Sedan, SUV, Truck, Sports Car, Luxury, Electric, Hybrid",
            "salesperson_id": "FK to salespersons",
            "created_date": "Lead creation date",
            "last_contact_date": "Last contact timestamp",
            "converted_date": "Conversion date (null if unconverted)",
            "is_converted": "Conversion flag",
        },
    },
    "operations": {
        "warehouse_locations": {
            "warehouse_id": "Primary key (WH-###)",
            "warehouse_name": "Facility name",
            "warehouse_type": "Distribution Center (30%), Regional Warehouse (40%), Parts Depot (30%)",
            "street_address": "Street address",
            "city": "City",
            "state": "State abbreviation",
            "zip_code": "ZIP code",
            "capacity_sqft": "Capacity in square feet",
            "current_utilization": "Current utilization (0.60 - 0.95)",
            "manager_name": "Facility manager name",
            "phone": "Contact phone",
            "is_active": "Active status",
        },
        "suppliers": {
            "supplier_id": "Primary key (SUP-####)",
            "supplier_name": "Company name",
            "supplier_type": "OEM (20%), Aftermarket (40%), Specialty (20%), Wholesale (20%)",
            "primary_category": "Primary part category (ENG, BRK, ELE, BOD, SUS, TRN)",
            "contact_name": "Primary contact name",
            "contact_email": "Contact email",
            "contact_phone": "Contact phone",
            "street_address": "Street address",
            "city": "City",
            "state": "State abbreviation",
            "zip_code": "ZIP code",
            "country": "Country",
            "rating": "Supplier rating (3.0 - 5.0)",
            "lead_time_days": "Average lead time in days",
            "contract_start_date": "Contract start date",
            "payment_terms_days": "Payment terms",
            "is_active": "Active status",
        },
        "parts_inventory": {
            "part_id": "Primary key (PART-######)",
            "part_number": "Part number (CAT-####[A-C])",
            "part_name": "Part description",
            "category": "Category code (ENG, BRK, ELE, BOD, SUS, TRN)",
            "supplier_id": "FK to suppliers",
            "warehouse_id": "FK to warehouse_locations",
            "quantity_on_hand": "Current stock quantity",
            "reorder_point": "Reorder threshold",
            "unit_cost": "Cost per unit",
            "popularity_tier": "High Demand (20%), Standard (50%), Low Demand (20%), Rare (10%)",
            "status": "In Stock, Below Reorder, Critical Low, Out of Stock",
            "last_restocked_date": "Last restock date",
        },
        "service_orders": {
            "service_order_id": "Primary key (SVC-########)",
            "customer_id": "FK to customers",
            "vehicle_id": "FK to vehicles",
            "service_type": "Oil Change, Tire Rotation, Brake Service, Transmission Service, Engine Repair, AC Service, Battery Replacement, Alignment, Inspection, Recall Service",
            "service_date": "Service timestamp",
            "status": "Completed (80%), In Progress (10%), Scheduled (5%), Waiting for Parts (3%), Cancelled (2%)",
            "labor_cost": "Labor cost",
            "parts_cost": "Parts cost",
            "total_cost": "Total cost (labor + parts)",
            "duration_minutes": "Service duration",
            "technician_name": "Technician name",
            "mileage_at_service": "Odometer reading",
            "customer_rating": "Customer rating 1-5 (null if not rated)",
            "notes": "Service notes",
        },
    },
}


# =============================================================================
# Star Schema Dataset Descriptions
# =============================================================================
# Source: dataset_generators/star_schema_generator.py

STAR_SCHEMA_DESCRIPTIONS: ColumnDescriptions = {
    "default": {
        "dim_date": {
            "date_key": "Primary key (YYYYMMDD integer format)",
            "full_date": "Full calendar date",
            "year": "Calendar year",
            "month": "Month number (1-12)",
            "month_name": "Full month name",
            "day_of_month": "Day of the month (1-31)",
            "day_of_week": "Day of week (1=Monday, 7=Sunday)",
            "day_name": "Full day name (Monday, Tuesday, etc.)",
            "week_of_year": "ISO week number",
            "quarter": "Calendar quarter (1-4)",
            "fiscal_year": "Fiscal year (starts February 1)",
            "fiscal_quarter": "Fiscal quarter (1-4)",
            "fiscal_quarter_name": "Fiscal quarter display name (FY2024 Q1)",
            "is_weekend": "True if Saturday or Sunday",
            "is_holiday": "True if major holiday",
        },
        "dim_product": {
            "product_key": "Primary key (surrogate)",
            "product_sku": "Product SKU code",
            "product_name": "Full product name",
            "brand": "Brand name",
            "category": "Product category (Beer, Cider, Ready-to-Drink, Non-Alcoholic)",
            "subcategory": "Product subcategory",
            "pack_size": "Pack configuration (Single, 6-Pack, 12-Pack, 24-Pack, Keg)",
            "container_type": "Container type (Can, Bottle, Draft)",
            "unit_volume_ml": "Volume per unit in milliliters",
            "units_per_pack": "Number of units per pack",
            "alcohol_percentage": "ABV percentage (0.0 for non-alcoholic)",
            "unit_cost": "Cost per unit",
            "unit_price": "Selling price per unit",
            "is_seasonal": "True if seasonal product",
            "launch_date": "Product launch date",
            "is_active": "True if currently active",
        },
        "dim_customer": {
            "customer_key": "Primary key (surrogate)",
            "customer_id": "Business customer ID",
            "customer_name": "Customer display name",
            "customer_type": "Type of business (Bar/Restaurant, Liquor Store, Grocery, etc.)",
            "segment": "Customer segment (Enterprise, Mid-Market, Small Business, Independent)",
            "channel": "Sales channel (On-Premise, Off-Premise, E-Commerce)",
            "city": "Customer city",
            "region": "Geographic region (Northeast, Southeast, Midwest, Southwest, West)",
            "credit_limit": "Credit limit in USD",
            "payment_terms_days": "Payment terms in days",
            "account_manager": "Assigned account manager",
            "customer_since": "Customer relationship start date",
            "is_active": "True if active customer",
        },
        "dim_store": {
            "store_key": "Primary key (surrogate)",
            "store_code": "Store/facility code",
            "store_name": "Facility name",
            "store_type": "Facility type (Distribution Center, Regional Warehouse, Local Depot)",
            "state": "State abbreviation",
            "square_footage": "Facility size in square feet",
            "max_capacity_pallets": "Maximum pallet capacity",
            "has_cold_storage": "True if facility has cold storage",
            "open_date": "Facility opening date",
        },
        "dim_promotion": {
            "promotion_key": "Primary key (surrogate)",
            "promotion_code": "Promotion code",
            "promotion_name": "Promotion display name",
            "promotion_type": "Type (Price Discount, BOGO, Bundle Deal, Loyalty Reward, Seasonal Special)",
            "discount_percentage": "Discount percentage (5-30%)",
            "start_date": "Promotion start date",
            "end_date": "Promotion end date",
            "minimum_quantity": "Minimum quantity to qualify",
            "is_stackable": "True if can combine with other promotions",
        },
        "fact_sales": {
            "sale_key": "Primary key (surrogate)",
            "date_key": "FK to dim_date",
            "product_key": "FK to dim_product",
            "customer_key": "FK to dim_customer",
            "store_key": "FK to dim_store",
            "promotion_key": "FK to dim_promotion (null if no promotion)",
            "quantity_sold": "Number of packs sold",
            "unit_price": "Price per unit at time of sale",
            "gross_amount": "Gross sale amount before discount",
            "discount_amount": "Discount amount applied",
            "net_amount": "Net sale amount after discount",
            "cost_amount": "Cost of goods sold",
            "profit_amount": "Profit (net_amount - cost_amount)",
            "units_sold": "Total individual units sold",
        },
    },
}


# =============================================================================
# Super Table (Anti-Pattern Example)
# =============================================================================
# Note: The super table intentionally has confusing column names
# We provide minimal descriptions to highlight the anti-patterns

SUPER_TABLE_DESCRIPTIONS: ColumnDescriptions = {
    "default": {
        "super_table": {
            # Intentionally sparse - this is the anti-pattern demo
            "txn_id": "Transaction ID (one of several duplicate ID columns)",
            "sale_date": "Sale date (one of multiple date format columns)",
            "net_amt": "Net amount (one of 7 revenue-related columns)",
            "qty": "Quantity (one of 5 quantity columns)",
        },
    },
}


# =============================================================================
# Dataset Configurations
# =============================================================================

DATASET_CONFIGS = {
    "velocity_motors": {
        "schemas": VELOCITY_MOTORS_SCHEMAS,
        "description": "Automotive dealership with 12 tables across Sales, CRM, and Operations domains. Realistic relationships and seasonal patterns.",
        "base_url": "https://compassagentemofiles.blob.core.windows.net/datasets/velocity_motors",
        "tables": {
            "sales": ["salespersons", "vehicles", "orders", "order_items"],
            "crm": ["customer_segments", "customers", "interactions", "leads"],
            "operations": ["warehouse_locations", "suppliers", "parts_inventory", "service_orders"],
        },
    },
    "star_schema": {
        "schemas": STAR_SCHEMA_DESCRIPTIONS,
        "description": "Clean dimensional model for CPG/Beverage company. 6 tables demonstrating proper star schema design.",
        "base_url": "https://compassagentemofiles.blob.core.windows.net/datasets/star_schema",
        "tables": {
            "default": ["dim_date", "dim_product", "dim_customer", "dim_store", "dim_promotion", "fact_sales"],
        },
    },
    "super_table": {
        "schemas": SUPER_TABLE_DESCRIPTIONS,
        "description": "Messy denormalized table demonstrating anti-patterns. 139 columns with cryptic names, duplicate data, and inconsistent formats.",
        "base_url": "https://compassagentemofiles.blob.core.windows.net/datasets/super_table",
        "tables": {
            "default": ["super_table"],
        },
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_column_descriptions(dataset: str, schema: str, table: str) -> Dict[str, str]:
    """Get column descriptions for a specific table.

    Args:
        dataset: Dataset name (velocity_motors, star_schema, super_table)
        schema: Schema name within the dataset
        table: Table name

    Returns:
        Dictionary mapping column names to descriptions

    Raises:
        KeyError: If dataset, schema, or table not found
    """
    config = DATASET_CONFIGS.get(dataset)
    if not config:
        raise KeyError(f"Unknown dataset: {dataset}. Available: {list(DATASET_CONFIGS.keys())}")

    schemas = config["schemas"]
    if schema not in schemas:
        raise KeyError(f"Unknown schema: {schema}. Available: {list(schemas.keys())}")

    tables = schemas[schema]
    if table not in tables:
        raise KeyError(f"Unknown table: {table}. Available: {list(tables.keys())}")

    return tables[table]


def get_table_list(dataset: str) -> Dict[str, list]:
    """Get all tables for a dataset organized by schema.

    Args:
        dataset: Dataset name

    Returns:
        Dictionary mapping schema names to list of table names
    """
    config = DATASET_CONFIGS.get(dataset)
    if not config:
        raise KeyError(f"Unknown dataset: {dataset}")

    return config["tables"]


def get_base_url(dataset: str) -> str:
    """Get the Azure Blob Storage base URL for a dataset.

    Args:
        dataset: Dataset name

    Returns:
        Base URL for the dataset files
    """
    config = DATASET_CONFIGS.get(dataset)
    if not config:
        raise KeyError(f"Unknown dataset: {dataset}")

    return config["base_url"]


def list_datasets() -> Dict[str, str]:
    """List all available datasets with descriptions.

    Returns:
        Dictionary mapping dataset names to descriptions
    """
    return {name: config["description"] for name, config in DATASET_CONFIGS.items()}
