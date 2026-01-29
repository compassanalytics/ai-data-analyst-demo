"""
Test Query System for Dataset Generators.

This module provides a collection of natural language test queries designed
to demonstrate where AI/BI tools like Databricks Genie fail when working
with poorly modeled data.

Each TestQuery includes:
- The natural language question a user might ask
- A description of how/why AI will fail
- Correct SQL for star schema (well-modeled data)
- Incorrect SQL that AI will likely generate against a super table
- Mapping to anti-pattern categories and trap IDs

Use these queries in workshops to demonstrate:
1. The real-world impact of data quality issues
2. How proper star schema design enables AI success
3. Why documentation and metadata matter

Test Query Categories:
- naming: Ambiguous columns, cryptic codes, abbreviations
- redundancy: Duplicate columns, duplicate IDs
- type: Mixed booleans, inconsistent dates, null variations
- structural: Complex joins, anti-joins, set operations
- metadata: Fiscal calendars, undocumented codes, hidden business logic
- trap: Queries that trigger specific trap columns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .anti_patterns import get_registry
from .traps import get_trap_registry


@dataclass
class TestQuery:
    """
    A test query to demonstrate AI/BI failure scenarios.

    Each query represents a natural language question that users might ask,
    along with documentation of how AI will fail and what the correct behavior
    should be.
    """

    id: str
    """Unique identifier, e.g., 'revenue_ambiguity_1'."""

    natural_language: str
    """The question a user would ask, e.g., 'What was total revenue last quarter?'"""

    expected_failure: str
    """Description of how AI will fail or produce incorrect results."""

    correct_sql: str
    """The correct SQL query for a well-modeled star schema."""

    incorrect_sql: str
    """The SQL that AI will likely generate against a super table."""

    anti_pattern_category: str
    """Primary category this tests: naming, redundancy, type, structural, metadata, trap."""

    severity: str
    """Type of failure: 'wrong_answer', 'error', 'partial', 'timeout'."""

    related_patterns: list[str] = field(default_factory=list)
    """Pattern IDs this query tests (from anti_patterns.py)."""

    related_traps: list[str] = field(default_factory=list)
    """Trap IDs this query might trigger (from traps.py)."""

    notes: str = ""
    """Additional workshop notes or talking points."""


class TestQueryGenerator:
    """
    Registry and generator for test queries.

    Provides methods to retrieve test queries by category, patterns,
    or cleanliness level, and to generate test scripts for workshops.
    """

    def __init__(self) -> None:
        """Initialize the query generator with all built-in queries."""
        self._queries: list[TestQuery] = []
        self._register_all_queries()

    def _register_all_queries(self) -> None:
        """Register all built-in test queries."""
        # Register queries by category
        self._register_naming_queries()
        self._register_redundancy_queries()
        self._register_type_queries()
        self._register_structural_queries()
        self._register_metadata_queries()
        self._register_trap_queries()

    # =========================================================================
    # NAMING CATEGORY QUERIES
    # =========================================================================

    def _register_naming_queries(self) -> None:
        """Register test queries for naming anti-patterns."""

        # Revenue ambiguity queries (7 variations as specified)
        revenue_base_queries = [
            (
                "revenue_ambiguity_1",
                "What was total revenue last quarter?",
                "SUM from net_amount column with date filtering",
            ),
            (
                "revenue_ambiguity_2",
                "Show me our monthly revenue for 2024",
                "GROUP BY month with net_amount aggregation",
            ),
            (
                "revenue_ambiguity_3",
                "What's our revenue by product category?",
                "JOIN to dim_product and GROUP BY category",
            ),
            ("revenue_ambiguity_4", "Compare Q1 vs Q2 revenue", "fiscal_quarter grouping with net_amount"),
            (
                "revenue_ambiguity_5",
                "What was revenue for the Enterprise segment?",
                "JOIN to dim_customer with segment filter",
            ),
            (
                "revenue_ambiguity_6",
                "Show year-over-year revenue growth",
                "Compare current and prior year using date dimension",
            ),
            (
                "revenue_ambiguity_7",
                "What's the average revenue per customer?",
                "SUM(net_amount) / COUNT(DISTINCT customer_key)",
            ),
        ]

        for qid, question, note in revenue_base_queries:
            self._queries.append(
                TestQuery(
                    id=qid,
                    natural_language=question,
                    expected_failure=(
                        "Genie encounters 7 columns that could represent revenue: "
                        "net_amt, net_sales, NET, net_revenue, revenue, REVENUE, REV. "
                        "It may: (1) ask for clarification (breaks self-service), "
                        "(2) pick arbitrarily (may be wrong), or "
                        "(3) sum multiple columns (incorrect - they're duplicates)."
                    ),
                    correct_sql=f"""
-- Star Schema: Single source of truth
SELECT SUM(f.net_amount) as total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.fiscal_quarter = 1  -- {note}
""".strip(),
                    incorrect_sql="""
-- Super Table: Which column is revenue?
SELECT SUM(revenue) as total_revenue  -- Or net_amt? Or NET? Or REV?
FROM super_table
WHERE QUARTER(sale_date) = 1  -- Calendar or fiscal?
""".strip(),
                    anti_pattern_category="naming",
                    severity="wrong_answer",
                    related_patterns=["redundancy_duplicate_columns", "naming_ambiguous"],
                    notes=note,
                )
            )

        # Cryptic codes query - ENT vs Enterprise
        self._queries.append(
            TestQuery(
                id="cryptic_codes_segment",
                natural_language="Show me sales for Enterprise customers",
                expected_failure=(
                    "Table contains 'ENT', 'MID', 'SMB', 'IND' codes without documentation. "
                    "Genie doesn't know ENT means Enterprise. It may: "
                    "(1) search for literal 'Enterprise' (no results), "
                    "(2) guess incorrectly which code to use, or "
                    "(3) ask for clarification about the code meaning."
                ),
                correct_sql="""
-- Star Schema: Human-readable dimension values
SELECT SUM(f.net_amount) as total_revenue, c.segment
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
WHERE c.segment = 'Enterprise'
GROUP BY c.segment
""".strip(),
                incorrect_sql="""
