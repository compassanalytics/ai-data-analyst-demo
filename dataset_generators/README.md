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

---

## Healthcare Dataset

A healthcare-focused dataset demonstrating the same good vs bad data modeling principles.

### Quick Start

```bash
# Generate healthcare datasets
uv run python -m dataset_generators.generate_healthcare

# Generate only star schema (clean)
uv run python -m dataset_generators.generate_healthcare --clean-only

# Generate at 10% scale for testing
uv run python -m dataset_generators.generate_healthcare --scale 0.1
```

### Output Structure

```
./data/
├── healthcare_star/
│   ├── dim_patient.parquet        # Patient demographics
│   ├── dim_provider.parquet       # Providers/physicians
│   ├── dim_date.parquet           # Date dimension with flu season
│   ├── dim_diagnosis.parquet      # ICD-10 codes
│   ├── dim_procedure.parquet      # CPT codes
│   ├── dim_payer.parquet          # Insurance payers
│   ├── fact_encounters.parquet    # Patient encounters
│   ├── fact_claims.parquet        # Insurance claims
│   └── fact_prescriptions.parquet # Medications
│
└── healthcare_super/
    └── healthcare_super_table.parquet  # 100+ column nightmare
```

### Star Schema (Clean) - 9 Tables

```
        dim_date
            │
            ▼
    fact_encounters ◄──── dim_patient
            │
            ├──────────► dim_provider
            │
            └──────────► dim_diagnosis

    fact_claims ◄──────► dim_payer
            │
            └──────────► fact_encounters

    fact_prescriptions ◄──► dim_patient
            │
            ├──────────────► dim_provider
            │
            └──────────────► fact_encounters
```

### Super Table Anti-Patterns (Dirty) - 100+ Columns

| Anti-Pattern | Example Columns |
|--------------|-----------------|
| Conflicting Patient IDs | `patient_id`, `patientID`, `PAT_ID` have DIFFERENT values! |
| Multiple Date Formats | `service_date` (date), `ServiceDate` (MM/DD/YYYY), `svc_dt` (YYYYMMDD) |
| Provider ID Chaos | `npi` and `NPI` have DIFFERENT values! |
| Amount Ambiguity | `charge_amt`, `CHARGES`, `billed`, `billed_amt` all differ |
| Boolean Chaos | `is_admitted` contains: 0, 1, 'Y', 'N', True, False, 'YES', 'NO' |
| Cryptic Codes | `enc_type`, `flg1`, `cd1`, `status_cd` - undocumented |

### Demo Questions

**Questions that FAIL on Super Table:**

1. **"How many unique patients do we have?"**
   - Problem: 10+ patient ID columns with DIFFERENT values

2. **"Show admissions from January 2024"**
   - Problem: 10+ date columns with different formats

3. **"What is our total revenue?"**
   - Problem: 15+ amount columns, all different values

4. **"Which provider has the most encounters?"**
   - Problem: `provider_id` vs `PROVIDER_ID` have DIFFERENT values

**Same Questions SUCCEED on Star Schema:**

- Single `patient_key` in fact_encounters
- Consistent `date_key` (YYYYMMDD integer)
- Clear `billed_amount`, `paid_amount` columns
- Single `provider_key` linking to dim_provider

### Healthcare-Specific Features

- **Real ICD-10 codes** in star schema (E11.x Diabetes, I10 Hypertension, etc.)
- **Synthetic codes** in super table (DX-001, SYN-DIAB-01) to avoid PHI concerns
- **Age-appropriate diagnoses** (pregnancy only for females 12-55, etc.)
- **Flu season flag** in date dimension
- **Claim status workflow** (Paid, Pending, Denied, Appealed)
- **Realistic LOS** (Length of Stay) by encounter type

---

## Finance Banking Dataset

A fictional bank dataset demonstrating the same good vs bad data modeling principles, focused on financial services use cases.

### Quick Start

```bash
# Generate finance datasets (star schema + super table)
uv run python dataset_generators/generate_finance.py

# Generate only star schema (clean)
uv run python dataset_generators/generate_finance.py --clean-only

# Generate only super table (dirty)
uv run python dataset_generators/generate_finance.py --dirty-only

# Generate at 10% scale for testing
uv run python dataset_generators/generate_finance.py --scale 0.1 --seed 42
```

### Output Structure

```
./data/
├── finance_star_schema/
│   ├── dim_customer.parquet       # Customer master data with segments
│   ├── dim_product.parquet        # Banking products (loans, cards, deposits)
│   ├── dim_account.parquet        # Customer accounts
│   ├── dim_branch.parquet         # Bank branch locations
│   ├── dim_employee.parquet       # Bank employees
│   ├── dim_date.parquet           # Date dimension with fiscal calendar
│   ├── fact_transaction.parquet   # Transaction records
│   └── fact_account_balance.parquet # Daily balance snapshots
│
└── finance_super_table/
    └── finance_super_table.parquet  # 80+ column nightmare
```

### Star Schema (Clean) - 8 Tables

```
        dim_date
            │
            ▼
    fact_transaction ◄──── dim_account ◄──── dim_customer
            │
            ├──────────► dim_branch
            │
            └──────────► dim_employee

    fact_account_balance ◄──► dim_account
            │
            └────────────────► dim_date

    dim_product (standalone product catalog)
```

**Table Descriptions:**

