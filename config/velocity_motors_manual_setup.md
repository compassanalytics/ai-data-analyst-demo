# Velocity Motors Genie Spaces - Manual Setup Guide

This guide contains instructions, join specifications, and example SQL queries
that need to be manually configured in the Databricks Genie UI after space creation.

> **Note**: The Genie API currently does not support setting these fields programmatically.
> Copy-paste these into the Genie Space settings in the Databricks UI.

---

## Sales Analytics

**Config file**: `infra/configs/velocity_motors/sales_analytics.yaml`

### Instructions

```
This space analyzes sales data for Velocity Motors, a multi-brand automotive dealership network.

Business Context:
- Velocity Motors sells new and used vehicles from major manufacturers (Ford, Toyota, Honda, Chevrolet, BMW, Mercedes-Benz)
- Dealership network operates across 6 regions: Northeast, Southeast, Midwest, Southwest, West, Pacific Northwest
- Sales patterns show Q4 spike (Nov-Dec have 1.2x baseline volume)
- Vehicle conditions: New (60%), Certified Pre-Owned (25%), Used (15%)

Table Descriptions:
- salespersons: Sales team members with quotas and commission rates. ~50 salespersons.
- vehicles: Vehicle inventory with VIN, make, model, year, condition, and status.
- orders: Customer vehicle orders with order date, status, and payment method.
- order_items: Line items per order including Vehicle (required), Accessories, and Services.

Key Relationships:
- orders.salesperson_id = salespersons.salesperson_id
- orders.vehicle_id = vehicles.vehicle_id
- order_items.order_id = orders.order_id

Key Metrics:
- Revenue: SUM of order_items.total_price for item_type = 'Vehicle'
- Units Sold: COUNT of completed orders
- Average Order Value: Total revenue / COUNT of orders
- Quota Attainment: (Salesperson revenue / quota) * 100

Business Rules:
- Each order has exactly 1 vehicle item plus optional accessories and services
- Order status values: Completed (85%), Pending (5%), Processing (5%), Cancelled (5%)
- Payment methods: Financing (55%), Cash (20%), Lease (15%), Trade-In + Financing (10%)
- Commission rates range from 1.5% to 4%, correlated with salesperson seniority
```

### Join Specifications

| Left Table | Right Table | Join Keys |
|------------|-------------|-----------|
| `velocity_motors.sales.orders` | `velocity_motors.sales.salespersons` | `salesperson_id=salesperson_id` |
| `velocity_motors.sales.orders` | `velocity_motors.sales.vehicles` | `vehicle_id=vehicle_id` |
| `velocity_motors.sales.order_items` | `velocity_motors.sales.orders` | `order_id=order_id` |

### Example SQL Queries

**1. Total revenue by vehicle make**

```sql
SELECT
  v.make,
  COUNT(DISTINCT o.order_id) as orders,
  SUM(oi.total_price) as revenue
FROM velocity_motors.sales.orders o
JOIN velocity_motors.sales.vehicles v ON o.vehicle_id = v.vehicle_id
JOIN velocity_motors.sales.order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'Completed' AND oi.item_type = 'Vehicle'
GROUP BY v.make
ORDER BY revenue DESC
```

**2. Top salespeople by revenue with quota attainment**

```sql
SELECT
  s.name as salesperson,
  s.region,
  s.quota,
  SUM(oi.total_price) as revenue,
  ROUND(100.0 * SUM(oi.total_price) / s.quota, 1) as quota_attainment_pct
FROM velocity_motors.sales.orders o
JOIN velocity_motors.sales.salespersons s ON o.salesperson_id = s.salesperson_id
JOIN velocity_motors.sales.order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'Completed' AND oi.item_type = 'Vehicle'
  AND YEAR(o.order_date) = YEAR(CURRENT_DATE())
GROUP BY s.salesperson_id, s.name, s.region, s.quota
ORDER BY revenue DESC
LIMIT 10
```

**3. Monthly sales trends**

```sql
SELECT
  DATE_TRUNC('month', o.order_date) as month,
  COUNT(DISTINCT o.order_id) as orders,
  SUM(oi.total_price) as revenue,
  SUM(CASE WHEN v.condition = 'New' THEN oi.total_price ELSE 0 END) as new_vehicle_revenue,
  SUM(CASE WHEN v.condition != 'New' THEN oi.total_price ELSE 0 END) as used_vehicle_revenue
FROM velocity_motors.sales.orders o
JOIN velocity_motors.sales.vehicles v ON o.vehicle_id = v.vehicle_id
JOIN velocity_motors.sales.order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'Completed' AND oi.item_type = 'Vehicle'
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY month DESC
LIMIT 12
```

---

## Customer Intelligence