-- Super Table: Cryptic codes without documentation
SELECT SUM(net_amt) as total_revenue, cust_seg
FROM super_table
WHERE cust_seg = 'ENT'  -- User asked for 'Enterprise', AI must guess the code
GROUP BY cust_seg
""".strip(),
                anti_pattern_category="naming",
                severity="partial",
                related_patterns=["naming_cryptic_codes"],
                notes="Common in legacy systems where codes were for storage efficiency.",
            )
        )

        # Channel codes
        self._queries.append(
            TestQuery(
                id="cryptic_codes_channel",
                natural_language="What is the breakdown by sales channel?",
                expected_failure=(
                    "Channel stored as ON/OFF/EC. Genie returns these codes without "
                    "understanding ON=On-Premise, OFF=Off-Premise, EC=E-Commerce. "
                    "Business users see meaningless abbreviations in results."
                ),
                correct_sql="""
-- Star Schema: Clear channel names
SELECT c.channel_name, SUM(f.net_amount) as total_revenue
FROM fact_sales f
JOIN dim_channel c ON f.channel_key = c.channel_key
GROUP BY c.channel_name
ORDER BY total_revenue DESC
""".strip(),
                incorrect_sql="""
-- Super Table: Cryptic channel codes
SELECT chnl, SUM(net_amt) as total_revenue
FROM super_table
GROUP BY chnl  -- Returns ON, OFF, EC - meaningless to executives
ORDER BY total_revenue DESC
""".strip(),
                anti_pattern_category="naming",
                severity="partial",
                related_patterns=["naming_cryptic_codes"],
                notes="Executive dashboards need human-readable labels, not codes.",
            )
        )

        # Abbreviation confusion
        self._queries.append(
            TestQuery(
                id="abbreviation_qty",
                natural_language="What's the average qty per order?",
                expected_failure=(
                    "Multiple abbreviated columns exist: qty_sld, unit_sld, QTY_SOLD. "
                    "Genie may interpret 'qty' as any of these, or confuse quantity "
                    "with count. Result: wrong aggregation level or column."
                ),
                correct_sql="""
-- Star Schema: Clear column names
SELECT AVG(order_quantity) as avg_quantity
FROM (
    SELECT sale_key, SUM(quantity_sold) as order_quantity
    FROM fact_sales
    GROUP BY sale_key
) order_totals
""".strip(),
                incorrect_sql="""
-- Super Table: Ambiguous abbreviations
SELECT AVG(qty_sld) as avg_qty  -- Is this line qty or order qty?
FROM super_table  -- Likely gets avg LINE quantity, not ORDER quantity
""".strip(),
                anti_pattern_category="naming",
                severity="wrong_answer",
                related_patterns=["naming_abbreviations", "naming_ambiguous"],
                notes="'qty' could mean line quantity, order quantity, or available stock.",
            )
        )

        # Status code confusion
        self._queries.append(
            TestQuery(
                id="cryptic_codes_status",
                natural_language="How many orders have status 'pending'?",
                expected_failure=(
                    "Status stored as 1-5 codes: 1=Pending, 2=Shipped, 3=Delivered, etc. "
                    "Nowhere documented. Genie can't map 'pending' to code 1. "
                    "May return all records or error on string comparison."
                ),
                correct_sql="""
-- Star Schema: Readable status or documented dimension
SELECT COUNT(*) as pending_orders
FROM fact_sales f
JOIN dim_order_status s ON f.status_key = s.status_key
WHERE s.status_name = 'Pending'
""".strip(),
                incorrect_sql="""
-- Super Table: Undocumented status codes
SELECT COUNT(*) as pending_orders
FROM super_table
WHERE sts_cd = 1  -- Genie must GUESS that 1 = Pending
""".strip(),
                anti_pattern_category="naming",
                severity="error",
                related_patterns=["naming_cryptic_codes", "metadata_undocumented_codes"],
                notes="Tribal knowledge required to interpret status codes.",
            )
        )

    # =========================================================================
    # REDUNDANCY CATEGORY QUERIES
    # =========================================================================

    def _register_redundancy_queries(self) -> None:
        """Register test queries for redundancy anti-patterns."""

        # Net revenue with duplicates
        self._queries.append(
            TestQuery(
                id="duplicate_revenue_net",
                natural_language="What's our net revenue by product?",
                expected_failure=(
                    "Multiple columns claim to be net revenue: net_amt, net_sales, NET, "
                    "net_revenue. Some may have subtle differences (rounding, currency). "
                    "Genie picks one arbitrarily - may be the wrong one for this context."
                ),
                correct_sql="""
-- Star Schema: Single net_amount column
SELECT p.product_name, SUM(f.net_amount) as net_revenue
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_name
ORDER BY net_revenue DESC
""".strip(),
                incorrect_sql="""
-- Super Table: Which is canonical? They might differ!
SELECT prd_nm, SUM(net_revenue) as net_rev  -- or net_amt? or NET?
FROM super_table
GROUP BY prd_nm
ORDER BY net_rev DESC
""".strip(),
                anti_pattern_category="redundancy",
                severity="wrong_answer",
                related_patterns=["redundancy_duplicate_columns"],
                notes="Data reconciliation nightmare when columns have subtle differences.",
            )
        )

        # Duplicate IDs
        self._queries.append(
            TestQuery(
                id="duplicate_ids_lookup",
                natural_language="List all transaction IDs for customer X",
                expected_failure=(
                    "Multiple ID columns exist: txn_id, transaction_id, sale_id, "
                    "order_number, OrderNum. They use different formats (int vs ORD-00000001). "
                    "Genie may return IDs that don't match what the user expects."
                ),
                correct_sql="""
-- Star Schema: Single sale_key with clear natural key
SELECT f.sale_key, f.sale_id  -- Surrogate and natural key
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
WHERE c.customer_name = 'Acme Corp'
ORDER BY f.sale_key
""".strip(),
                incorrect_sql="""
-- Super Table: Which ID to return?
SELECT txn_id, order_number  -- These might not even match!
FROM super_table
WHERE cust_nm = 'Acme Corp'
ORDER BY txn_id
""".strip(),
                anti_pattern_category="redundancy",
                severity="partial",
                related_patterns=["redundancy_duplicate_ids"],
                notes="Users in different departments may expect different ID formats.",
            )
        )

        # Calculated vs stored
        self._queries.append(
            TestQuery(
                id="calculated_margin",
                natural_language="What's the profit margin for each category?",
                expected_failure=(
                    "Table has margin_pct, gm_%, profit_margin stored columns - "
                    "all with slightly different values due to rounding or formula variations. "
                    "Genie picks one, but finance uses a different formula."
                ),
                correct_sql="""
