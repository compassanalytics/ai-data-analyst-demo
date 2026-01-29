# Velocity Motors Dataset Realism Recommendations

## Executive Summary

The Velocity Motors synthetic dataset currently generates near-pristine data with minimal NULLs, no duplicates, no outliers, and perfect referential integrity. While this ensures data quality for initial testing, it does not reflect real-world automotive dealership data which typically contains missing values, data entry errors, and edge cases. This document outlines specific recommendations to introduce controlled imperfections that will make the dataset more realistic for data engineering and analytics training scenarios.

**Key Recommendations:**
1. Implement a `cleanliness` parameter (0-100) to control data quality levels
2. Introduce NULL injection for optional contact fields (email, phone, address)
3. Expand vehicle makes from 6 to 15 and service types from 10 to 15
4. Add outlier scenarios (fleet orders, high mileage vehicles, rush services)
5. Fix the FK ordering bug at low scale factors

## Current State Analysis

### Data Quality Score: ~95-100 (Near Pristine)

| Metric | Current State | Realistic Target |
|--------|---------------|------------------|
| NULL Rate | <1% | 5-15% |
| Duplicate Rate | 0% | 0.5-2% |
| Outlier Rate | 0% | 1-5% |
| Format Inconsistencies | 0% | 2-5% |

### Dataset Statistics at 0.1 Scale
- **Tables**: 12
- **Customers**: ~5,000
- **Vehicle Makes**: 6
- **Service Types**: 10
- **Lead Sources**: 7

### Semantic NULLs (Appropriate - Keep As Is)

These NULL patterns are semantically correct and should be preserved:

| Field | Table | Reason |
|-------|-------|--------|
| company_name | customers | NULL for Individual segment customers |
| customer_id | leads | NULL for unconverted leads |
| converted_date | leads | NULL for unconverted leads |
| customer_rating | service_orders | NULL for unrated services (~40%) |

### Missing Realistic Patterns

The following patterns are absent but commonly occur in real dealership data:

- No missing contact info (email, phone, address always populated)
- `notes` fields always NULL (unused placeholders that should contain data)
- No data entry errors or typos
- No case inconsistencies in text fields
- No near-duplicate customer records
- No extreme outliers in numeric fields

## Gap Analysis

### 1. NULL Injection Opportunities (Priority: HIGH)

These fields should realistically have missing values in production data:

| Field | Table | Recommended NULL Rate | Rationale |
|-------|-------|----------------------|-----------|
| email | customers | 5-10% | Some customers refuse to provide or have no email |
| phone | customers | 3-8% | Privacy concerns, landline-only households |
| street_address | customers | 2-5% | PO boxes, incomplete records, privacy |
| notes | interactions | 20-40% NULL | Some interactions have no meaningful notes |
| notes | service_orders | 30-50% NULL | Not all services require technician observations |
| phone | leads | 5-10% | Web leads may only provide email |
| last_contact_date | leads | 3-5% | New leads with no follow-up yet |

**Note on `notes` Fields:** Currently always NULL. Should be populated 60-80% of the time with realistic content like:
- Interactions: "Customer inquired about trade-in value", "Scheduled test drive for Saturday"
- Service Orders: "Recommended brake inspection at next visit", "Customer declined cabin filter replacement"

### 2. Variety Expansion (Priority: MEDIUM)

#### Vehicle Makes (Currently 6)

| Current | Recommended Additions |
|---------|----------------------|
| Ford | Nissan |
| Toyota | Hyundai |
| Honda | Kia |
| Chevrolet | Subaru |
| BMW | Mazda |
| Mercedes-Benz | Volkswagen |
| | Audi |
| | Lexus |
| | Acura |

**Rationale:** 15 makes provides realistic brand variety for a multi-line dealership while maintaining manageable complexity.

#### Service Types (Currently 10)

| Current Types | Recommended Additions |
|--------------|----------------------|
| Oil Change | Detailing |
| Tire Rotation | State Inspection |
| Brake Service | Windshield Repair |
| Engine Repair | Key Programming |
| Transmission Service | Suspension Work |
| AC Service | |
| Battery Replacement | |
| Alignment | |
| Diagnostic | |
| Recall Service | |

#### Lead Sources (Currently 7)

| Current Sources | Recommended Additions |
|----------------|----------------------|
| Website | Events/Auto Shows |
| Walk-in | Third-party Referral |
| Referral | Social Media Ads |
| Phone | |
| Email | |
| Mailer | |
| Online Ad | |

