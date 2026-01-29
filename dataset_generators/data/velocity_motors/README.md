# Velocity Motors Dataset

A fictional automotive company dataset designed for AI/BI demonstrations, featuring 16 tables across 3 domains with realistic data distributions and relationships.

## Overview

**Company Context:** Velocity Motors is a multi-brand automotive dealership network with nationwide operations. They sell new and used vehicles from major manufacturers, provide maintenance services, and manage complex B2B relationships with fleet customers and dealers.

**Dataset Characteristics:**
- 16 tables across 3 domains (Sales, CRM, Operations)
- Realistic foreign key relationships
- Seasonal sales patterns (Q4 spike of 1.2x baseline)
- Customer segment distribution (70% Individual, 20% Fleet, 10% Dealer)
- Lead conversion rate of ~20%
- Reproducible via random seed

## Domain Structure

```
velocity_motors/
├── Sales Domain
│   ├── territories       # Sales territory hierarchy
│   ├── salespersons      # Sales team members
│   ├── vehicles          # Vehicle inventory
│   ├── features          # Vehicle feature catalog
│   ├── vehicle_features  # Vehicle-feature mappings
│   ├── price_history     # SCD Type 2 price tracking
│   ├── orders            # Customer orders
│   └── order_items       # Line items per order
├── CRM Domain
│   ├── customer_segments # Segment definitions
│   ├── customers         # Customer master data
│   ├── interactions      # Interaction history
│   └── leads             # Sales leads
└── Operations Domain
    ├── warehouse_locations # Distribution centers
    ├── suppliers           # Parts suppliers
    ├── parts_inventory     # Parts stock
    └── service_orders      # Service/maintenance
```

---

## Sales Domain

### salespersons

Sales team members with quotas and commission rates.