-- Star Schema: Calculate at query time from atomic measures
SELECT
    p.category,
    (SUM(f.net_amount) - SUM(f.cost_amount)) / NULLIF(SUM(f.net_amount), 0) * 100 as margin_pct
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY margin_pct DESC
""".strip(),
                incorrect_sql="""
-- Super Table: Pre-calculated with unknown formula
SELECT
    category,
    AVG(margin_pct) as avg_margin  -- Is this profit/revenue? profit/cost?
FROM super_table                   -- gm_% and profit_margin have different values!
GROUP BY category
ORDER BY avg_margin DESC
""".strip(),
                anti_pattern_category="redundancy",
                severity="wrong_answer",
                related_patterns=["redundancy_calculated_stored"],
                notes="Finance may use different margin formula than operations team.",
            )
        )

    # =========================================================================
    # TYPE CATEGORY QUERIES
    # =========================================================================

    def _register_type_queries(self) -> None:
        """Register test queries for type anti-patterns."""

        # Mixed boolean - active products
        self._queries.append(
            TestQuery(
                id="mixed_boolean_active",
                natural_language="Show active products",
                expected_failure=(
                    "is_active column contains mixed values: 0, 1, 'Y', 'N', 'True', 'False'. "
                    "SQL like WHERE is_active = 1 misses 'Y' and 'True' rows. "
                    "Result: incomplete product list."
                ),
                correct_sql="""
-- Star Schema: Native boolean type
SELECT product_name, category, brand
FROM dim_product
WHERE is_active = TRUE
ORDER BY product_name
""".strip(),
                incorrect_sql="""
-- Super Table: Mixed boolean formats
SELECT prd_nm, category, brand
FROM super_table
WHERE is_active = 1  -- Misses 'Y', 'True', 'Active' values
ORDER BY prd_nm
""".strip(),
                anti_pattern_category="type",
                severity="partial",
                related_patterns=["type_mixed_booleans"],
                notes="Each source system may use different boolean conventions.",
            )
        )

        # Mixed boolean - seasonal filter
        self._queries.append(
            TestQuery(
                id="mixed_boolean_seasonal",
                natural_language="Show seasonal products only",
                expected_failure=(
                    "is_seasonal has 0, 1, 'Y', 'N', True, False as strings. "
                    "Filtering is_seasonal = 'Y' gets some records; is_seasonal = 1 gets others. "
                    "No filter captures all seasonal products."
                ),
                correct_sql="""
-- Star Schema: Boolean column with consistent values
SELECT p.product_name, p.category
FROM dim_product p
WHERE p.is_seasonal = TRUE
""".strip(),
                incorrect_sql="""
-- Super Table: How to filter for seasonal?
SELECT prd_nm, category
FROM super_table
WHERE seasonal_flg = 'Y'  -- Misses is_seasonal=1 and is_seasonal=True
""".strip(),
                anti_pattern_category="type",
                severity="partial",
                related_patterns=["type_mixed_booleans"],
                notes="Legacy ETL often preserves source system boolean formats.",
            )
        )

        # Date format confusion - US vs EU
        self._queries.append(
            TestQuery(
                id="date_format_ambiguous",
                natural_language="What were sales on January 2nd, 2024?",
                expected_failure=(
                    "Date stored as '01/02/2024' string - is this January 2 (US) or "
                    "February 1 (UK/EU)? Genie may interpret incorrectly based on locale. "
                    "International users get wrong results."
                ),
                correct_sql="""
-- Star Schema: Proper DATE type
SELECT SUM(f.net_amount) as daily_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.full_date = '2024-01-02'  -- Unambiguous ISO format
""".strip(),
                incorrect_sql="""
-- Super Table: Ambiguous date string
SELECT SUM(net_amt) as daily_revenue
FROM super_table
WHERE sale_date = '01/02/2024'  -- US or EU format? AI must guess
""".strip(),
                anti_pattern_category="type",
                severity="wrong_answer",
                related_patterns=["type_inconsistent_dates"],
                notes="MM/DD/YYYY vs DD/MM/YYYY causes international confusion.",
            )
        )

        # Date format - multiple formats
        self._queries.append(
            TestQuery(
                id="date_format_multiple",
                natural_language="Show sales from last week",
                expected_failure=(
                    "Date columns in various formats: date object, '01/15/2024', 20240115, "
                    "ISO timestamp. Genie can't reliably compute 'last week' across formats."
                ),
                correct_sql="""
-- Star Schema: Date dimension with flags
SELECT SUM(f.net_amount) as weekly_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.is_last_week = TRUE  -- Pre-computed flag
""".strip(),
                incorrect_sql="""
-- Super Table: Which date column? What format?
SELECT SUM(net_amt) as weekly_revenue
FROM super_table
WHERE trans_dt >= DATEADD(day, -7, CURRENT_DATE)  -- Which of 5 date columns?
""".strip(),
                anti_pattern_category="type",
                severity="error",
                related_patterns=["type_inconsistent_dates"],
                notes="Different date columns may have different timezone handling too.",
            )
        )

        # NULL variations
        self._queries.append(
            TestQuery(
                id="null_variations_filter",
                natural_language="Find records with missing values",
                expected_failure=(
                    "Missing values represented as NULL, '', 'N/A', 'NA', '-1', 0. "
                    "WHERE col IS NULL only finds proper NULLs. Empty strings, 'N/A', "
                    "and sentinel values (-1) are missed."
                ),
                correct_sql="""
-- Star Schema: Consistent NULL handling
SELECT * FROM fact_sales
WHERE promotion_key IS NULL  -- Proper NULL for no promotion
""".strip(),
                incorrect_sql="""
-- Super Table: Multiple missing value representations
SELECT * FROM super_table
WHERE promo_cd IS NULL  -- Misses '', 'N/A', '-', '0' representations
   OR promo_cd = ''
   OR promo_cd = 'N/A'  -- Must enumerate all possibilities
""".strip(),
                anti_pattern_category="type",
                severity="partial",
                related_patterns=["type_null_variations"],
                notes="COUNT(*) vs COUNT(col) behavior becomes unpredictable.",
            )
        )

        # NULL variations - counting
        self._queries.append(
            TestQuery(
                id="null_variations_count",
                natural_language="How many orders had no promotion?",
                expected_failure=(
                    "Promotion marked as NULL, '', 'NONE', '0', 'N/A' inconsistently. "
                    "COUNT WHERE promo IS NULL dramatically undercounts because "
                    "many 'no promotion' records use other representations."
                ),
                correct_sql="""
