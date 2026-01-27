"""
Genie Failure Scenarios - Demonstration Cases
==============================================

This module provides specific test cases to demonstrate where AI/BI Genie
will fail or produce incorrect results. Use these in the workshop to show
why data engineering matters.

Categories of Failures:
1. Ambiguous column names
2. Missing metadata/descriptions
3. Complex business logic
4. Undocumented calculations
5. Schema complexity
6. Temporal confusion
7. Aggregation ambiguity
"""

# ============================================================================
# FAILURE CATEGORY 1: AMBIGUOUS COLUMN NAMES
# ============================================================================

AMBIGUOUS_COLUMNS_TEST = {
    "description": "Multiple columns that could answer the same question",
    "setup": """
    -- Create table with redundant revenue columns
    CREATE TABLE sales_ambiguous (
        id INT,
        net_amt DECIMAL(10,2),
        net_sales DECIMAL(10,2),
        net_revenue DECIMAL(10,2),
        revenue DECIMAL(10,2),
        REV DECIMAL(10,2),
        total_sales DECIMAL(10,2)
    );
    """,
    "question": "What was total revenue last month?",
    "expected_failure": """
    Genie will either:
    1. Pick one column arbitrarily (may be wrong)
    2. Ask for clarification (breaks self-service experience)
    3. Sum multiple columns (incorrect - they're duplicates)
    """,
    "fix": """
    Star schema solution: Single fact table with ONE 'net_amount' column.
    Clear naming convention documented in Unity Catalog.
    """
}


# ============================================================================
# FAILURE CATEGORY 2: CRYPTIC ABBREVIATIONS
# ============================================================================

CRYPTIC_CODES_TEST = {
    "description": "Status codes and abbreviations without documentation",
    "setup": """
    -- Table with cryptic codes
    CREATE TABLE orders_cryptic (
        order_id INT,
        cust_seg VARCHAR(3),     -- ENT, MID, SMB, IND
        prd_cat VARCHAR(3),      -- BER, CID, RTD, NAB
        sts_cd INT,              -- 1, 2, 3, 4, 5
        chnl VARCHAR(3),         -- ON, OFF, EC
        typ INT                  -- 1, 2, 3
    );
    """,
    "questions": [
        {
            "question": "Show sales by customer segment",
            "problem": "Genie sees ENT, MID, SMB, IND but doesn't know ENT=Enterprise"
        },
        {
            "question": "How many orders have status 'pending'?",
            "problem": "Which sts_cd = pending? Genie can't map business terms to codes"
        },
        {
            "question": "What is the breakdown by channel?",
            "problem": "ON=On-Premise, OFF=Off-Premise, EC=E-Commerce - not obvious"
        }
    ],
    "fix": """
    Star schema solution:
    - dim_customer with 'segment' column containing 'Enterprise', 'Mid-Market', etc.
    - dim_order_status with status_name column
    - Clear business-friendly naming in all dimensions
    - SQL expressions in Genie Knowledge Store to map common terms
    """
}


# ============================================================================
# FAILURE CATEGORY 3: UNDOCUMENTED BUSINESS LOGIC
# ============================================================================

BUSINESS_LOGIC_TEST = {
    "description": "Questions requiring domain knowledge not in the data",
    "questions": [
        {
            "question": "What was Q1 revenue?",
            "problem": """
            Calendar Q1 (Jan-Mar) or Fiscal Q1 (Feb-Apr)?
            Most beverage companies use fiscal calendar starting Feb 1.
            Without documentation, Genie assumes calendar quarters.
            """,
            "incorrect_sql": "WHERE QUARTER(sale_date) = 1",
            "correct_sql": "WHERE fiscal_quarter = 1"
        },
        {
            "question": "Show active customers only",
            "problem": """
            What defines 'active'?
            - Has order in last 90 days?
            - Account status = 'Active'?
            - Not marked as churned?
            Genie doesn't know your definition.
            """,
        },
        {
            "question": "What is our gross margin?",
            "problem": """
            Gross margin = (Revenue - COGS) / Revenue
            But which 'revenue'? Gross or net of discounts?
            Does COGS include freight? Warehousing?
            Company-specific definitions not in data.
            """,
        },
        {
            "question": "Show premium products",
            "problem": """
            What makes a product 'premium'?
            - Price > $X?
            - In premium category?
            - Brand tier = premium?
            No 'is_premium' flag means Genie guesses.
            """,
        }
    ],
    "fix": """
    Solutions:
    1. Add fiscal calendar to dim_date with fiscal_quarter column
    2. Add is_active_customer flag with clear definition in column description
    3. Create SQL expressions in Genie Knowledge Store:
       - gross_margin: (SUM(net_amount) - SUM(cost_amount)) / SUM(net_amount)
       - active_customer: order_date >= DATE_SUB(CURRENT_DATE, 90)
    4. Document all business rules in table/column descriptions
    """
}


