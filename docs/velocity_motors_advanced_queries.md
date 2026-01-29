# Velocity Motors - Advanced Query Patterns

This document provides SQL query examples for each advanced relationship pattern in the Velocity Motors dataset. All queries use Databricks SQL syntax.

## Source of Truth Definitions

Before writing queries, understand which columns are authoritative:

| Concept | Authoritative Source | Notes |
|---------|---------------------|-------|
| **Region** | `velocity_motors.sales.territories.region_name` | `salespersons.region` is **DEPRECATED** - retained for backward compatibility only |
| **Current Price** | `velocity_motors.sales.price_history` WHERE `is_current = true` | `vehicles.msrp` represents **list price** (MSRP), not current selling price |
| **Order Total** | `SUM(order_items.total_price)` computed at query time | `orders.order_total` is a **cached value** - use for performance, validate periodically |

## Pattern 1: Hierarchy (Territories)

### ROLLUP Query for Division/Region/Territory Aggregation

Aggregate sales metrics at each level of the geographic hierarchy.

```sql
-- Sales metrics with ROLLUP across territory hierarchy
SELECT
    t.division_name,
    t.region_name,
    t.territory_name,
    COUNT(DISTINCT o.order_id) AS orders,
    COUNT(DISTINCT o.salesperson_id) AS active_salespeople,
    SUM(oi.total_price) AS revenue,
    AVG(oi.total_price) AS avg_order_value
FROM velocity_motors.sales.orders o
JOIN velocity_motors.sales.salespersons s
    ON o.salesperson_id = s.salesperson_id
JOIN velocity_motors.sales.territories t
    ON s.territory_id = t.territory_id
JOIN velocity_motors.sales.order_items oi
    ON o.order_id = oi.order_id
WHERE o.status = 'Completed'
    AND oi.item_type = 'Vehicle'
    AND YEAR(o.order_date) = YEAR(CURRENT_DATE())
GROUP BY ROLLUP(t.division_name, t.region_name, t.territory_name)
ORDER BY
    GROUPING(t.division_name),
    t.division_name,
    GROUPING(t.region_name),
    t.region_name,
    GROUPING(t.territory_name),
    t.territory_name
```

### Region Performance Comparison

Compare regional performance using the authoritative territory data.

```sql
-- Regional performance comparison (use territories, NOT salespersons.region)
SELECT
    t.region_name,
    COUNT(DISTINCT s.salesperson_id) AS headcount,
    SUM(s.quota) AS total_quota,
    SUM(oi.total_price) AS actual_revenue,
    ROUND(100.0 * SUM(oi.total_price) / SUM(s.quota), 1) AS quota_attainment_pct
FROM velocity_motors.sales.territories t
JOIN velocity_motors.sales.salespersons s
    ON t.territory_id = s.territory_id
LEFT JOIN velocity_motors.sales.orders o
    ON s.salesperson_id = o.salesperson_id
    AND o.status = 'Completed'
    AND YEAR(o.order_date) = YEAR(CURRENT_DATE())
LEFT JOIN velocity_motors.sales.order_items oi
    ON o.order_id = oi.order_id
    AND oi.item_type = 'Vehicle'
WHERE t.is_active = true
GROUP BY t.region_name
ORDER BY actual_revenue DESC
```

### Best Practices for Hierarchy Queries

1. **Always use the territories table** for geographic grouping - never use `salespersons.region`
2. **Use ROLLUP/CUBE** for multi-level aggregations to avoid multiple queries
3. **Include GROUPING()** to distinguish between NULL values and subtotals
4. **Filter by is_active** to exclude inactive territories

---

## Pattern 2: Many-to-Many (Vehicle Features)

### Find Vehicles with Multiple Specific Features (AND Logic)

Find vehicles that have ALL specified features.

```sql
-- Vehicles with BOTH leather seats AND sunroof (AND logic)
WITH feature_list AS (
    SELECT feature_id
    FROM velocity_motors.sales.features
    WHERE feature_name IN ('Leather Seats', 'Sunroof')
),
vehicle_matches AS (
    SELECT
        vf.vehicle_id,
        COUNT(DISTINCT vf.feature_id) AS matched_features
    FROM velocity_motors.sales.vehicle_features vf
    JOIN feature_list fl ON vf.feature_id = fl.feature_id
    GROUP BY vf.vehicle_id
    HAVING COUNT(DISTINCT vf.feature_id) = (SELECT COUNT(*) FROM feature_list)
)
SELECT
    v.vehicle_id,
    v.make,
    v.model,
    v.year,
    v.condition,
    v.msrp
FROM velocity_motors.sales.vehicles v
JOIN vehicle_matches vm ON v.vehicle_id = vm.vehicle_id
WHERE v.status = 'Available'
ORDER BY v.msrp
```