-- Star Schema: Explicit 'No Promotion' dimension member
SELECT COUNT(*) as no_promo_orders
FROM fact_sales f
JOIN dim_promotion p ON f.promotion_key = p.promotion_key
WHERE p.promotion_name = 'No Promotion'  -- Explicit default value
""".strip(),
                incorrect_sql="""
-- Super Table: Complex null checking required
SELECT COUNT(*) as no_promo_orders
FROM super_table
WHERE promo_cd IS NULL
   OR promo_cd IN ('', 'N/A', 'NONE', '0', '-')  -- Never complete
""".strip(),
                anti_pattern_category="type",
                severity="wrong_answer",
                related_patterns=["type_null_variations"],
                notes="Default dimension members (key=0) are a best practice solution.",
            )
        )

    # =========================================================================
    # STRUCTURAL CATEGORY QUERIES
    # =========================================================================

    def _register_structural_queries(self) -> None:
        """Register test queries for structural anti-patterns."""

        # Anti-join - never sold products
        self._queries.append(
            TestQuery(
                id="antijoin_never_sold",
                natural_language="Which products have never been sold?",
                expected_failure=(
                    "Requires LEFT JOIN + NULL check (anti-join pattern). "
                    "Genie might: (1) do INNER JOIN (excludes unsold products entirely), "
                    "(2) forget NULL check, or (3) get join direction wrong."
                ),
                correct_sql="""
-- Star Schema: Clean anti-join
SELECT p.product_name, p.category, p.brand
FROM dim_product p
LEFT JOIN fact_sales f ON p.product_key = f.product_key
WHERE f.product_key IS NULL
ORDER BY p.product_name
""".strip(),
                incorrect_sql="""
-- Super Table: Anti-join is complex without clear relationships
SELECT DISTINCT prd_nm, category
FROM super_table
WHERE prd_key NOT IN (  -- NOT IN with NULLs is dangerous!
    SELECT DISTINCT prd_key FROM super_table WHERE sale_amt > 0
)
""".strip(),
                anti_pattern_category="structural",
                severity="wrong_answer",
                related_patterns=["structural_denormalization"],
                notes="Anti-join is one of the most commonly misimplemented patterns.",
            )
        )

        # Set difference - Q1 but not Q2
        self._queries.append(
            TestQuery(
                id="set_difference_quarters",
                natural_language="Show customers who bought in Q1 but not Q2",
                expected_failure=(
                    "Requires set difference: NOT EXISTS or EXCEPT pattern. "
                    "Genie often fails this, doing wrong join logic or "
                    "returning customers who bought in both quarters."
                ),
                correct_sql="""
-- Star Schema: Clear set difference with dimension
SELECT DISTINCT c.customer_name
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.fiscal_quarter = 1
  AND c.customer_key NOT IN (
      SELECT f2.customer_key
      FROM fact_sales f2
      JOIN dim_date d2 ON f2.date_key = d2.date_key
      WHERE d2.fiscal_quarter = 2
  )
""".strip(),
                incorrect_sql="""
-- Super Table: Complex self-join logic
SELECT DISTINCT cust_nm
FROM super_table
WHERE QUARTER(sale_date) = 1  -- Calendar or fiscal?
  AND cust_id NOT IN (
      SELECT cust_id FROM super_table
      WHERE QUARTER(sale_date) = 2
  )
-- Assumes calendar quarters, may have NULL issues
""".strip(),
                anti_pattern_category="structural",
                severity="wrong_answer",
                related_patterns=["structural_denormalization", "metadata_hidden_logic"],
                notes="Set operations require clear entity identification.",
            )
        )

        # Top customers by spend
        self._queries.append(
            TestQuery(
                id="aggregation_top_customers",
                natural_language="Top 10 customers by total spend across all their orders",
                expected_failure=(
                    "Needs proper grouping: join to customer, aggregate, sort, limit. "
                    "If relationships aren't documented, Genie may create invalid joins "
                    "or wrong groupings. May also confuse customer_key with customer_id."
                ),
                correct_sql="""
-- Star Schema: Clear relationships
SELECT
    c.customer_name,
    c.segment,
    SUM(f.net_amount) as total_spend
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_key, c.customer_name, c.segment
ORDER BY total_spend DESC
LIMIT 10
""".strip(),
                incorrect_sql="""
-- Super Table: Multiple customer columns, unclear grouping
SELECT
    cust_nm,
    cust_seg,
    SUM(net_amt) as total_spend
FROM super_table
GROUP BY cust_nm, cust_seg  -- cust_id? cust_key? CUSTID?
ORDER BY total_spend DESC
LIMIT 10
-- Duplicate customer names might exist across segments!
""".strip(),
                anti_pattern_category="structural",
                severity="partial",
                related_patterns=["redundancy_duplicate_ids", "structural_denormalization"],
                notes="GROUP BY on the wrong ID column produces incorrect results.",
            )
        )

        # Orphan keys
        self._queries.append(
            TestQuery(
                id="orphan_keys_product",
                natural_language="Show sales by product with category breakdown",
                expected_failure=(
                    "Some product_keys reference non-existent products (orphan keys). "
                    "INNER JOIN silently excludes these sales. LEFT JOIN shows NULLs. "
                    "Either way, totals don't match finance reports."
                ),
                correct_sql="""
-- Star Schema with referential integrity
SELECT
    COALESCE(p.category, 'Unknown') as category,
    COALESCE(p.product_name, 'Unknown Product') as product_name,
    SUM(f.net_amount) as revenue
FROM fact_sales f
LEFT JOIN dim_product p ON f.product_key = p.product_key
GROUP BY COALESCE(p.category, 'Unknown'), COALESCE(p.product_name, 'Unknown Product')
ORDER BY revenue DESC
""".strip(),
                incorrect_sql="""
-- Super Table: Orphan keys cause silent data loss
SELECT
    category,
    prd_nm,
    SUM(net_amt) as revenue