| Table | Records (scale=1.0) | Description |
|-------|---------------------|-------------|
| dim_customer | 5,000 | Customer master with segment, risk rating, KYC status |
| dim_product | ~25 | Fixed banking products (loans, cards, deposits, investments) |
| dim_account | 8,000 | Customer accounts with type, status, currency |
| dim_branch | 50 | Branch locations with type, region, manager |
| dim_employee | 200 | Employees with role, department, branch assignment |
| dim_date | 1,096 | Date dimension (2023-2025) with fiscal calendar (Feb start) |
| fact_transaction | 500,000 | Transactions with amounts, types, channels |
| fact_account_balance | ~87,000 | Daily balance snapshots (10% sample rate) |

### Super Table Anti-Patterns (Dirty) - 80+ Columns

| Anti-Pattern | Example Columns | Problem |
|--------------|-----------------|---------|
| **6 Transaction IDs** | `txn_id`, `transaction_id`, `trans_id`, `TXN_KEY`, `ref_num`, `reference_number` | Which is the primary key? |
| **6 Account Numbers** | `acct_num`, `account_number`, `ACCTNO`, `account_id`, `acct_id`, `acct` (last 4 only!) | `acct` is truncated! |
| **6 Customer IDs** | `cust_id`, `customer_id`, `CUSTID`, `party_id`, `client_id`, `tax_id` (masked) | Inconsistent formats |
| **10+ Dates** | Various formats: date, MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, DD-Mon-YYYY, separate yr/mth/dy | Which date to filter? |
| **8 Amount Columns** | `amt`, `amount`, `AMT`, `amount_usd`, `amount_local`, `local_amt`, `trans_amt`, `TRANS_AMT` | Which is correct? |
| **12 Balance Columns** | `balance`, `bal`, `BAL`, `current_balance`, `available_balance`, `ledger_balance`, etc. | Risk of double-counting |
| **Segment Codes vs Names** | `seg='R'` vs `segment='Retail'`, `seg='HNW'` vs `segment='High Net Worth'` | Cryptic outputs |
| **Boolean Chaos** | `is_pending` contains: 0, 1, 'Y', 'N', True, False, 'Yes', 'No' | Filters miss records |
| **Mystery Columns** | `cd1`, `cd2`, `val`, `cnt`, `attr1`, `flg1`, `flg2` | No documentation |

### Demo Questions

**Questions that FAIL on Super Table:**

1. **"What was total transaction volume last month?"**
   - Problem: 8 different amount columns (amt, amount, AMT, amount_usd, etc.)
   - AI picks wrong column, gets wrong answer

2. **"How many unique customers transacted?"**
   - Problem: 6 different customer ID columns with different formats
   - Different counts depending on column used

3. **"Show Q1 fiscal year revenue"**
   - Problem: Multiple date columns, fiscal year starts Feb not Jan
   - Uses wrong quarter boundaries

4. **"Breakdown by customer segment"**
   - Problem: Returns codes 'R', 'MA', 'HNW' instead of readable names
   - Meaningless output

5. **"Show pending transactions only"**
   - Problem: `is_pending` has mixed boolean formats (0/1/Y/N/True/False)
   - Partial matches, incorrect filtering

6. **"What is total account balance?"**
   - Problem: 12 balance columns with overlapping semantics
   - Risk of summing related columns and double-counting

**Same Questions SUCCEED on Star Schema:**

- Single `amount` column in fact_transaction
- Single `customer_key` linking to dim_customer
- `fiscal_quarter_name` in dim_date (e.g., "FY2024 Q1")
- `segment` contains readable names ('Retail', 'High Net Worth', etc.)
- Consistent boolean flags (True/False only)
- Clear `current_balance`, `available_balance` with distinct semantics

### Banking-Specific Features

- **Customer Segments**: Retail, Mass Affluent, High Net Worth, Private Banking, Institutional
- **Risk Ratings**: Low, Medium, Medium-High, High (correlated with segment)
- **KYC Status**: Verified, Pending, Expired, Enhanced Due Diligence
- **Transaction Types**: Deposit, Withdrawal, Transfer, Payment, Fee, Interest, Charge, Refund
- **Channels**: Online Banking, Mobile App, ATM, Branch, Wire, ACH
- **Branch Types**: Full Service, Express, Private Banking Center, Commercial Center
- **Products**: 25+ products across Loans, Cards, Deposits, Investments
- **Fiscal Calendar**: Fiscal year starts February 1st (common in banking)
- **Amount Distribution**: Lognormal with median ~$400, capped at $50K

### Genie Knowledge Store Setup

After uploading star schema to Databricks, add these SQL expressions:

**Measures:**

```sql
-- Total Transaction Volume
SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)

-- Net Transaction Flow
SUM(amount)

-- Average Transaction Size
AVG(ABS(amount))

-- Transaction Count by Channel
COUNT(*) GROUP BY channel
```

**Filters:**

```sql
-- Active Customers Only
customer_key IN (
    SELECT DISTINCT customer_key FROM fact_transaction
    WHERE date_key >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd')
)

-- High Net Worth Segment
segment = 'High Net Worth'

-- Fiscal Q1 (Feb-Apr)
fiscal_quarter = 1
```

**Example Questions to Configure:**

```
- What was total transaction volume last quarter?
- Show transactions by customer segment
- Compare deposit vs withdrawal trends
- Which channel has highest transaction volume?
- What is the average account balance by segment?
- How many transactions processed by branch?
```