### Find Vehicles with Any of Specified Features (OR Logic)

Find vehicles that have ANY of the specified features.

```sql
-- Vehicles with Leather Seats OR Sunroof OR Navigation (OR logic)
SELECT DISTINCT
    v.vehicle_id,
    v.make,
    v.model,
    v.year,
    v.condition,
    v.msrp,
    COLLECT_SET(f.feature_name) AS matching_features
FROM velocity_motors.sales.vehicles v
JOIN velocity_motors.sales.vehicle_features vf
    ON v.vehicle_id = vf.vehicle_id
JOIN velocity_motors.sales.features f
    ON vf.feature_id = f.feature_id
WHERE f.feature_name IN ('Leather Seats', 'Sunroof', 'Navigation System')
    AND v.status = 'Available'
GROUP BY v.vehicle_id, v.make, v.model, v.year, v.condition, v.msrp
ORDER BY SIZE(COLLECT_SET(f.feature_name)) DESC, v.msrp
```

### Feature Popularity Analysis

Analyze which features are most common and their correlation with sales.

```sql
-- Feature popularity by vehicle condition
SELECT
    f.feature_name,
    f.feature_category,
    v.condition,
    COUNT(DISTINCT v.vehicle_id) AS vehicle_count,
    SUM(CASE WHEN vf.is_standard THEN 1 ELSE 0 END) AS standard_count,
    SUM(CASE WHEN NOT vf.is_standard THEN 1 ELSE 0 END) AS optional_count
FROM velocity_motors.sales.features f
JOIN velocity_motors.sales.vehicle_features vf
    ON f.feature_id = vf.feature_id
JOIN velocity_motors.sales.vehicles v
    ON vf.vehicle_id = v.vehicle_id
GROUP BY f.feature_name, f.feature_category, v.condition
ORDER BY vehicle_count DESC
```

### Best Practices for M2M Queries

1. **Use CTEs with HAVING** for AND logic (all features required)
2. **Use DISTINCT with JOIN** for OR logic (any feature matches)
3. **Use COLLECT_SET** to aggregate matched features for display
4. **Consider indexing** the junction table on both foreign keys

---

## Pattern 3: Self-Referential (Manager Hierarchy)

### Recursive CTE for Organization Chart

Traverse the full management hierarchy from top to bottom.

```sql
-- Full org chart using recursive CTE
WITH RECURSIVE org_chart AS (
    -- Anchor: Top-level managers (no manager_id)
    SELECT
        s.salesperson_id,
        s.name,
        s.manager_id,
        s.region,
        1 AS level,
        s.name AS path,
        CAST(s.salesperson_id AS STRING) AS id_path
    FROM velocity_motors.sales.salespersons s
    WHERE s.manager_id IS NULL

    UNION ALL

    -- Recursive: Direct reports
    SELECT
        e.salesperson_id,
        e.name,
        e.manager_id,
        e.region,
        o.level + 1 AS level,
        CONCAT(o.path, ' > ', e.name) AS path,
        CONCAT(o.id_path, '/', e.salesperson_id) AS id_path
    FROM velocity_motors.sales.salespersons e
    JOIN org_chart o ON e.manager_id = o.salesperson_id
)
SELECT
    level,
    REPEAT('  ', level - 1) || name AS indented_name,
    region,
    path
FROM org_chart
ORDER BY id_path
```

### Team Performance Summary

Aggregate metrics for each manager including their entire team.

```sql
-- Manager team performance (direct + indirect reports)
WITH RECURSIVE team_hierarchy AS (
    SELECT
        s.salesperson_id,
        s.name,
        s.manager_id,
        s.salesperson_id AS team_lead_id
    FROM velocity_motors.sales.salespersons s
    WHERE s.manager_id IS NULL

    UNION ALL

    SELECT
        e.salesperson_id,
        e.name,
        e.manager_id,
        COALESCE(e.manager_id, e.salesperson_id) AS team_lead_id
    FROM velocity_motors.sales.salespersons e
    JOIN team_hierarchy h ON e.manager_id = h.salesperson_id
),
team_revenue AS (
    SELECT
        th.team_lead_id,
        SUM(oi.total_price) AS team_revenue,
        COUNT(DISTINCT th.salesperson_id) AS team_size
    FROM team_hierarchy th
    JOIN velocity_motors.sales.orders o
        ON th.salesperson_id = o.salesperson_id
    JOIN velocity_motors.sales.order_items oi
        ON o.order_id = oi.order_id
    WHERE o.status = 'Completed'
        AND oi.item_type = 'Vehicle'
        AND YEAR(o.order_date) = YEAR(CURRENT_DATE())
    GROUP BY th.team_lead_id
)
SELECT
    s.name AS manager_name,
    tr.team_size,
    tr.team_revenue,
    ROUND(tr.team_revenue / tr.team_size, 2) AS revenue_per_person
FROM team_revenue tr
JOIN velocity_motors.sales.salespersons s
    ON tr.team_lead_id = s.salesperson_id
ORDER BY tr.team_revenue DESC
```