FROM super_table
WHERE prd_key IN (SELECT prd_key FROM products)  -- Some keys don't exist!
GROUP BY category, prd_nm
ORDER BY revenue DESC
-- Missing ~5% of revenue from orphaned products
""".strip(),
                anti_pattern_category="structural",
                severity="wrong_answer",
                related_patterns=["structural_orphan_keys"],
                notes="Data integrity issues are silent killers of analytics accuracy.",
            )
        )

    # =========================================================================
    # METADATA CATEGORY QUERIES
    # =========================================================================

    def _register_metadata_queries(self) -> None:
        """Register test queries for metadata anti-patterns."""

        # Fiscal vs calendar quarter
        self._queries.append(
            TestQuery(
                id="fiscal_quarter",
                natural_language="What's our Q1 revenue?",
                expected_failure=(
                    "Beverage industry uses fiscal calendar starting February 1. "
                    "Fiscal Q1 = Feb-Apr, not Jan-Mar. Genie assumes calendar quarters. "
                    "Result: WRONG quarter boundaries, incorrect revenue."
                ),
                correct_sql="""
-- Star Schema: Explicit fiscal quarter column
SELECT SUM(f.net_amount) as q1_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.fiscal_quarter = 1
  AND d.fiscal_year = 2024
""".strip(),
                incorrect_sql="""
-- Super Table: Assumes calendar quarters
SELECT SUM(net_amt) as q1_revenue
FROM super_table
WHERE QUARTER(sale_date) = 1  -- Calendar Q1 = Jan-Mar (WRONG!)
  AND YEAR(sale_date) = 2024
""".strip(),
                anti_pattern_category="metadata",
                severity="wrong_answer",
                related_patterns=["metadata_hidden_logic"],
                notes="Most beverage companies use Feb-Jan fiscal year. Critical for YoY comparisons.",
            )
        )

        # Active customer definition
        self._queries.append(
            TestQuery(
                id="business_logic_active",
                natural_language="Show active customers only",
                expected_failure=(
                    "What defines 'active'? Has order in last 90 days? Account status flag? "
                    "Not marked as churned? Without documentation, Genie guesses. "
                    "Different users expect different definitions."
                ),
                correct_sql="""
-- Star Schema: Documented is_active_customer SQL expression
SELECT c.customer_name, c.segment
FROM dim_customer c
WHERE c.customer_key IN (
    SELECT DISTINCT customer_key
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE d.full_date >= DATEADD(day, -90, CURRENT_DATE)
)
-- Definition documented in Genie Knowledge Store
""".strip(),
                incorrect_sql="""
-- Super Table: What is 'active'?
SELECT cust_nm, cust_seg
FROM super_table
WHERE active = 1  -- Is this the right flag? What about recent purchases?
-- Different teams have different definitions
""".strip(),
                anti_pattern_category="metadata",
                severity="partial",
                related_patterns=["metadata_hidden_logic", "metadata_no_descriptions"],
                notes="Sales, Finance, and Marketing may each have different 'active' definitions.",
            )
        )

        # Undocumented status codes
        self._queries.append(
            TestQuery(
                id="undocumented_status_3",
                natural_language="Show status code 3 records",
                expected_failure=(
                    "User knows status code 3 exists but not what it means. "
                    "Genie can filter but cannot explain. Status 3 might be "
                    "'Delivered', 'Cancelled', or 'On Hold' - no documentation."
                ),
                correct_sql="""
-- Star Schema: Readable status dimension
SELECT f.*, s.status_name, s.status_description
FROM fact_sales f
JOIN dim_order_status s ON f.status_key = s.status_key
WHERE s.status_code = 3  -- And we can see status_name = 'Delivered'
""".strip(),
                incorrect_sql="""
-- Super Table: Code without meaning
SELECT *
FROM super_table
WHERE sts_cd = 3  -- What does 3 mean? Only tribal knowledge knows
""".strip(),
                anti_pattern_category="metadata",
                severity="partial",
                related_patterns=["metadata_undocumented_codes", "naming_cryptic_codes"],
                notes="Status codes are the most common source of confusion in legacy systems.",
            )
        )

        # Gross margin definition
        self._queries.append(
            TestQuery(
                id="business_logic_margin",
                natural_language="What is our gross margin?",
                expected_failure=(
                    "Gross margin = (Revenue - COGS) / Revenue. But which 'revenue'? "
                    "Gross or net of discounts? Does COGS include freight? Warehousing? "
                    "Company-specific definition not documented anywhere."
                ),
                correct_sql="""
-- Star Schema: Documented margin calculation
SELECT
    (SUM(f.net_amount) - SUM(f.cost_amount)) / NULLIF(SUM(f.net_amount), 0) * 100 as gross_margin_pct
FROM fact_sales f
-- Formula documented: margin uses net_amount (post-discount) and direct product cost
""".strip(),
                incorrect_sql="""
-- Super Table: Undocumented calculation
SELECT
    (SUM(revenue) - SUM(COGS)) / SUM(revenue) * 100 as gross_margin
FROM super_table
-- Is this gross_amount or net? Does COGS include freight?
""".strip(),
                anti_pattern_category="metadata",
                severity="wrong_answer",
                related_patterns=["metadata_hidden_logic", "redundancy_calculated_stored"],
                notes="Finance and Operations often use different margin calculations.",
            )
        )

        # Premium products
        self._queries.append(
            TestQuery(
                id="business_logic_premium",
                natural_language="Show premium products",
                expected_failure=(
                    "What makes a product 'premium'? Price > $X? Premium category? "
                    "Brand tier = premium? No is_premium flag means Genie must guess. "
                    "May use price threshold that doesn't match business definition."
                ),
                correct_sql="""
-- Star Schema: Explicit tier classification
SELECT p.product_name, p.category, p.brand, p.unit_price
FROM dim_product p
WHERE p.brand_tier = 'Premium'
ORDER BY p.unit_price DESC
""".strip(),
                incorrect_sql="""
-- Super Table: No classification, must guess
SELECT prd_nm, category, brand, unit_px
FROM super_table
WHERE unit_px > 10  -- Arbitrary threshold - what defines 'premium'?
ORDER BY unit_px DESC
""".strip(),
                anti_pattern_category="metadata",
                severity="partial",
                related_patterns=["metadata_no_descriptions", "metadata_hidden_logic"],
                notes="Business definitions should be explicit, not inferred from data.",
            )
        )

        # YoY comparison
        self._queries.append(
            TestQuery(
                id="temporal_yoy",
                natural_language="Compare YoY growth",
                expected_failure=(
                    "Year-over-year requires: same period comparison (YTD vs prior YTD), "
                    "handling of leap years, fiscal vs calendar alignment. "
                    "Complex logic often fails without explicit date dimension setup."
                ),
                correct_sql="""
