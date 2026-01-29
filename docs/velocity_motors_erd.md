# Velocity Motors - Entity Relationship Diagram

This document provides a comprehensive ERD showing all tables in the Velocity Motors dataset, including proposed new tables and columns for advanced relationship patterns.

## Entity Relationship Diagram

```mermaid
erDiagram
    %% ============================================
    %% SALES DOMAIN
    %% ============================================

    territories {
        string territory_id PK "PROPOSED"
        string territory_name
        string region_name
        string division_name
        boolean is_active
    }

    salespersons {
        string salesperson_id PK
        string first_name
        string last_name
        string name
        string email
        date hire_date
        string region "DEPRECATED - use territories"
        int quota
        decimal commission_rate
        string territory_id FK "PROPOSED"
        string manager_id FK "PROPOSED - self-ref"
    }

    vehicles {
        string vehicle_id PK
        string vin UK
        string make
        string model
        int year
        string trim
        string color
        decimal msrp
        string condition
        int mileage
        string status
    }

    features {
        string feature_id PK "PROPOSED"
        string feature_name
        string feature_category
        string description
    }

    vehicle_features {
        string vehicle_feature_id PK "PROPOSED"
        string vehicle_id FK "PROPOSED"
        string feature_id FK "PROPOSED"
        boolean is_standard
    }

    orders {
        string order_id PK
        string customer_id FK
        string vehicle_id FK
        string salesperson_id FK
        date order_date
        string status
        string payment_method
        decimal order_total "PROPOSED - denormalized"
        decimal discount_amount "PROPOSED"
    }

    order_items {
        string order_item_id PK
        string order_id FK
        string item_type
        string item_description
        int quantity
        decimal unit_price
        decimal total_price
    }

    price_history {
        string price_history_id PK "PROPOSED"
        string vehicle_id FK "PROPOSED"
        decimal price
        date effective_date
        date end_date
        boolean is_current
        string change_reason
    }

    %% ============================================
    %% CRM DOMAIN
    %% ============================================

    customer_segments {
        string segment_id PK
        string segment_name
        string description
        string discount_tier
        int credit_limit_default
        int payment_terms_days
    }

    customers {
        string customer_id PK
        string segment_id FK
        string customer_name
        string first_name
        string last_name
        string company_name
        string email
        string phone
        string street_address
        string city
        string state
        string zip_code
        string country
        date customer_since
        int credit_score
        decimal lifetime_value
        boolean is_active
    }

    interactions {
        string interaction_id PK
        string customer_id FK
        string interaction_type
        datetime interaction_date
        int duration_minutes
        string outcome
        string sentiment
        string notes
    }

    leads {
        string lead_id PK
        string customer_id FK
        string first_name
        string last_name
        string email
        string phone
        string source
        string status
        string interest_level
        string vehicle_interest
        string salesperson_id FK
        date created_date
        date last_contact_date
        date converted_date
        boolean is_converted
    }

    %% ============================================
    %% OPERATIONS DOMAIN
    %% ============================================

    warehouse_locations {
        string warehouse_id PK
        string warehouse_name
        string warehouse_type
        string street_address
        string city
        string state
        string zip_code
        int capacity_sqft
        decimal current_utilization
        string manager_name
        string phone
        boolean is_active
    }

    suppliers {
        string supplier_id PK
        string supplier_name
        string supplier_type
        string primary_category
        string contact_name
        string contact_email
        string contact_phone
        string street_address
        string city
        string state
        string zip_code
        string country
        decimal rating
        int lead_time_days
        date contract_start_date
        int payment_terms_days
        boolean is_active
    }

    parts_inventory {
        string part_id PK
        string part_number UK
        string part_name
        string category
        string supplier_id FK
        string warehouse_id FK
        int quantity_on_hand
        int reorder_point
        decimal unit_cost
        string popularity_tier
        string status
        date last_restocked_date
    }

    service_orders {
        string service_order_id PK
        string customer_id FK
        string vehicle_id FK
        string service_type
        datetime service_date
        string status
        decimal labor_cost
        decimal parts_cost
        decimal total_cost
        int duration_minutes
        string technician_name
        int mileage_at_service
        int customer_rating
        string notes
    }

    %% ============================================
    %% RELATIONSHIPS
    %% ============================================

    %% Sales Domain Relationships
    territories ||--o{ salespersons : "has"
    salespersons ||--o{ salespersons : "manages (self-ref)"
    salespersons ||--o{ orders : "processes"
    salespersons ||--o{ leads : "assigned"
    vehicles ||--o{ orders : "sold_in"
    vehicles ||--o{ order_items : "referenced_in"
    vehicles ||--o{ price_history : "has_pricing"
    vehicles ||--o{ vehicle_features : "has"
    features ||--o{ vehicle_features : "applied_to"
    orders ||--o{ order_items : "contains"

    %% CRM Domain Relationships
    customer_segments ||--o{ customers : "categorizes"
    customers ||--o{ orders : "places"
    customers ||--o{ interactions : "has"
    customers ||--o{ leads : "converted_from"
    customers ||--o{ service_orders : "requests"

    %% Operations Domain Relationships
    warehouse_locations ||--o{ parts_inventory : "stores"
    suppliers ||--o{ parts_inventory : "supplies"
    vehicles ||--o{ service_orders : "serviced_in"
```

