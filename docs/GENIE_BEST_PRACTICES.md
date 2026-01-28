# Genie Best Practices

This guide covers data quality and Knowledge Store configuration for effective Genie Spaces.

## The Core Lesson

> **The quality of AI answers depends on the quality of your data, not the AI model.**

In the workshop, we demonstrate this by asking the same questions to two Genie Spaces:
- **Dirty data (super_table):** Genie gets confused, returns wrong answers
- **Clean data (star_schema):** Same questions work perfectly

## Why Dirty Data Fails

### Problem 1: Ambiguous Columns

**Bad:** 7 columns that could mean "revenue"
```
net_amt, NET, net_sales, revenue, REVENUE, REV, net_revenue
```

**Question:** "What's our total revenue?"
**Result:** Genie picks one randomly, or sums them all (double-counting)

**Good:** Single source of truth
```
net_amount  -- The only revenue column, clearly named
```

### Problem 2: Cryptic Codes

**Bad:** Codes without context
```
seg = 'ENT', 'MID', 'SMB'
chnl = 'ON', 'OF', 'PH'
```

**Question:** "Show me enterprise sales"
**Result:** Genie doesn't know ENT = Enterprise

**Good:** Business-friendly values
```
customer_segment = 'Enterprise', 'Mid-Market', 'Small Business'
sales_channel = 'Online', 'In-Store', 'Phone'
```

### Problem 3: Date Confusion

**Bad:** No fiscal year context
```
order_date  -- Just a date, no fiscal context
```

**Question:** "What's Q1 revenue?"
**Result:** Genie uses calendar Q1 (Jan-Mar), but company uses fiscal Q1 (Feb-Apr)

**Good:** Explicit fiscal dimensions
```
fiscal_quarter_name = 'FY24 Q1', 'FY24 Q2', ...
fiscal_year = 2024
```

### Problem 4: Inconsistent Formats

**Bad:** Mixed boolean representations
```
is_seasonal = 0, 1, 'Y', 'N', True, False, 'yes', 'no'
```

**Question:** "Show seasonal products"
**Result:** Genie only filters on one format, misses others

**Good:** Consistent format
```
is_seasonal = true, false  -- Always boolean
```

---

## Data Modeling Best Practices

### Use Star Schema

Star schema separates facts from dimensions:

```
         dim_date
            │
            ▼
dim_product ─── fact_sales ─── dim_customer
            │
            ▼
         dim_store
```

**Benefits:**
- Clear relationships
- Single source of truth
- Business-friendly naming
- Efficient queries

### Table Limit Strategy

Genie supports max **25 tables/views** per space.

**If you have more:**
1. Pre-join related tables into views
2. Create domain-specific Genie Spaces
3. Use metric views for pre-aggregated KPIs

### Column Naming

| Bad | Good |
|-----|------|
| `amt` | `order_amount` |
| `dt` | `order_date` |
| `cust_id` | `customer_id` |
| `cat` | `product_category` |
| `flg1` | `is_promotional` |

---

## Knowledge Store Configuration

The Knowledge Store teaches Genie your business context.

### 1. System Instructions

Navigate to **Configure > Instructions** and add business rules:

```
# Business Context
- Fiscal year starts February 1st
- All monetary values are in USD
- "Active customer" = ordered in last 90 days
- "High-value customer" = lifetime value > $10,000

# Metric Definitions
- Revenue = net_amount (excludes tax and shipping)
- Gross margin = (revenue - cost) / revenue * 100

# Segment Definitions
- Enterprise: >1000 employees
- Mid-Market: 100-1000 employees
- SMB: <100 employees
```

### 2. SQL Expressions

Define exact formulas for metrics:

#### Measures (KPIs)

```sql
-- Gross Margin Percentage
Name: gross_margin
Code: (SUM(net_amount) - SUM(cost)) / SUM(net_amount) * 100
Synonyms: margin, profit margin, GP%
Instructions: Returns percentage. Use for profitability analysis.
```

```sql
-- Year-over-Year Growth
Name: yoy_growth
Code: (SUM(current_year) - SUM(prior_year)) / SUM(prior_year) * 100
Synonyms: YoY, growth rate, annual growth
Instructions: Returns percentage change vs prior year.
```

#### Filters

```sql
-- Recent Orders
Name: recent_orders
Code: order_date >= DATE_SUB(CURRENT_DATE(), 30)
Synonyms: last 30 days, recent sales, new orders
Instructions: Filters to orders within last 30 days.
```

```sql
-- Enterprise Customers Only
Name: enterprise_only
Code: customer_segment = 'Enterprise'
Synonyms: enterprise, large customers, ENT
Instructions: Filters to enterprise segment customers.
```