-- Star Schema: Date dimension with prior year links
SELECT
    d.fiscal_year,
    SUM(f.net_amount) as revenue,
    LAG(SUM(f.net_amount)) OVER (ORDER BY d.fiscal_year) as prior_year,
    (SUM(f.net_amount) - LAG(SUM(f.net_amount)) OVER (ORDER BY d.fiscal_year))
        / NULLIF(LAG(SUM(f.net_amount)) OVER (ORDER BY d.fiscal_year), 0) * 100 as yoy_growth
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.fiscal_year
ORDER BY d.fiscal_year
""".strip(),
                incorrect_sql="""
-- Super Table: Complex date handling
SELECT
    YEAR(sale_date) as year,
    SUM(net_amt) as revenue
FROM super_table
GROUP BY YEAR(sale_date)  -- Calendar year, not fiscal!
-- No easy way to compare same fiscal periods
""".strip(),
                anti_pattern_category="metadata",
                severity="wrong_answer",
                related_patterns=["metadata_hidden_logic", "type_inconsistent_dates"],
                notes="YoY on fiscal vs calendar can differ by 2+ months of data.",
            )
        )

    # =========================================================================
    # TRAP CATEGORY QUERIES
    # =========================================================================

    def _register_trap_queries(self) -> None:
        """Register test queries that trigger trap columns."""

        # Trap revenue
        self._queries.append(
            TestQuery(
                id="trap_revenue_total",
                natural_language="What's our total revenue?",
                expected_failure=(
                    "trap_revenue column contains QUANTITY, not dollars. "
                    "AI sums this and reports '$45,000' when actual revenue is '$2.3M'. "
                    "Order of magnitude error goes unnoticed."
                ),
                correct_sql="""
-- Star Schema: Clear net_amount column
SELECT SUM(net_amount) as total_revenue
FROM fact_sales
-- Returns $2,300,000 (correct)
""".strip(),
                incorrect_sql="""
-- Super Table with trap: AI picks wrong column
SELECT SUM(trap_revenue) as total_revenue
FROM super_table
-- Returns $45,000 (actually quantity, not dollars!)
""".strip(),
                anti_pattern_category="trap",
                severity="wrong_answer",
                related_patterns=["redundancy_duplicate_columns"],
                related_traps=["trap_revenue"],
                notes="Column name 'revenue' strongly implies dollars. Trap uses quantity instead.",
            )
        )

        # Trap margin
        self._queries.append(
            TestQuery(
                id="trap_margin_avg",
                natural_language="What's the average profit margin?",
                expected_failure=(
                    "trap_margin contains MARKUP (profit/cost), not margin (profit/revenue). "
                    "25% markup = ~20% margin. AI reports inflated margins. "
                    "Pricing decisions based on wrong metric."
                ),
                correct_sql="""
-- Star Schema: Calculate margin correctly
SELECT
    AVG((net_amount - cost_amount) / NULLIF(net_amount, 0) * 100) as avg_margin_pct
FROM fact_sales
-- Returns ~26% (correct margin = profit/revenue)
""".strip(),
                incorrect_sql="""
-- Super Table with trap: AI uses markup as margin
SELECT AVG(trap_margin) as avg_margin
FROM super_table
-- Returns ~35% (actually markup = profit/cost, inflated!)
""".strip(),
                anti_pattern_category="trap",
                severity="wrong_answer",
                related_patterns=["redundancy_calculated_stored"],
                related_traps=["trap_margin"],
                notes="Markup vs margin confusion is common even among business users.",
            )
        )

        # Trap customer count
        self._queries.append(
            TestQuery(
                id="trap_customer_count_total",
                natural_language="How many customers do we have?",
                expected_failure=(
                    "trap_customer_count contains TRANSACTION count, not unique customers. "
                    "AI reports '50,000 customers' when there are only 500 unique customers. "
                    "Market sizing and CAC calculations completely wrong."
                ),
                correct_sql="""
-- Star Schema: Distinct customer count
SELECT COUNT(DISTINCT customer_key) as customer_count
FROM fact_sales
-- Returns 500 (correct unique customers)
""".strip(),
                incorrect_sql="""
-- Super Table with trap: AI counts transactions
SELECT MAX(trap_customer_count) as customer_count
FROM super_table
-- Returns 50,000 (transaction count, 100x inflated!)
""".strip(),
                anti_pattern_category="trap",
                severity="wrong_answer",
                related_patterns=["naming_ambiguous"],
                related_traps=["trap_customer_count"],
                notes="Customer count vs transaction count is a classic analytics mistake.",
            )
        )

        # Trap total
        self._queries.append(
            TestQuery(
                id="trap_total_sum",
                natural_language="What is the total order value for 2024?",
                expected_failure=(
                    "trap_total is missing 15% tax/fees. AI reports '$850K' when actual is '$1M'. "
                    "Systematically underreports revenue. Looks reasonable, but wrong."
                ),
                correct_sql="""
-- Star Schema: Correct gross amount
SELECT SUM(gross_amount) as total_value
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.calendar_year = 2024
-- Returns $1,000,000 (correct with tax/fees)
""".strip(),
                incorrect_sql="""
-- Super Table with trap: Missing tax/fees
SELECT SUM(trap_total) as total_value
FROM super_table
WHERE YEAR(sale_date) = 2024
-- Returns $850,000 (missing 15% tax/fees!)
""".strip(),
                anti_pattern_category="trap",
                severity="wrong_answer",
                related_patterns=["redundancy_calculated_stored"],
                related_traps=["trap_total"],
                notes="Pre-tax vs post-tax confusion is common in revenue reporting.",
            )
        )

        # Trap status
        self._queries.append(
            TestQuery(
                id="trap_status_active",
                natural_language="Show all active products",
                expected_failure=(
                    "trap_status has INVERTED logic: 0=active, 1=inactive. "
                    "AI filters status=1 expecting active but gets inactive records. "
                    "Returns exactly the wrong set."
                ),
                correct_sql="""
-- Star Schema: Standard boolean
SELECT product_name, category
FROM dim_product
WHERE is_active = TRUE  -- Standard convention
""".strip(),
                incorrect_sql="""