| Column | Type | Description |
|--------|------|-------------|
| salesperson_id | string | Primary key (SP-####) |
| first_name | string | First name |
| last_name | string | Last name |
| name | string | Full name |
| email | string | Email address |
| hire_date | date | Date hired |
| region | string | Sales region (Northeast, Southeast, Midwest, Southwest, West, Pacific Northwest) |
| quota | integer | Annual sales quota in USD |
| commission_rate | decimal | Commission rate (0.015 - 0.04) |

**Notes:**
- Seniority correlates with higher quota and commission rate
- ~50 salespersons at full scale

---

### vehicles

Vehicle inventory with status tracking.

| Column | Type | Description |
|--------|------|-------------|
| vehicle_id | string | Primary key (VH-######) |
| vin | string | 17-character VIN with valid WMI codes |
| make | string | Vehicle manufacturer (Ford, Toyota, Honda, Chevrolet, BMW, Mercedes-Benz) |
| model | string | Vehicle model |
| year | integer | Model year (current year - 4 to current) |
| trim | string | Trim level |
| color | string | Exterior color |
| msrp | integer | Manufacturer's suggested retail price |
| condition | string | New (60%), Certified Pre-Owned (25%), Used (15%) |
| mileage | integer | Odometer reading |
| status | string | Available (70%), Reserved (10%), Sold (15%), In Transit (5%) |

**Notes:**
- VINs use valid WMI codes: 1FA (Ford), 2T1 (Toyota), 1HG (Honda), 3GN (Chevrolet), WBA (BMW), WDD (Mercedes-Benz)
- MSRP adjusted based on condition and mileage
- ~5,000 vehicles at full scale

---

### orders

Customer vehicle orders with seasonal distribution.

| Column | Type | Description |
|--------|------|-------------|
| order_id | string | Primary key (ORD-########) |
| customer_id | string | FK to customers |
| vehicle_id | string | FK to vehicles |
| salesperson_id | string | FK to salespersons |
| order_date | datetime | Order timestamp |
| status | string | Completed (85%), Pending (5%), Processing (5%), Cancelled (5%) |
| payment_method | string | Financing (55%), Cash (20%), Lease (15%), Trade-In + Financing (10%) |

**Notes:**
- Dates have seasonal weighting: Nov-Dec = 1.2x baseline (Q4 spike)
- Orders span 2 years of history
- ~100,000 orders at full scale

---

### order_items

Line items for each order (vehicle + accessories + services).

| Column | Type | Description |
|--------|------|-------------|
| order_item_id | string | Primary key (OI-##########) |
| order_id | string | FK to orders |
| item_type | string | Vehicle, Accessory, or Service |
| item_description | string | Item name/description |
| quantity | integer | Quantity (always 1 for vehicles) |
| unit_price | decimal | Price per unit |
| total_price | decimal | Line item total |

**Notes:**
- Each order has 1 vehicle (required)
- 0-3 accessories (extended warranty, floor mats, roof rack, etc.)
- 0-2 services (registration, documentation fee, delivery, etc.)

---

### territories

Sales territory hierarchy (division > region > territory).

| Column | Type | Description |
|--------|------|-------------|
| territory_id | string | Primary key (TER-###) |
| territory_name | string | Territory name (e.g., Northeast North, Southeast South) |
| region_name | string | Region name (Northeast, Southeast, Midwest, Southwest, West, Pacific Northwest) |
| division_name | string | Division name (East, Central, West) |
| is_active | boolean | Active status |

**Notes:**
- 3 divisions, 3 regions per division, 2 territories per region = ~18 territories
- 95% of territories are active
- Used for salesperson assignment and regional reporting

---

### features

Vehicle feature catalog (dimension table).

| Column | Type | Description |
|--------|------|-------------|
| feature_id | string | Primary key (FEAT-###) |
| feature_name | string | Feature name (e.g., Heated Seats, Navigation System) |
| feature_category | string | Category (Safety, Comfort, Technology, Performance, Appearance) |
| description | string | Feature description |

**Notes:**
- ~35 features across 5 categories
- Used with vehicle_features junction table for many-to-many relationship
- Examples: Heated Seats (Comfort), Lane Departure Warning (Safety), Turbocharger (Performance)

---

### vehicle_features

Junction table linking vehicles to features (many-to-many).

| Column | Type | Description |
|--------|------|-------------|
| vehicle_feature_id | string | Primary key (VF-########) |
| vehicle_id | string | FK to vehicles |
| feature_id | string | FK to features |
| is_standard | boolean | Whether feature comes standard (60%) or optional (40%) |

**Notes:**
- Each vehicle has 3-10 features
- Premium trims (Limited, Platinum, etc.) get more features (6-10)
- Base trims get fewer features (3-7)
- Enables queries like "vehicles with heated seats and navigation"

---

### price_history

SCD Type 2 price tracking for vehicles (temporal data).

| Column | Type | Description |
|--------|------|-------------|
| price_history_id | string | Primary key (PH-########) |
| vehicle_id | string | FK to vehicles |
| price | decimal | Price at this time |
| effective_date | date | Date this price became effective |
| end_date | date | Date this price was superseded (null if current) |
| is_current | boolean | Whether this is the current price record |
| change_reason | string | Reason for price change (Market Adjustment, Promotion, Model Year Change, Inventory Reduction, Demand Increase) |

**Notes:**
- Each vehicle has 1-5 price records (weighted toward 1-2)
- Only the latest record has is_current=True and end_date=null
- Price changes range from -15% to +5% from previous
- Enables point-in-time queries and price trend analysis

---

## CRM Domain

### customer_segments

Fixed customer segment dimension.

| Column | Type | Description |
|--------|------|-------------|
| segment_id | string | Primary key (SEG-###) |
| segment_name | string | Individual, Fleet, or Dealer |
| description | string | Segment description |
| discount_tier | string | Standard, Volume, or Dealer |
| credit_limit_default | integer | Default credit limit |
| payment_terms_days | integer | Default payment terms |

**Notes:**
- Fixed 3 rows (Individual, Fleet, Dealer)

---

### customers

Customer master data with segment assignment.

| Column | Type | Description |
|--------|------|-------------|
| customer_id | string | Primary key (CUST-#####) |
| segment_id | string | FK to customer_segments |
| customer_name | string | Display name (person or company) |
| first_name | string | Contact first name |
| last_name | string | Contact last name |
| company_name | string | Company name (null for Individual) |
| email | string | Email address |
| phone | string | Phone number |
| street_address | string | Street address |
| city | string | City |
| state | string | State abbreviation |
| zip_code | string | ZIP code |
| country | string | Country (USA) |
| customer_since | date | Account creation date |
| credit_score | integer | Credit score (580-850) |
| lifetime_value | integer | Customer lifetime value in USD |
| is_active | boolean | Active status |

**Notes:**
- Segment distribution: Individual 70%, Fleet 20%, Dealer 10%
- LTV correlated with segment and tenure
- ~50,000 customers at full scale

---

### interactions

Customer interaction history with sentiment tracking.

| Column | Type | Description |
|--------|------|-------------|
| interaction_id | string | Primary key (INT-########) |
| customer_id | string | FK to customers |
| interaction_type | string | Phone Call, Email, In-Person Visit, Test Drive, Service Appointment, Website Chat |
| interaction_date | datetime | Interaction timestamp |
| duration_minutes | integer | Duration in minutes |
| outcome | string | Resolved, Follow-up Required, Information Provided, Escalated, No Answer |
| sentiment | string | Positive (40%), Neutral (45%), Negative (15%) |
| notes | string | Interaction notes (null placeholder) |

**Notes:**
- Number of interactions correlated with customer LTV
- High-LTV customers have 10-50 interactions
- Low-LTV customers have 1-5 interactions

---

### leads

Sales leads including unconverted prospects.

| Column | Type | Description |
|--------|------|-------------|
| lead_id | string | Primary key (LEAD-#######) |
| customer_id | string | FK to customers (null if unconverted) |
| first_name | string | Lead first name |
| last_name | string | Lead last name |
| email | string | Email address |
| phone | string | Phone number |
| source | string | Website (35%), Phone Inquiry (20%), Walk-In (15%), Referral (12%), Social Media (8%), Auto Show (5%), Partner (5%) |
| status | string | Converted, Cold, Contacted, Qualified, Proposal, Lost |
| interest_level | string | High, Medium, Low |
| vehicle_interest | string | Sedan, SUV, Truck, Sports Car, Luxury, Electric, Hybrid |
| salesperson_id | string | FK to salespersons |
| created_date | datetime | Lead creation date |
| last_contact_date | datetime | Last contact timestamp |
| converted_date | datetime | Conversion date (null if unconverted) |
| is_converted | boolean | Conversion flag |

**Notes:**
- ~20% conversion rate
- Converted leads link to customer records

---

## Operations Domain

### warehouse_locations

Distribution centers and warehouse facilities.

| Column | Type | Description |
|--------|------|-------------|
| warehouse_id | string | Primary key (WH-###) |
| warehouse_name | string | Facility name |
| warehouse_type | string | Distribution Center (30%), Regional Warehouse (40%), Parts Depot (30%) |
| street_address | string | Street address |
| city | string | City |
| state | string | State abbreviation |
| zip_code | string | ZIP code |
| capacity_sqft | integer | Capacity in square feet |
| current_utilization | decimal | Current utilization (0.60 - 0.95) |
| manager_name | string | Facility manager name |
| phone | string | Contact phone |
| is_active | boolean | Active status |

**Notes:**
- Capacity varies by type: Distribution Center (50k-100k sqft), Regional (20k-50k), Depot (5k-20k)
- ~10 warehouses at full scale

---

### suppliers

Parts and equipment suppliers.

| Column | Type | Description |
|--------|------|-------------|
| supplier_id | string | Primary key (SUP-####) |
| supplier_name | string | Company name |
| supplier_type | string | OEM (20%), Aftermarket (40%), Specialty (20%), Wholesale (20%) |
| primary_category | string | Primary part category (ENG, BRK, ELE, BOD, SUS, TRN) |
| contact_name | string | Primary contact name |
| contact_email | string | Contact email |
| contact_phone | string | Contact phone |
| street_address | string | Street address |
| city | string | City |
| state | string | State abbreviation |
| zip_code | string | ZIP code |
| country | string | Country |
| rating | decimal | Supplier rating (3.0 - 5.0) |
| lead_time_days | integer | Average lead time in days |
| contract_start_date | date | Contract start date |
| payment_terms_days | integer | Payment terms |
| is_active | boolean | Active status |

**Notes:**
- Lead times vary by type: OEM (7-21 days), Wholesale (1-7 days)
- ~50 suppliers at full scale

---

### parts_inventory

Parts stock with popularity-based inventory levels.

| Column | Type | Description |
|--------|------|-------------|
| part_id | string | Primary key (PART-######) |
| part_number | string | Part number (CAT-####[A-C]) |
| part_name | string | Part description |
| category | string | Category code (ENG, BRK, ELE, BOD, SUS, TRN) |
| supplier_id | string | FK to suppliers |
| warehouse_id | string | FK to warehouse_locations |
| quantity_on_hand | integer | Current stock quantity |
| reorder_point | integer | Reorder threshold |
| unit_cost | decimal | Cost per unit |
| popularity_tier | string | High Demand (20%), Standard (50%), Low Demand (20%), Rare (10%) |
| status | string | In Stock, Below Reorder, Critical Low, Out of Stock |
| last_restocked_date | date | Last restock date |

**Notes:**
- Part number format: CAT-####[A-C] where CAT is category prefix
- Categories: ENG (Engine), BRK (Brake), ELE (Electrical), BOD (Body), SUS (Suspension), TRN (Transmission)
- Stock levels inversely correlated with popularity
- ~2,000 parts at full scale

---

### service_orders

Vehicle service and maintenance orders.

| Column | Type | Description |
|--------|------|-------------|
| service_order_id | string | Primary key (SVC-########) |
| customer_id | string | FK to customers |
| vehicle_id | string | FK to vehicles |
| service_type | string | Oil Change, Tire Rotation, Brake Service, Transmission Service, Engine Repair, AC Service, Battery Replacement, Alignment, Inspection, Recall Service |
| service_date | datetime | Service timestamp |
| status | string | Completed (80%), In Progress (10%), Scheduled (5%), Waiting for Parts (3%), Cancelled (2%) |
| labor_cost | decimal | Labor cost |
| parts_cost | decimal | Parts cost |
| total_cost | decimal | Total cost (labor + parts) |
| duration_minutes | integer | Service duration |
| technician_name | string | Technician name |
| mileage_at_service | integer | Odometer reading |
| customer_rating | integer | Customer rating 1-5 (null if not rated) |
| notes | string | Service notes (null placeholder) |

**Notes:**
- Service frequency correlated with vehicle age
- ~60% of completed orders have ratings
- ~30,000 service orders at full scale

---

## Data Generation

### Regenerate Dataset

```bash
# Full dataset (default)
uv run python dataset_generators/generate_velocity_motors.py

# 10% scale for testing
uv run python dataset_generators/generate_velocity_motors.py --scale 0.1 --seed 42

# Specific domain only
uv run python dataset_generators/generate_velocity_motors.py --domain sales

# Preview without writing
uv run python dataset_generators/generate_velocity_motors.py --dry-run
```

### Scale Reference

| Scale | Customers | Vehicles | Orders | Service Orders |
|-------|-----------|----------|--------|----------------|
| 0.1   | 5,000     | 500      | 10,000 | 3,000          |
| 0.5   | 25,000    | 2,500    | 50,000 | 15,000         |
| 1.0   | 50,000    | 5,000    | 100,000| 30,000         |

---

## Unity Catalog Loading

### Create Schema

```sql
CREATE CATALOG IF NOT EXISTS velocity_motors;
CREATE SCHEMA IF NOT EXISTS velocity_motors.bronze;
```

### Load Tables

Upload parquet files via Databricks UI or use:

```python
# Example: Load from cloud storage
spark.read.parquet("abfss://container@storage.dfs.core.windows.net/velocity_motors/customers.parquet") \
    .write.mode("overwrite") \
    .saveAsTable("velocity_motors.bronze.customers")
```

### Add Table Comments

```sql
COMMENT ON TABLE velocity_motors.bronze.customers IS
    'Customer master data with segment assignment. 70% Individual, 20% Fleet, 10% Dealer.';

COMMENT ON TABLE velocity_motors.bronze.orders IS
    'Vehicle orders with seasonal Q4 spike (Nov-Dec = 1.2x baseline).';
```

---

## Sample Queries

### Sales Performance

```sql
-- Monthly sales by salesperson
SELECT
    s.name as salesperson,
    s.region,
    DATE_TRUNC('month', o.order_date) as month,
    COUNT(*) as orders,
    SUM(oi.total_price) as revenue
FROM orders o
JOIN salespersons s ON o.salesperson_id = s.salesperson_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE oi.item_type = 'Vehicle'
GROUP BY 1, 2, 3
ORDER BY month, revenue DESC;
```

### Customer Segments

```sql
-- Segment analysis with LTV
SELECT
    cs.segment_name,
    COUNT(*) as customer_count,
    AVG(c.lifetime_value) as avg_ltv,
    SUM(c.lifetime_value) as total_ltv
FROM customers c
JOIN customer_segments cs ON c.segment_id = cs.segment_id
GROUP BY cs.segment_name;
```

### Lead Conversion

```sql
-- Lead source effectiveness
SELECT
    source,
    COUNT(*) as total_leads,
    SUM(CASE WHEN is_converted THEN 1 ELSE 0 END) as converted,
    ROUND(100.0 * SUM(CASE WHEN is_converted THEN 1 ELSE 0 END) / COUNT(*), 1) as conversion_rate
FROM leads
GROUP BY source
ORDER BY conversion_rate DESC;
```

### Service Analysis

```sql
-- Service revenue by type
SELECT
    service_type,
    COUNT(*) as orders,
    AVG(total_cost) as avg_cost,
    SUM(total_cost) as total_revenue
FROM service_orders
WHERE status = 'Completed'
GROUP BY service_type
ORDER BY total_revenue DESC;
```