### 3. Outlier/Anomaly Injection (Priority: MEDIUM)

Real dealership data contains edge cases and anomalies. Recommended injection:

| Scenario | Target Rate | Description |
|----------|-------------|-------------|
| Fleet bulk orders | 1-2% of sales | Orders with 5+ vehicles from same customer on same day |
| Dealer markup | 0.5% of sales | Final price exceeds MSRP (dealer premium/markup) |
| Negative lifetime value | 0.1% of customers | Total refunds exceed total purchases |
| High mileage trade-ins | 1% of vehicles | Vehicles with >150,000 miles |
| Ultra-low mileage | 0.5% of vehicles | Vehicles with <100 miles (dealer transfers, demos) |
| Same-day rush service | 0.5% of service orders | Service completed same day as scheduling |
| Unusually long service | 0.5% of service orders | Multi-day service (engine rebuilds, body work) |
| Zero-dollar service orders | 0.5% of service orders | Warranty work, goodwill repairs |

### 4. Controlled Messiness (Priority: LOW)

Low-priority but adds realism for data cleaning exercises:

| Pattern | Target Rate | Example |
|---------|-------------|---------|
| Case inconsistency (makes) | 2-5% | "BMW" vs "Bmw" vs "bmw" |
| Case inconsistency (names) | 2-3% | "JOHN SMITH" vs "john smith" |
| Near-duplicate customers | 0.5-1% | Same person, slight address variation |
| Email typos | 1-2% | Missing @, double dots, .con instead of .com |
| Phone format variation | 3-5% | (555) 123-4567 vs 555-123-4567 vs 5551234567 |
| Extra whitespace | 1-2% | "  John Smith  " with leading/trailing spaces |
| Inconsistent state abbreviations | 1-2% | "California" vs "CA" vs "Ca" |

## Implementation Priority Matrix

| Item | Impact | Effort | Priority | Notes |
|------|--------|--------|----------|-------|
| Fix FK ordering bug | Critical | Low | **P0** | Breaks data integrity at low scales |
| Add cleanliness parameter | High | Medium | **P1** | Foundation for all other features |
| NULL injection for optional fields | High | Low | **P1** | Quick win, high realism boost |
| Populate notes fields with content | Medium | Low | **P1** | Currently wasted columns |
| Expand vehicle makes to 15 | Medium | Medium | **P2** | More realistic brand variety |
| Expand service types to 15 | Medium | Low | **P2** | Simple addition |
| Expand lead sources to 10 | Low | Low | **P2** | Simple addition |
| Outlier injection | Medium | Medium | **P2** | Important for edge case testing |
| Case inconsistencies | Low | Low | **P3** | Nice-to-have for data cleaning |
| Near-duplicates | Low | High | **P3** | Complex to implement correctly |

## Technical Recommendations

### Cleanliness Parameter Design

Implement a `cleanliness` parameter ranging from 0-100:
- **100**: Pristine data (current behavior, backwards compatible)
- **0**: Maximum chaos (all imperfections enabled at high rates)

#### Threshold-Based Activation

```
cleanliness = 100: No imperfections (pristine)
cleanliness < 100: NULL injection begins (rate scales with dirtiness)
cleanliness < 90:  Extended variety used (more makes, services, sources)
cleanliness < 80:  Case inconsistencies introduced
cleanliness < 70:  Near-duplicates generated
cleanliness < 60:  Outliers and anomalies injected
cleanliness < 50:  Format inconsistencies (phones, emails)
cleanliness < 40:  Increased error rates across all categories
```

#### Rate Scaling Formula

For NULL injection and other features, scale the rate based on cleanliness:

```python
def get_null_rate(base_rate: float, cleanliness: int) -> float:
    """
    Scale the NULL rate inversely with cleanliness.
    At cleanliness=100, rate is 0.
    At cleanliness=0, rate is base_rate.
    """
    if cleanliness >= 100:
        return 0.0
    dirtiness = (100 - cleanliness) / 100
    return base_rate * dirtiness
```

### NULLABLE_FIELDS Allowlist

Define per table which fields can safely be NULLed without breaking referential integrity or business logic:

```python
NULLABLE_FIELDS = {
    'customers': ['email', 'phone', 'street_address', 'company_name'],
    'interactions': ['notes', 'duration_minutes'],
    'service_orders': ['notes', 'customer_rating'],
    'leads': ['phone', 'last_contact_date'],
    'vehicles': ['notes'],
    'sales_orders': ['notes', 'trade_in_vehicle_id'],
}
```