-- Super Table with trap: Inverted logic
SELECT prd_nm, category
FROM super_table
WHERE trap_status = 1  -- Expects active, gets INACTIVE!
""".strip(),
                anti_pattern_category="trap",
                severity="wrong_answer",
                related_patterns=["type_mixed_booleans"],
                related_traps=["trap_status"],
                notes="Inverted boolean logic is surprisingly common in legacy systems.",
            )
        )

        # Trap discount
        self._queries.append(
            TestQuery(
                id="trap_discount_avg",
                natural_language="What is our average discount percentage?",
                expected_failure=(
                    "trap_discount contains dollar AMOUNT, not percentage. "
                    "AI reports 'average 15% discount' when it's actually $15. "
                    "For a $500 order, $15 is only 3%, not 15%."
                ),
                correct_sql="""
-- Star Schema: Calculate percentage from amounts
SELECT
    AVG(discount_amount / NULLIF(gross_amount, 0) * 100) as avg_discount_pct
FROM fact_sales
WHERE discount_amount > 0
-- Returns ~5% (correct percentage)
""".strip(),
                incorrect_sql="""
-- Super Table with trap: Dollar amount treated as percentage
SELECT AVG(trap_discount) as avg_discount_pct
FROM super_table
WHERE trap_discount > 0
-- Returns ~15 (dollars, not percent!)
""".strip(),
                anti_pattern_category="trap",
                severity="wrong_answer",
                related_patterns=["naming_ambiguous"],
                related_traps=["trap_discount"],
                notes="Amount vs percentage confusion affects promotional ROI analysis.",
            )
        )

        # Trap date
        self._queries.append(
            TestQuery(
                id="trap_date_filter",
                natural_language="Show me sales from January 2024",
                expected_failure=(
                    "trap_date contains Unix epoch MILLISECONDS (1704067200000). "
                    "AI tries to filter on this numeric column, fails completely. "
                    "May return empty results or error."
                ),
                correct_sql="""
-- Star Schema: Proper date dimension
SELECT f.sale_key, d.full_date, f.net_amount
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.calendar_month = 1 AND d.calendar_year = 2024
""".strip(),
                incorrect_sql="""