# ============================================================================
# FAILURE CATEGORY 4: TEMPORAL CONFUSION
# ============================================================================

TEMPORAL_TEST = {
    "description": "Date/time handling issues",
    "questions": [
        {
            "question": "Show last week's sales",
            "problem": """
            'Last week' is ambiguous:
            - Last 7 days from today?
            - Previous calendar week (Mon-Sun)?
            - Previous business week?
            Different users expect different answers.
            """,
        },
        {
            "question": "Compare YoY growth",
            "problem": """
            Year-over-year requires:
            - Same period comparison (YTD vs prior YTD)
            - Handling of leap years
            - Fiscal vs calendar year alignment
            Complex logic often fails without explicit setup.
            """,
        },
        {
            "question": "What were sales on 01/02/2024?",
            "problem": """
            Is this January 2nd (US) or February 1st (UK/EU)?
            If date is stored as string in MM/DD/YYYY format,
            international users will be confused.
            """,
        }
    ],
    "fix": """
    Solutions:
    1. dim_date with explicit columns:
       - is_current_week, is_last_week, is_current_month
       - prior_year_date_key for easy YoY joins
       - fiscal_year, fiscal_quarter, fiscal_month
    2. Store dates as proper DATE type, never strings
    3. Add example SQL queries for common time comparisons
    4. Document time zone assumptions
    """
}


# ============================================================================
# FAILURE CATEGORY 5: AGGREGATION AMBIGUITY
# ============================================================================

AGGREGATION_TEST = {
    "description": "Unclear what/how to aggregate",
    "questions": [
        {
            "question": "What is our average order value?",
            "problem": """
            Average of what?
            - AVG(order_total)?
            - SUM(revenue) / COUNT(DISTINCT order_id)?
            - Include or exclude returns?
            - Include shipping/tax?

            With fact_sales at line-item grain:
            - AVG(net_amount) = avg LINE value (wrong!)
            - Need to aggregate to order level first
            """,
            "incorrect_sql": "SELECT AVG(net_amount) FROM fact_sales",
            "correct_sql": """
            SELECT AVG(order_total) FROM (
                SELECT order_id, SUM(net_amount) as order_total
                FROM fact_sales
                GROUP BY order_id
            )
            """
        },
        {
            "question": "How many customers bought Product X?",
            "problem": """
            COUNT(customer_id) vs COUNT(DISTINCT customer_id)?
            Genie might count transactions, not unique customers.
            """,
        },
        {
            "question": "What is our customer retention rate?",
            "problem": """
            Complex metric requiring:
            - Definition of 'retained' (ordered in both periods?)
            - Cohort identification
            - Period boundaries
            Can't be answered with simple SQL on transactional data.
            """,
        }
    ],
    "fix": """
    Solutions:
    1. Create pre-aggregated tables for common metrics:
       - fact_orders (order grain, one row per order)
       - fact_customer_monthly (customer metrics by month)
    2. Define metrics in Genie Knowledge Store:
       - avg_order_value: SUM(net_amount) / COUNT(DISTINCT order_id)
       - unique_customers: COUNT(DISTINCT customer_key)
    3. Use metric views in Databricks for complex calculations
    """
}


# ============================================================================
# FAILURE CATEGORY 6: JOIN COMPLEXITY
# ============================================================================