**Config file**: `infra/configs/velocity_motors/customer_intelligence.yaml`

### Instructions

```
This space analyzes CRM data for Velocity Motors, a multi-brand automotive dealership network.

Business Context:
- Customer base includes Individual buyers (70%), Fleet customers (20%), and Dealer partners (10%)
- Leads are captured from multiple sources with ~20% overall conversion rate
- Customer interactions are tracked across multiple channels with sentiment analysis
- Lifetime Value (LTV) correlates with segment type and customer tenure

Table Descriptions:
- customer_segments: Fixed dimension with 3 segments (Individual, Fleet, Dealer) defining discount tiers and credit limits.
- customers: Customer master data including contact info, address, credit score, and lifetime value.
- interactions: Customer interaction history with type, duration, outcome, and sentiment tracking.
- leads: Sales leads including converted and unconverted prospects with source and interest tracking.
- salespersons: Sales team members (cross-domain reference for lead assignment).

Key Relationships:
- customers.segment_id = customer_segments.segment_id
- interactions.customer_id = customers.customer_id
- leads.customer_id = customers.customer_id (null if unconverted)
- leads.salesperson_id = salespersons.salesperson_id

Key Metrics:
- Lead Conversion Rate: (Converted leads / Total leads) * 100
- Customer Lifetime Value (LTV): lifetime_value field in customers table
- Retention Rate: (Active customers / Total customers) * 100
- Interaction Frequency: COUNT of interactions per customer

Business Rules:
- Segment distribution: Individual 70%, Fleet 20%, Dealer 10%
- Lead status progression: Cold -> Contacted -> Qualified -> Proposal -> Converted/Lost
- Interaction sentiment: Positive (40%), Neutral (45%), Negative (15%)
- Lead sources: Website (35%), Phone Inquiry (20%), Walk-In (15%), Referral (12%), Social Media (8%), Auto Show (5%), Partner (5%)
- High-LTV customers have 10-50 interactions; Low-LTV have 1-5 interactions
```

### Join Specifications

| Left Table | Right Table | Join Keys |
|------------|-------------|-----------|
| `velocity_motors.crm.customers` | `velocity_motors.crm.customer_segments` | `segment_id=segment_id` |
| `velocity_motors.crm.interactions` | `velocity_motors.crm.customers` | `customer_id=customer_id` |
| `velocity_motors.crm.leads` | `velocity_motors.crm.customers` | `customer_id=customer_id` |
| `velocity_motors.crm.leads` | `velocity_motors.sales.salespersons` | `salesperson_id=salesperson_id` |

### Example SQL Queries

**1. Lead conversion rate by source**

```sql
SELECT
  source,
  COUNT(*) as total_leads,
  SUM(CASE WHEN is_converted THEN 1 ELSE 0 END) as converted,
  ROUND(100.0 * SUM(CASE WHEN is_converted THEN 1 ELSE 0 END) / COUNT(*), 1) as conversion_rate_pct
FROM velocity_motors.crm.leads
GROUP BY source
ORDER BY conversion_rate_pct DESC
```

**2. Customer segment analysis with LTV**

```sql
SELECT
  cs.segment_name,
  COUNT(*) as customer_count,
  SUM(CASE WHEN c.is_active THEN 1 ELSE 0 END) as active_customers,
  ROUND(AVG(c.lifetime_value), 2) as avg_ltv,
  SUM(c.lifetime_value) as total_ltv,
  ROUND(AVG(c.credit_score), 0) as avg_credit_score
FROM velocity_motors.crm.customers c
JOIN velocity_motors.crm.customer_segments cs ON c.segment_id = cs.segment_id
GROUP BY cs.segment_name
ORDER BY total_ltv DESC
```

**3. Salesperson lead performance**

```sql
SELECT
  s.name as salesperson,
  s.region,
  COUNT(*) as assigned_leads,
  SUM(CASE WHEN l.is_converted THEN 1 ELSE 0 END) as converted,
  ROUND(100.0 * SUM(CASE WHEN l.is_converted THEN 1 ELSE 0 END) / COUNT(*), 1) as conversion_rate_pct
FROM velocity_motors.crm.leads l
JOIN velocity_motors.sales.salespersons s ON l.salesperson_id = s.salesperson_id
GROUP BY s.salesperson_id, s.name, s.region
HAVING COUNT(*) >= 10
ORDER BY conversion_rate_pct DESC
LIMIT 10
```

---

## Operations & Inventory

**Config file**: `infra/configs/velocity_motors/operations_inventory.yaml`

### Instructions