## Table Summary

### Existing Tables (12)

| Domain | Table | Description | Approx Records |
|--------|-------|-------------|----------------|
| Sales | `salespersons` | Sales team members with quotas | ~50 |
| Sales | `vehicles` | Vehicle inventory | ~5,000 |
| Sales | `orders` | Customer vehicle orders | ~100,000 |
| Sales | `order_items` | Line items per order | ~150,000 |
| CRM | `customer_segments` | Segment definitions | 3 |
| CRM | `customers` | Customer master data | ~50,000 |
| CRM | `interactions` | Customer interaction history | ~500,000 |
| CRM | `leads` | Sales leads | ~60,000 |
| Operations | `warehouse_locations` | Distribution centers | ~10 |
| Operations | `suppliers` | Parts suppliers | ~50 |
| Operations | `parts_inventory` | Parts stock levels | ~2,000 |
| Operations | `service_orders` | Service/maintenance orders | ~30,000 |

### Proposed New Tables (4)

| Domain | Table | Pattern | Description |
|--------|-------|---------|-------------|
| Sales | `territories` | **Hierarchy** | Geographic hierarchy: Division > Region > Territory |
| Sales | `features` | **Many-to-Many** | Vehicle features/options catalog |
| Sales | `vehicle_features` | **Many-to-Many** | Junction table linking vehicles to features |
| Sales | `price_history` | **SCD Type 2** | Historical vehicle pricing with effective dates |

### Proposed Column Additions

| Table | Column | Pattern | Description |
|-------|--------|---------|-------------|
| `salespersons` | `territory_id` | **Hierarchy** | FK to territories table |
| `salespersons` | `manager_id` | **Self-Referential** | FK to salespersons (self) |
| `orders` | `order_total` | **Denormalized Aggregate** | Pre-computed order total |
| `orders` | `discount_amount` | **Denormalized** | Applied discount amount |

## Pattern Descriptions

### 1. Hierarchy Pattern (Territories)

The `territories` table implements a geographic hierarchy with three levels:
- **Division**: Highest level (e.g., "East", "West", "Central")
- **Region**: Mid-level (e.g., "Northeast", "Southeast", "Midwest")
- **Territory**: Lowest level, individual sales territories

This enables:
- ROLLUP aggregations from territory to region to division
- Flexible geographic reporting at any level
- Deprecates the flat `salespersons.region` column

### 2. Many-to-Many Pattern (Vehicle Features)

The `features` and `vehicle_features` tables implement a classic M2M relationship:
- **features**: Master list of all available vehicle features/options
- **vehicle_features**: Junction table with `is_standard` flag

Use cases:
- Find vehicles with specific feature combinations (AND/OR logic)
- Analyze feature popularity across vehicle types
- Support complex feature filtering in queries

### 3. Self-Referential Pattern (Manager Hierarchy)

The `salespersons.manager_id` column creates an organizational hierarchy:
- Each salesperson can have one manager (who is also a salesperson)
- Enables recursive CTEs for org chart traversal
- Supports multi-level management reporting

### 4. SCD Type 2 Pattern (Price History)

The `price_history` table implements Slowly Changing Dimension Type 2:
- **effective_date**: When this price became active
- **end_date**: When this price was superseded (NULL = current)
- **is_current**: Boolean flag for current price (optimization)

Use cases:
- Point-in-time price lookups for historical analysis
- Price change timeline and trend analysis
- Revenue variance analysis using historical prices

### 5. Denormalized Aggregate Pattern (Order Totals)

The `orders.order_total` column stores a pre-computed sum:
- Calculated as `SUM(order_items.total_price)` at order completion
- Enables fast order-level reporting without joins
- Requires validation against source data to detect discrepancies

The `orders.discount_amount` column stores applied discounts:
- Explains difference between gross and net order totals
- Supports discount analysis and reporting

## Data Integrity Notes

### Source of Truth Definitions

| Concept | Authoritative Source | Deprecated/Secondary |
|---------|---------------------|---------------------|
| Region | `territories.region_name` | `salespersons.region` |
| Current Price | `price_history.is_current = true` | `vehicles.msrp` (list price only) |
| Order Total | `SUM(order_items.total_price)` | `orders.order_total` (cached) |

### Referential Integrity

All proposed foreign keys should be enforced:
- `salespersons.territory_id` -> `territories.territory_id`
- `salespersons.manager_id` -> `salespersons.salesperson_id` (nullable for top-level)
- `vehicle_features.vehicle_id` -> `vehicles.vehicle_id`
- `vehicle_features.feature_id` -> `features.feature_id`
- `price_history.vehicle_id` -> `vehicles.vehicle_id`