-- Super Table with trap: Epoch milliseconds
SELECT sale_key, trap_date, net_amt
FROM super_table
WHERE MONTH(trap_date) = 1  -- Fails! trap_date is integer 1704067200000
""".strip(),
                anti_pattern_category="trap",
                severity="error",
                related_patterns=["type_inconsistent_dates"],
                related_traps=["trap_date"],
                notes="Unix timestamps require explicit conversion that AI often misses.",
            )
        )

    # =========================================================================
    # QUERY RETRIEVAL METHODS
    # =========================================================================

    def get_all(self) -> list[TestQuery]:
        """
        Get all registered test queries.

        Returns:
            List of all TestQuery instances
        """
        return self._queries.copy()

    def get_by_category(self, category: str) -> list[TestQuery]:
        """
        Get queries for a specific anti-pattern category.

        Args:
            category: Category name (naming, redundancy, type, structural, metadata, trap)

        Returns:
            List of TestQuery instances in that category
        """
        return [q for q in self._queries if q.anti_pattern_category == category]

    def get_by_id(self, query_id: str) -> TestQuery | None:
        """
        Get a specific query by ID.

        Args:
            query_id: Unique query identifier

        Returns:
            TestQuery if found, None otherwise
        """
        for query in self._queries:
            if query.id == query_id:
                return query
        return None

    def get_for_patterns(self, pattern_ids: list[str]) -> list[TestQuery]:
        """
        Get queries that test specific anti-patterns.

        Args:
            pattern_ids: List of pattern IDs to match

        Returns:
            List of TestQuery instances that test any of the patterns
        """
        pattern_set = set(pattern_ids)
        return [q for q in self._queries if pattern_set.intersection(set(q.related_patterns))]

    def get_for_traps(self, trap_ids: list[str]) -> list[TestQuery]:
        """
        Get queries that trigger specific traps.

        Args:
            trap_ids: List of trap IDs to match

        Returns:
            List of TestQuery instances that trigger any of the traps
        """
        trap_set = set(trap_ids)
        return [q for q in self._queries if trap_set.intersection(set(q.related_traps))]

    def get_for_cleanliness(
        self,
        cleanliness: int,
        active_patterns: list[str] | None = None,
    ) -> list[TestQuery]:
        """
        Get relevant test queries for active anti-patterns at cleanliness level.

        Args:
            cleanliness: Cleanliness level (0-100)
            active_patterns: Optional list of active pattern IDs.
                            If None, determined from registry based on cleanliness.

        Returns:
            List of TestQuery instances relevant to active patterns
        """
        if active_patterns is None:
            registry = get_registry()
            active_patterns = registry.get_active_patterns(cleanliness)

        # Also get active traps
        trap_registry = get_trap_registry()
        active_traps = [t.id for t in trap_registry.get_active_traps(cleanliness)]

        # Get queries for patterns and traps
        pattern_queries = self.get_for_patterns(active_patterns or [])
        trap_queries = self.get_for_traps(active_traps)

        # Combine and deduplicate
        seen_ids = set()
        result = []
        for q in pattern_queries + trap_queries:
            if q.id not in seen_ids:
                seen_ids.add(q.id)
                result.append(q)

        return result

    def get_by_severity(self, severity: str) -> list[TestQuery]:
        """
        Get queries by failure severity.

        Args:
            severity: Severity level ('wrong_answer', 'error', 'partial', 'timeout')

        Returns:
            List of TestQuery instances with that severity
        """
        return [q for q in self._queries if q.severity == severity]

    # =========================================================================
    # TEST SCRIPT GENERATION
    # =========================================================================

    def generate_test_script(
        self,
        queries: list[TestQuery] | None = None,
        format: str = "markdown",
        include_sql: bool = True,
    ) -> str:
        """
        Generate a test script document with queries and expected results.

        Args:
            queries: List of queries to include. If None, includes all.
            format: Output format ('markdown', 'text')
            include_sql: Whether to include SQL examples

        Returns:
            Formatted test script as string
        """
        if queries is None:
            queries = self._queries

        if format == "markdown":
            return self._generate_markdown_script(queries, include_sql)
        else:
            return self._generate_text_script(queries, include_sql)

    def _generate_markdown_script(
        self,
        queries: list[TestQuery],
        include_sql: bool,
    ) -> str:
        """Generate markdown-formatted test script."""
        lines = [
            "# AI/BI Genie Test Script",
            "",
            "This document contains test queries to demonstrate where Genie fails",
            "when working with poorly modeled data. Use these in workshops to show",
            "the importance of data engineering.",
            "",
            "## How to Use",
            "",
            "1. Load the **super_table** into a Genie Space (no documentation)",
            "2. Load the **star_schema** tables into a separate Genie Space (with documentation)",
            "3. Ask each question in both spaces and compare results",
            "4. Discuss why the differences occur",
            "",
            "---",
            "",
        ]

        # Group by category
        categories = {}
        for q in queries:
            if q.anti_pattern_category not in categories:
                categories[q.anti_pattern_category] = []
            categories[q.anti_pattern_category].append(q)

        category_order = ["naming", "redundancy", "type", "structural", "metadata", "trap"]
        category_titles = {
            "naming": "Naming Anti-Patterns",
            "redundancy": "Redundancy Anti-Patterns",
            "type": "Type Anti-Patterns",
            "structural": "Structural Anti-Patterns",
            "metadata": "Metadata Anti-Patterns",
            "trap": "Trap Column Tests",
        }

        for cat in category_order:
            if cat not in categories:
                continue

            lines.append(f"## {category_titles.get(cat, cat.title())}")
            lines.append("")

            for q in categories[cat]:
                severity_emoji = {
                    "wrong_answer": "[WRONG]",
                    "error": "[ERROR]",
                    "partial": "[PARTIAL]",
                    "timeout": "[SLOW]",
                }.get(q.severity, "[?]")

                lines.append(f"### {severity_emoji} {q.natural_language}")
                lines.append("")
                lines.append(f"**Query ID:** `{q.id}`")
                lines.append("")
                lines.append("**Expected Failure:**")
                lines.append(f"> {q.expected_failure}")
                lines.append("")

                if q.related_patterns:
                    lines.append(f"**Related Patterns:** {', '.join(q.related_patterns)}")
                    lines.append("")

                if q.related_traps:
                    lines.append(f"**Related Traps:** {', '.join(q.related_traps)}")
                    lines.append("")

                if include_sql:
                    lines.append("**Correct SQL (Star Schema):**")
                    lines.append("```sql")
                    lines.append(q.correct_sql)
                    lines.append("```")
                    lines.append("")
                    lines.append("**Incorrect SQL (Super Table):**")
                    lines.append("```sql")
                    lines.append(q.incorrect_sql)
                    lines.append("```")
                    lines.append("")

                if q.notes:
                    lines.append(f"**Note:** {q.notes}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def _generate_text_script(
        self,
        queries: list[TestQuery],
        include_sql: bool,
    ) -> str:
        """Generate plain text test script."""
        lines = [
            "=" * 80,
            "AI/BI GENIE TEST SCRIPT",
            "=" * 80,
            "",
            "Test queries to demonstrate Genie failures on poorly modeled data.",
            "",
            "INSTRUCTIONS:",
            "1. Load super_table into Genie Space (no documentation)",
            "2. Load star_schema into separate Genie Space (with documentation)",
            "3. Ask each question in both and compare results",
            "",
            "-" * 80,
        ]

        # Group by category
        categories = {}
        for q in queries:
            if q.anti_pattern_category not in categories:
                categories[q.anti_pattern_category] = []
            categories[q.anti_pattern_category].append(q)

        category_order = ["naming", "redundancy", "type", "structural", "metadata", "trap"]

        for cat in category_order:
            if cat not in categories:
                continue

            lines.append("")
            lines.append(f"{'=' * 80}")
            lines.append(f"CATEGORY: {cat.upper()}")
            lines.append(f"{'=' * 80}")

            for q in categories[cat]:
                lines.append("")
                lines.append(f"QUESTION: {q.natural_language}")
                lines.append(f"ID: {q.id}")
                lines.append(f"Severity: {q.severity}")
                lines.append("")
                lines.append("Expected Failure:")
                lines.append(f"  {q.expected_failure}")
                lines.append("")

                if include_sql:
                    lines.append("Correct SQL (Star Schema):")
                    for sql_line in q.correct_sql.split("\n"):
                        lines.append(f"  {sql_line}")
                    lines.append("")
                    lines.append("Incorrect SQL (Super Table):")
                    for sql_line in q.incorrect_sql.split("\n"):
                        lines.append(f"  {sql_line}")
                    lines.append("")

                if q.notes:
                    lines.append(f"Note: {q.notes}")

                lines.append("-" * 80)

        return "\n".join(lines)

    def generate_quick_reference(self) -> str:
        """
        Generate a quick reference card with just questions and categories.

        Returns:
            Formatted quick reference as string
        """
        lines = [
            "=" * 80,
            "GENIE TEST QUERIES - QUICK REFERENCE",
            "=" * 80,
            "",
            f"{'Question':<60} {'Category':<12} {'Severity':<12}",
            "-" * 80,
        ]

        for q in self._queries:
            question = q.natural_language[:58] + ".." if len(q.natural_language) > 60 else q.natural_language
            lines.append(f"{question:<60} {q.anti_pattern_category:<12} {q.severity:<12}")

        lines.append("-" * 80)
        lines.append(f"Total queries: {len(self._queries)}")

        return "\n".join(lines)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about registered queries.

        Returns:
            Dictionary with query statistics
        """
        categories = {}
        severities = {}
        patterns = set()
        traps = set()

        for q in self._queries:
            categories[q.anti_pattern_category] = categories.get(q.anti_pattern_category, 0) + 1
            severities[q.severity] = severities.get(q.severity, 0) + 1
            patterns.update(q.related_patterns)
            traps.update(q.related_traps)

        return {
            "total_queries": len(self._queries),
            "by_category": categories,
            "by_severity": severities,
            "unique_patterns_tested": len(patterns),
            "unique_traps_tested": len(traps),
            "patterns_list": sorted(patterns),
            "traps_list": sorted(traps),
        }


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================


_generator: TestQueryGenerator | None = None


def get_query_generator() -> TestQueryGenerator:
    """
    Get singleton query generator.

    Returns:
        TestQueryGenerator instance
    """
    global _generator
    if _generator is None:
        _generator = TestQueryGenerator()
    return _generator