```
This space analyzes operations and inventory data for Velocity Motors, a multi-brand automotive dealership network.

Business Context:
- Velocity Motors operates multiple warehouse facilities for parts distribution
- Parts are sourced from OEM (20%), Aftermarket (40%), Specialty (20%), and Wholesale (20%) suppliers
- Service department handles maintenance and repairs with parts cost and labor tracking
- Inventory levels are managed based on popularity tiers and reorder points

Part Categories:
- ENG: Engine parts
- BRK: Brake components
- ELE: Electrical systems
- BOD: Body parts
- SUS: Suspension components
- TRN: Transmission parts

Service Types:
- Oil Change, Tire Rotation, Brake Service, Transmission Service
- Engine Repair, AC Service, Battery Replacement, Alignment
- Inspection, Recall Service

Table Descriptions:
- warehouse_locations: Distribution centers and parts depots with capacity and utilization tracking.
- suppliers: Parts suppliers with ratings, lead times, and contract information.
- parts_inventory: Parts stock with quantity, reorder points, and popularity tiers.
- service_orders: Service and maintenance orders with labor/parts costs and customer ratings.
- customers: Customer master data (cross-domain reference for service context).
- vehicles: Vehicle inventory (cross-domain reference for service history).

Key Relationships:
- parts_inventory.supplier_id = suppliers.supplier_id
- parts_inventory.warehouse_id = warehouse_locations.warehouse_id
- service_orders.customer_id = customers.customer_id
- service_orders.vehicle_id = vehicles.vehicle_id

Key Metrics:
- Inventory Value: SUM(quantity_on_hand * unit_cost)
- Warehouse Utilization: current_utilization field (0.60 - 0.95)
- Supplier Rating: rating field (3.0 - 5.0)
- Service Revenue: SUM(total_cost) for completed orders
- Completion Rate: (Completed orders / Total orders) * 100
- Average Customer Rating: AVG(customer_rating) for rated services

Business Rules:
- Warehouse types: Distribution Center (50k-100k sqft), Regional (20k-50k), Parts Depot (5k-20k)
- Lead times vary: OEM (7-21 days), Wholesale (1-7 days)
- Parts status values: In Stock, Below Reorder, Critical Low, Out of Stock
- Service status: Completed (80%), In Progress (10%), Scheduled (5%), Waiting for Parts (3%), Cancelled (2%)
- ~60% of completed service orders have customer ratings
```

### Join Specifications

| Left Table | Right Table | Join Keys |
|------------|-------------|-----------|
| `velocity_motors.operations.parts_inventory` | `velocity_motors.operations.suppliers` | `supplier_id=supplier_id` |
| `velocity_motors.operations.parts_inventory` | `velocity_motors.operations.warehouse_locations` | `warehouse_id=warehouse_id` |
| `velocity_motors.operations.service_orders` | `velocity_motors.crm.customers` | `customer_id=customer_id` |
| `velocity_motors.operations.service_orders` | `velocity_motors.sales.vehicles` | `vehicle_id=vehicle_id` |

### Example SQL Queries

**1. Parts below reorder point by category**

```sql
SELECT
  p.category,
  p.part_number,
  p.part_name,
  p.quantity_on_hand,
  p.reorder_point,
  p.status,
  s.supplier_name,
  s.lead_time_days
FROM velocity_motors.operations.parts_inventory p
JOIN velocity_motors.operations.suppliers s ON p.supplier_id = s.supplier_id
WHERE p.quantity_on_hand <= p.reorder_point
ORDER BY p.category, p.quantity_on_hand ASC
```

**2. Service revenue and ratings by type**

```sql
SELECT
  service_type,
  COUNT(*) as total_orders,
  SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
  ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) as completion_rate_pct,
  SUM(total_cost) as total_revenue,
  ROUND(AVG(CASE WHEN status = 'Completed' THEN total_cost END), 2) as avg_order_value,
  ROUND(AVG(customer_rating), 2) as avg_rating
FROM velocity_motors.operations.service_orders
GROUP BY service_type
ORDER BY total_revenue DESC
```

**3. Inventory value and status by warehouse**

```sql
SELECT
  w.warehouse_name,
  w.warehouse_type,
  w.current_utilization,
  COUNT(p.part_id) as part_count,
  SUM(p.quantity_on_hand * p.unit_cost) as inventory_value,
  SUM(CASE WHEN p.status IN ('Below Reorder', 'Critical Low', 'Out of Stock') THEN 1 ELSE 0 END) as parts_needing_reorder
FROM velocity_motors.operations.warehouse_locations w
LEFT JOIN velocity_motors.operations.parts_inventory p ON w.warehouse_id = p.warehouse_id
WHERE w.is_active = true
GROUP BY w.warehouse_id, w.warehouse_name, w.warehouse_type, w.current_utilization
ORDER BY inventory_value DESC
```

---