### Best Practices for Self-Referential Queries

1. **Use WITH RECURSIVE** for multi-level traversal
2. **Include a path column** for debugging and display
3. **Set a maximum depth** (level < 10) to prevent infinite loops if data has cycles
4. **Handle NULL manager_id** explicitly for root nodes

---

## Pattern 4: SCD Type 2 (Price History)

### Point-in-Time Price Lookup

Get the price that was effective on a specific date.

```sql
-- Get vehicle prices as of a specific date
SELECT
    v.vehicle_id,
    v.make,
    v.model,
    v.year,
    v.msrp AS list_price,
    ph.price AS actual_price_on_date,
    ph.effective_date,
    ph.end_date
FROM velocity_motors.sales.vehicles v
JOIN velocity_motors.sales.price_history ph
    ON v.vehicle_id = ph.vehicle_id
WHERE DATE('2024-06-15') >= ph.effective_date
    AND (ph.end_date IS NULL OR DATE('2024-06-15') < ph.end_date)
ORDER BY v.make, v.model
```

### Current Price Lookup (Optimized)

Use the is_current flag for efficient current price queries.

```sql
-- Current prices using is_current optimization
SELECT
    v.vehicle_id,
    v.make,
    v.model,
    v.year,
    v.msrp AS list_price,
    ph.price AS current_price,
    ROUND(100.0 * (v.msrp - ph.price) / v.msrp, 1) AS discount_pct
FROM velocity_motors.sales.vehicles v
JOIN velocity_motors.sales.price_history ph
    ON v.vehicle_id = ph.vehicle_id
WHERE ph.is_current = true
    AND v.status = 'Available'
ORDER BY discount_pct DESC
```

### Price Change Timeline

Analyze price changes over time for a specific vehicle or across inventory.

```sql
-- Price change history for vehicles
SELECT
    v.vehicle_id,
    v.make,
    v.model,
    ph.effective_date,
    ph.price,
    LAG(ph.price) OVER (
        PARTITION BY v.vehicle_id
        ORDER BY ph.effective_date
    ) AS previous_price,
    ph.price - LAG(ph.price) OVER (
        PARTITION BY v.vehicle_id
        ORDER BY ph.effective_date
    ) AS price_change,
    ph.change_reason
FROM velocity_motors.sales.vehicles v
JOIN velocity_motors.sales.price_history ph
    ON v.vehicle_id = ph.vehicle_id
ORDER BY v.vehicle_id, ph.effective_date
```

### Historical Revenue Analysis

Calculate revenue using prices that were effective at time of sale.

```sql
-- Revenue using historical prices (point-in-time accurate)
SELECT
    DATE_TRUNC('month', o.order_date) AS month,
    v.make,
    SUM(ph.price) AS revenue_at_sale_price,
    SUM(v.msrp) AS revenue_at_list_price,
    ROUND(100.0 * (SUM(v.msrp) - SUM(ph.price)) / SUM(v.msrp), 1) AS avg_discount_pct
FROM velocity_motors.sales.orders o
JOIN velocity_motors.sales.vehicles v
    ON o.vehicle_id = v.vehicle_id
JOIN velocity_motors.sales.price_history ph
    ON v.vehicle_id = ph.vehicle_id
    AND o.order_date >= ph.effective_date
    AND (ph.end_date IS NULL OR o.order_date < ph.end_date)
WHERE o.status = 'Completed'
GROUP BY DATE_TRUNC('month', o.order_date), v.make
ORDER BY month DESC, make
```

### Best Practices for SCD Type 2 Queries

1. **Use is_current = true** for current values (indexed, faster)
2. **Use date range predicates** for point-in-time lookups: `date >= effective_date AND (end_date IS NULL OR date < end_date)`
3. **Use LAG/LEAD** for change analysis
4. **Remember**: `vehicles.msrp` is list price; `price_history` has actual selling price

---

## Pattern 5: Denormalized Aggregate (Order Totals)

### Variance Detection Between Cached and Computed Totals

Identify orders where the cached total differs from the computed total.