#### Dimensions

```sql
-- Fiscal Quarter
Name: fiscal_quarter
Code: CASE
        WHEN MONTH(order_date) IN (2,3,4) THEN 'Q1'
        WHEN MONTH(order_date) IN (5,6,7) THEN 'Q2'
        WHEN MONTH(order_date) IN (8,9,10) THEN 'Q3'
        ELSE 'Q4'
      END
Synonyms: quarter, FQ, fiscal period
Instructions: Company fiscal year starts February 1st.
```

### 3. Sample Questions

Train Genie with example queries:

```json
{
  "sample_questions": [
    {"question": ["What were total sales last month?"]},
    {"question": ["Show top 10 customers by revenue"]},
    {"question": ["Compare Q1 vs Q2 by region"]},
    {"question": ["Which products have highest return rate?"]},
    {"question": ["Monthly revenue trend for past year"]},
    {"question": ["Gross margin by category for enterprise"]}
  ]
}
```

### 4. Example SQL

For complex queries, provide worked examples:

```sql
-- Question: Show quarterly revenue by customer segment, year over year

SELECT
  d.fiscal_quarter_name,
  c.customer_segment,
  SUM(CASE WHEN d.fiscal_year = 2024 THEN f.net_amount END) AS current_year,
  SUM(CASE WHEN d.fiscal_year = 2023 THEN f.net_amount END) AS prior_year,
  ROUND(
    (SUM(CASE WHEN d.fiscal_year = 2024 THEN f.net_amount END) -
     SUM(CASE WHEN d.fiscal_year = 2023 THEN f.net_amount END)) /
    SUM(CASE WHEN d.fiscal_year = 2023 THEN f.net_amount END) * 100,
    1
  ) AS yoy_growth_pct
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY 1, 2
ORDER BY 1, 2;
```

### 5. Join Relationships

Define joins in the Knowledge Store (not just relying on PK/FK):

| Left Table | Right Table | Join Condition | Type |
|------------|-------------|----------------|------|
| fact_sales | dim_customer | customer_key = customer_key | many-to-one |
| fact_sales | dim_product | product_key = product_key | many-to-one |
| fact_sales | dim_date | date_key = date_key | many-to-one |

---

## Demo Queries

### Queries That Fail on Dirty Data

| Query | Why It Fails |
|-------|--------------|
| "Total revenue?" | 7 revenue columns, picks wrong one |
| "Sales by segment?" | Returns codes (ENT, MID) not names |
| "Q1 revenue?" | Uses calendar Q1, not fiscal |
| "Seasonal products?" | Inconsistent boolean formats |

### Same Queries Succeed on Clean Data

| Query | Why It Works |
|-------|--------------|
| "Total revenue?" | Single `net_amount` column |
| "Sales by segment?" | Clear `customer_segment` values |
| "Q1 revenue?" | `fiscal_quarter_name` is explicit |
| "Seasonal products?" | Consistent `is_seasonal` boolean |

### Complex Query Demo

**Query:** "Gross margin by category, fiscal QoQ, enterprise only"

**On clean data, this works because:**
- `gross_margin` is defined as SQL expression
- `product_category` is clear
- `fiscal_quarter` dimension exists
- `customer_segment = 'Enterprise'` filter works

---

## Limitations to Know

| Limitation | Value |
|------------|-------|
| Tables per space | 25 max |
| SQL expressions | 200 max |
| Questions/minute (UI) | 20 |
| Questions/minute (API) | 5 |
| Session memory | None (stateless) |

### What Genie Cannot Do

- Query multiple data sources (e.g., Salesforce + warehouse)
- Perform actions (send emails, update records)
- Multi-step reasoning (longer horizon tasks)
- Call external APIs
- Remember previous sessions

**For these needs → Use agentic AI (LangGraph + Genie as a tool)**

---

## Checklist Before Demo

- [ ] Tables have clear, business-friendly names
- [ ] Single source of truth for each metric
- [ ] Codes replaced with readable values (or SQL expressions defined)
- [ ] Fiscal calendar included as dimension
- [ ] System instructions added with business context
- [ ] SQL expressions defined for key metrics
- [ ] Sample questions added
- [ ] Complex example SQL provided
- [ ] All demo queries tested multiple times

---

## References

- [Curate an effective Genie space](https://docs.databricks.com/aws/en/genie/best-practices)
- [Build a knowledge store](https://docs.databricks.com/aws/en/genie/knowledge-store)
- [Troubleshoot Genie spaces](https://docs.databricks.com/aws/en/genie/troubleshooting)
