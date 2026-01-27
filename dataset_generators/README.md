# Dataset Generators for Databricks AI/BI Workshop

This folder contains Python scripts to generate demonstration datasets that showcase why **data engineering matters** for AI/BI tools like Databricks Genie.

## Quick Start

```bash
# Install dependencies
uv pip install pandas numpy pyarrow

# Generate all datasets
uv run python generate_all.py
```

## Files

| File | Purpose |
|------|---------|
| `star_schema_generator.py` | Generates well-designed dimensional model (GOOD) |
| `super_table_generator.py` | Generates denormalized mess with anti-patterns (BAD) |
| `genie_failure_scenarios.py` | Documents specific failure cases + demo script |
| `generate_all.py` | Runs both generators |

## Output Structure

```
./data/
├── star_schema/
│   ├── dim_date.parquet        # Date dimension with fiscal calendar
│   ├── dim_product.parquet     # Product hierarchy
│   ├── dim_customer.parquet    # Customer segments
│   ├── dim_store.parquet       # Distribution centers
│   ├── dim_promotion.parquet   # Promotions
│   └── fact_sales.parquet      # Transaction fact table
│
└── super_table/
    └── super_table.parquet     # Everything in one horrible table
```

## Demo Comparison

### Star Schema (Good)

**6 tables, clear relationships:**

```
        dim_date
            │
            ▼
        fact_sales ◄──── dim_product
            │
            ├──────────► dim_customer
            │
            ├──────────► dim_store
            │
            └──────────► dim_promotion
```

**Why Genie succeeds:**
- Clear column names (`net_amount`, not `NET`, `net_amt`, `REV`, etc.)
- One source of truth per concept
- Business-friendly naming (`fiscal_quarter_name`)
- Consistent data types
- Documented relationships

### Super Table (Bad)

**1 table, 120+ columns:**

| Anti-Pattern | Example |
|--------------|---------|
| Redundant columns | `revenue`, `REVENUE`, `REV`, `net_sales`, `net_amt`, `NET`, `net_revenue` |
| Cryptic codes | `seg='ENT'` instead of `segment='Enterprise'` |
| Inconsistent booleans | `is_seasonal` contains: 0, 1, 'Y', 'N', True, False |
| Multiple date formats | `sale_date`, `SaleDate`, `trans_dt`, `dt` |
| Ambiguous names | `val`, `amt`, `cnt`, `flg1`, `type` |

**Why Genie fails:**
- Which "revenue" column is correct?
- Can't map business terms to cryptic codes
- Inconsistent filters break queries
- Too many columns exceed context limits

## Key Demo Questions

### Questions that FAIL on Super Table:

1. **"What was total revenue last quarter?"**
   - Problem: 7 different revenue columns

2. **"Show sales by customer segment"**
   - Problem: Returns `ENT`, `MID`, `SMB` codes (meaningless)

3. **"What was Q1 revenue?"**
   - Problem: Uses calendar Q1, not fiscal Q1 (WRONG answer)

4. **"Show only seasonal products"**
   - Problem: `is_seasonal` has mixed formats (0/1/Y/N/True/False)

### Same Questions SUCCEED on Star Schema:

- Single `net_amount` column
- `segment` contains 'Enterprise', 'Mid-Market', etc.
- `fiscal_quarter` column in dim_date
- Consistent boolean flags

## Genie Knowledge Store Setup

After uploading star schema to Databricks, add these SQL expressions:

### Measures

```sql
-- Gross Margin %
(SUM(net_amount) - SUM(cost_amount)) / NULLIF(SUM(net_amount), 0) * 100

-- Average Order Value
SUM(net_amount) / COUNT(DISTINCT sale_key)
```

### Filters

```sql
-- Active Customers (ordered in last 90 days)
customer_key IN (
    SELECT DISTINCT customer_key FROM fact_sales
    WHERE date_key >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd')
)

-- Enterprise Segment
segment = 'Enterprise'
```

### Example Questions to Configure

```
- What were total sales last quarter?
- Show top 10 products by revenue
- Compare sales by region for Q1 vs Q2
- Which customer segment has highest margin?
- What is our promotion ROI?
```

## Workshop Demo Script

See `genie_failure_scenarios.py` for the complete demo script including:

1. **Part 1: Super Table Disaster** - Show failures (2-3 min)
2. **Part 2: Star Schema Success** - Show same questions working (2-3 min)
3. **Part 3: Killer Question** - Complex query that proves the point (1 min)

**Key Talking Point:**
> "The gap between 86% benchmark accuracy and 6% real-world accuracy isn't about AI capability—it's about data engineering. This is why PoC is easy but production is hard. And this is what Compass does in 10 weeks."

## Uploading to Databricks

### Option 1: UI Upload

1. Go to Catalog > Create Schema
2. For each parquet file:
   - Click "Create Table"
   - Upload parquet file
   - Add column descriptions (important for Genie!)

### Option 2: Notebook Upload

```python
# Upload star schema tables
for table in ['dim_date', 'dim_product', 'dim_customer', 'dim_store', 'dim_promotion', 'fact_sales']:
    df = spark.read.parquet(f'/path/to/star_schema/{table}.parquet')
    df.write.mode('overwrite').saveAsTable(f'workshop.star_schema.{table}')

# Upload super table
df = spark.read.parquet('/path/to/super_table/super_table.parquet')
df.write.mode('overwrite').saveAsTable('workshop.super_table.sales_data')
```

### Adding Column Descriptions

```sql
-- Example: Add description to star schema columns
ALTER TABLE workshop.star_schema.fact_sales
ALTER COLUMN net_amount
COMMENT 'Net revenue after discounts, in USD. Use this for revenue calculations.';

ALTER TABLE workshop.star_schema.dim_date
ALTER COLUMN fiscal_quarter_name
COMMENT 'Fiscal quarter in FY2024 Q1 format. Fiscal year starts February 1st.';
```