JOIN_TEST = {
    "description": "Complex joins that Genie may get wrong",
    "questions": [
        {
            "question": "Which products have never been sold?",
            "problem": """
            Requires LEFT JOIN + NULL check:
            SELECT p.* FROM dim_product p
            LEFT JOIN fact_sales f ON p.product_key = f.product_key
            WHERE f.product_key IS NULL

            Genie might:
            - Do INNER JOIN (excludes unsold products!)
            - Miss the NULL check
            """,
        },
        {
            "question": "Show customers who bought in Q1 but not Q2",
            "problem": """
            Requires set difference / NOT EXISTS / EXCEPT
            Complex anti-join pattern that often fails.
            """,
        },
        {
            "question": "Top customers by total spend across all their orders",
            "problem": """
            Needs proper grouping:
            - Join to customer dimension
            - Aggregate at customer level
            - Sort and limit

            If relationships aren't documented, Genie may
            create invalid joins or wrong groupings.
            """,
        }
    ],
    "fix": """
    Solutions:
    1. Document all table relationships in Knowledge Store
    2. Add example SQL for complex patterns (anti-joins, set operations)
    3. Create views for common complex queries
    4. Keep star schema simple (facts + dimensions)
    """
}


# ============================================================================
# DEMO SCRIPT: LIVE FAILURE DEMONSTRATION
# ============================================================================

DEMO_SCRIPT = """
================================================================================
LIVE DEMO: Showing Where Genie Fails (and Why Data Engineering Matters)
================================================================================

SETUP:
1. Load the super_table into a Genie Space (no documentation)
2. Load the star_schema tables into a separate Genie Space (with documentation)

--------------------------------------------------------------------------------
DEMO PART 1: The Super Table Disaster (2-3 minutes)
--------------------------------------------------------------------------------

Open the super_table Genie Space and ask these questions:

Q1: "What was total revenue last month?"

[EXPECTED RESULT]
- Genie hesitates or asks: "Which revenue column? I see net_amt, net_sales,
  NET, net_revenue, revenue, REVENUE, and REV"
- OR picks one arbitrarily (may be wrong)

[TALKING POINT]
"See how having 7 different columns that all sound like revenue creates
confusion? An analyst would know which one to use. AI doesn't."

---

Q2: "Show sales by customer segment"

[EXPECTED RESULT]
- Returns ENT, MID, SMB, IND codes
- No business-friendly labels

[TALKING POINT]
"The AI found the data, but what does 'ENT' mean? Without documentation,
it's just cryptic codes. Your executives won't understand this."

---

Q3: "What was Q1 revenue?"

[EXPECTED RESULT]
- Uses calendar Q1 (Jan-Mar)
- Your business uses fiscal Q1 (Feb-Apr)
- Number is WRONG for your business context

[TALKING POINT]
"This is the dangerous failure. It returned an answer confidently,
but it's the WRONG answer because it doesn't know your fiscal calendar."

--------------------------------------------------------------------------------
DEMO PART 2: The Star Schema Success (2-3 minutes)
--------------------------------------------------------------------------------

Switch to the star_schema Genie Space:

Q1: "What was total revenue last month?"

[EXPECTED RESULT]
- Immediately uses net_amount from fact_sales
- Correct answer, no confusion

---

Q2: "Show sales by customer segment"

[EXPECTED RESULT]
- Returns Enterprise, Mid-Market, Small Business, Independent
- Clear, business-friendly labels

---

Q3: "What was Q1 revenue?"

[EXPECTED RESULT]
- Uses fiscal_quarter from dim_date
- Correct fiscal Q1 (Feb-Apr)
- Matches your business reports

[TALKING POINT]
"Same questions, completely different experience. The difference?
About 10 weeks of data engineering work. This is what we do at Compass."

--------------------------------------------------------------------------------
DEMO PART 3: The Killer Question (1 minute)
--------------------------------------------------------------------------------

Ask this in both spaces:

"Show me gross margin by product category, comparing this fiscal quarter
to the same quarter last year, for enterprise customers only"

[SUPER TABLE]
- Fails completely or gives wrong answer
- Too many columns, ambiguous definitions

[STAR SCHEMA]
- Works (if you've set up the SQL expressions)
- Shows proper fiscal YoY comparison
- Filters correctly

[CLOSING]
"This is why the technology isn't enough. You need the data engineering layer.
That's the difference between a 6% production accuracy and 90%+ accuracy."

================================================================================
"""