**Never NULL** (critical fields):
- Primary keys (all `*_id` columns)
- Foreign keys (referential integrity)
- Required business fields: `customer_name`, `segment_id`, `order_date`, `status`, etc.

### Notes Field Population

Implement template-based notes generation:

```python
INTERACTION_NOTES_TEMPLATES = [
    "Customer inquired about {vehicle_make} {vehicle_model}",
    "Discussed financing options, customer prefers {term}-month terms",
    "Scheduled test drive for {day_of_week}",
    "Follow-up call regarding service quote",
    "Customer requested trade-in appraisal",
    "Left voicemail, will try again {day_of_week}",
    None,  # Weighted for realistic NULL rate
]

SERVICE_NOTES_TEMPLATES = [
    "Recommended {service_type} at next visit",
    "Customer declined optional {service_type}",
    "Found minor issue with {component}, customer will monitor",
    "Warranty claim submitted, awaiting approval",
    "Vehicle detailed per customer request",
    "Parts on backorder, customer notified",
    None,  # Weighted for realistic NULL rate
]
```

### Outlier Generation

Implement outlier scenarios with dedicated functions:

```python
def maybe_generate_fleet_order(customer_id: int, rng: np.random.Generator,
                                cleanliness: int) -> list[SalesOrder]:
    """
    At low cleanliness, occasionally generate bulk fleet orders.
    Returns list of 5-20 vehicles if triggered, empty list otherwise.
    """
    if cleanliness >= 60:
        return []
    fleet_rate = 0.02 * (60 - cleanliness) / 60
    if rng.random() < fleet_rate:
        count = rng.integers(5, 21)
        return [generate_sale(customer_id, ...) for _ in range(count)]
    return []
```

## Risk Considerations

### 1. Seed Reproducibility
- **Risk**: Changing generation order will change random sequences, breaking reproducibility
- **Mitigation**: Use independent RNG streams for each new feature; add new generation at end of sequence

### 2. FK Integrity
- **Risk**: NULL injection could accidentally NULL foreign keys
- **Mitigation**: Strict allowlist of NULLABLE_FIELDS; FK columns explicitly excluded

### 3. Analytical Value
- **Risk**: Too much noise could obscure learning patterns
- **Mitigation**: Keep correlations intact (LTV-segment, credit-segment); cleanliness parameter allows users to control

### 4. Performance
- **Risk**: Row-by-row NULL injection could be slow at high scale
- **Mitigation**: Use vectorized operations with NumPy masks for all injection

### 5. Backwards Compatibility
- **Risk**: Existing tests/queries might break with new data patterns
- **Mitigation**: Default cleanliness=100 produces identical output to current generators

## Success Metrics

The implementation should be validated against these criteria:

| Metric | Target |
|--------|--------|
| NULL rates at cleanliness=50 | Match recommended ranges per field |
| FK integrity at all scales/cleanliness | 100% valid foreign keys |
| Extended variety visibility | All 15 makes appear in generated data |
| Outlier frequency at cleanliness=50 | Within 0.5x-2x of target rates |
| Backwards compatibility | cleanliness=100 produces byte-identical output |
| Performance overhead | <10% increase in generation time at scale=1.0 |

## Appendix: Sample Data at Different Cleanliness Levels

### cleanliness=100 (Current/Pristine)
```
customer_id | name         | email                | phone        | street_address
1           | John Smith   | john.smith@email.com | 555-123-4567 | 123 Main St
2           | Jane Doe     | jane.doe@email.com   | 555-987-6543 | 456 Oak Ave
```

### cleanliness=70 (Realistic)
```
customer_id | name         | email                | phone        | street_address
1           | John Smith   | john.smith@email.com | 555-123-4567 | 123 Main St
2           | Jane Doe     | NULL                 | 555-987-6543 | 456 Oak Ave
3           | BOB JOHNSON  | bob.j@email.com      | NULL         | NULL
```

### cleanliness=40 (Messy)
```
customer_id | name         | email                | phone          | street_address
1           | John Smith   | john.smith@email.com | 555-123-4567   | 123 Main St
2           | Jane Doe     | NULL                 | 555-987-6543   | 456 Oak Ave
3           | BOB JOHNSON  | bob.j@email.com      | NULL           | NULL
4           | jane doe     | jane.doe@email..com  | (555) 987-6543 | 456 oak avenue
```