```sql
-- Detect discrepancies between cached and computed order totals
WITH computed_totals AS (
    SELECT
        o.order_id,
        o.order_total AS cached_total,
        SUM(oi.total_price) AS computed_total,
        o.discount_amount
    FROM velocity_motors.sales.orders o
    JOIN velocity_motors.sales.order_items oi
        ON o.order_id = oi.order_id
    GROUP BY o.order_id, o.order_total, o.discount_amount
)
SELECT
    order_id,
    cached_total,
    computed_total,
    discount_amount,
    cached_total - computed_total AS variance,
    CASE
        WHEN cached_total = computed_total THEN 'MATCH'
        WHEN ABS(cached_total - computed_total - COALESCE(discount_amount, 0)) < 0.01 THEN 'DISCOUNT_ADJUSTED'
        ELSE 'DISCREPANCY'
    END AS status
FROM computed_totals
WHERE ABS(cached_total - computed_total) > 0.01
ORDER BY ABS(variance) DESC
LIMIT 100
```

### Order Totals Reconciliation Report

Generate a reconciliation report for auditing purposes.

```sql
-- Order totals reconciliation summary
SELECT
    DATE_TRUNC('month', o.order_date) AS month,
    COUNT(*) AS total_orders,
    SUM(CASE
        WHEN ABS(o.order_total - item_totals.computed) < 0.01 THEN 1
        ELSE 0
    END) AS matching_orders,
    SUM(CASE
        WHEN ABS(o.order_total - item_totals.computed) >= 0.01 THEN 1
        ELSE 0
    END) AS mismatched_orders,
    ROUND(100.0 * SUM(CASE
        WHEN ABS(o.order_total - item_totals.computed) < 0.01 THEN 1
        ELSE 0
    END) / COUNT(*), 2) AS match_rate_pct
FROM velocity_motors.sales.orders o
JOIN (
    SELECT order_id, SUM(total_price) AS computed
    FROM velocity_motors.sales.order_items
    GROUP BY order_id
) item_totals ON o.order_id = item_totals.order_id
WHERE o.order_total IS NOT NULL
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY month DESC
```

### Ambiguity Documentation: Order Totals

The `orders.order_total` column introduces intentional ambiguity:

| Scenario | Interpretation |
|----------|----------------|
| `order_total = SUM(order_items.total_price)` | Normal case - cached value matches |
| `order_total = SUM(order_items.total_price) - discount_amount` | Discount was applied post-computation |
| `order_total != SUM(order_items.total_price)` | Data quality issue OR mid-order modification |

**Recommendation**: Always compute totals from `order_items` for reporting. Use `order_total` only for:
- Quick dashboard queries where precision is not critical
- Index optimization (if indexed)
- Identifying data quality issues

### Best Practices for Denormalized Aggregates

1. **Treat cached values as hints**, not sources of truth
2. **Run periodic reconciliation** to detect drift
3. **Document the caching logic** (when is order_total computed/updated?)
4. **Consider discount_amount** when analyzing variances
5. **Use computed values** for financial reporting and audits

---

## Gap Analysis for Implementation

This section identifies the changes needed to implement these advanced patterns in the dataset generators.

### Python Files Requiring Modification

| File | Changes Needed |
|------|----------------|
| `dataset_generators/velocity_motors/sales.py` | Add: territories, features, vehicle_features, price_history generators; Modify: salespersons (add territory_id, manager_id), orders (add order_total, discount_amount) |
| `dataset_generators/velocity_motors/__init__.py` | Export new generator functions |
| `dataset_generators/velocity_motors/utils.py` | Add: territory names, feature catalog, price change reasons |

### Specific Changes Needed

#### 1. New Tables

| Table | Generator Function | Key Logic |
|-------|-------------------|-----------|
| `territories` | `generate_territories()` | 3-level hierarchy: 3 divisions, 6 regions, ~18 territories |
| `features` | `generate_features()` | ~50 features in categories: Safety, Comfort, Technology, Performance |
| `vehicle_features` | `generate_vehicle_features()` | 3-8 features per vehicle, is_standard based on trim level |
| `price_history` | `generate_price_history()` | 1-5 price records per vehicle, chronological effective dates |

#### 2. Column Additions

| Table | Column | Logic |
|-------|--------|-------|
| `salespersons` | `territory_id` | FK from territories, replace region-based assignment |
| `salespersons` | `manager_id` | Hierarchical: 5 top-level managers, each with 2-3 direct reports, then individual contributors |
| `orders` | `order_total` | SUM(order_items.total_price), with ~2% intentional variance for data quality demos |
| `orders` | `discount_amount` | 0-15% of order_total, weighted toward 0 |

#### 3. Data Generation Considerations

- **Territory Assignment**: Map existing 6 regions to new territory structure
- **Manager Hierarchy**: Create realistic org structure (CEO > Regional Managers > Team Leads > Sales Reps)
- **Feature Distribution**: Luxury vehicles have more features; used vehicles may have fewer
- **Price History**: More price changes for older/used vehicles; seasonal adjustments

### Reference Ticket

See follow-up implementation ticket for detailed acceptance criteria and test cases.