# ============================================================================
# SQL EXPRESSIONS TO ADD TO GENIE KNOWLEDGE STORE
# ============================================================================

GENIE_SQL_EXPRESSIONS = """
================================================================================
SQL EXPRESSIONS FOR GENIE KNOWLEDGE STORE (Star Schema)
================================================================================

Add these to your Genie Space under Configure > Knowledge Store > SQL Expressions

--------------------------------------------------------------------------------
MEASURES (Calculations/KPIs)
--------------------------------------------------------------------------------

1. Gross Margin Percentage
   Name: gross_margin_pct
   Expression: (SUM(net_amount) - SUM(cost_amount)) / NULLIF(SUM(net_amount), 0) * 100
   Synonyms: margin, profit margin, GM%, gross margin
   Description: Gross margin as a percentage of net revenue

2. Average Order Value
   Name: avg_order_value
   Expression: SUM(net_amount) / COUNT(DISTINCT sale_key)
   Synonyms: AOV, average transaction, avg sale
   Description: Average revenue per transaction

3. Revenue Per Customer
   Name: revenue_per_customer
   Expression: SUM(net_amount) / COUNT(DISTINCT customer_key)
   Synonyms: ARPC, average revenue per customer
   Description: Total revenue divided by unique customers

4. Units Per Transaction
   Name: units_per_transaction
   Expression: SUM(units_sold) / COUNT(DISTINCT sale_key)
   Synonyms: UPT, items per order
   Description: Average number of units sold per transaction

5. Discount Rate
   Name: discount_rate
   Expression: SUM(discount_amount) / NULLIF(SUM(gross_amount), 0) * 100
   Synonyms: discount percentage, promo rate
   Description: Total discounts as percentage of gross sales

--------------------------------------------------------------------------------
FILTERS (Boolean conditions)
--------------------------------------------------------------------------------

1. Active Customers
   Name: active_customer
   Expression: customer_key IN (
       SELECT DISTINCT customer_key FROM fact_sales
       WHERE date_key >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd')
   )
   Synonyms: current customer, recent customer
   Description: Customers with purchases in the last 90 days

2. Current Year
   Name: current_fiscal_year
   Expression: fiscal_year = YEAR(CURRENT_DATE()) - CASE WHEN MONTH(CURRENT_DATE()) < 2 THEN 1 ELSE 0 END
   Synonyms: this year, FY, current year
   Description: Current fiscal year (Feb-Jan)

3. Enterprise Segment
   Name: enterprise_customers
   Expression: segment = 'Enterprise'
   Synonyms: large customers, enterprise accounts
   Description: Enterprise segment customers only

4. Promotional Sales
   Name: promotional
   Expression: promotion_key IS NOT NULL
   Synonyms: on promo, discounted, has promotion
   Description: Sales with an active promotion

--------------------------------------------------------------------------------
DIMENSIONS (Grouping)
--------------------------------------------------------------------------------

1. Fiscal Quarter Name
   Name: fiscal_period
   Expression: fiscal_quarter_name
   Synonyms: quarter, FQ, fiscal quarter
   Description: Fiscal quarter in FY2024 Q1 format

2. Product Hierarchy
   Name: product_hierarchy
   Expression: CONCAT(category, ' > ', subcategory, ' > ', brand)
   Synonyms: product path, category hierarchy
   Description: Full product categorization path

================================================================================
"""


# ============================================================================
# PRINT ALL SCENARIOS
# ============================================================================

def print_all_scenarios():
    """Print all failure scenarios for reference."""
    print("="*80)
    print("GENIE FAILURE SCENARIOS - WORKSHOP DEMONSTRATION GUIDE")
    print("="*80)
    print(DEMO_SCRIPT)
    print("\n" + "="*80)
    print("SQL EXPRESSIONS TO FIX THESE ISSUES")
    print("="*80)
    print(GENIE_SQL_EXPRESSIONS)


if __name__ == "__main__":
    print_all_scenarios()
