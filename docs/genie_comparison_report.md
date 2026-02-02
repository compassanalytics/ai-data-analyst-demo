# Genie Space Comparison: Star Schema vs Super Table

**Date:** 2026-02-02
**Star Schema Space:** `01f0fff49d0414168adc66b6a1a82289` (6 tables, clean data)
**Super Table Space:** `01f0fff4764f185a9949c4c0c52067f2` (1 table, dirty data)

---

## Executive Summary

The same natural language questions were asked to two Genie Spaces backed by the same underlying data but with different data engineering. The star schema (clean, well-modeled data) consistently returned accurate, confident answers. The super table (denormalized, dirty data) struggled with ambiguous columns, cryptic codes, mixed data types, and produced unreliable results -- often silently returning wrong numbers.

---

## Question 1: Total Revenue

> **"What was the total revenue last year?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT SUM(`fact_sales`.`net_amount`) AS total_revenue
FROM `sandbox`.`analytics`.`fact_sales`
JOIN `sandbox`.`analytics`.`dim_date` ON `fact_sales`.`date_key` = `dim_date`.`date_key`
WHERE `dim_date`.`year` = YEAR(CURRENT_DATE) - 1
```

**Response:**
> The total revenue for last year was **357,654.98**. This figure represents the sum of all net sales amounts recorded for the previous calendar year.

**Analysis:** Genie confidently picked the single `net_amount` column and used the date dimension for clean year filtering.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT SUM(`revenue`) AS total_revenue_last_year
FROM `sandbox`.`demo`.`super_table`
WHERE `sale_date` BETWEEN '2025-01-01' AND '2025-12-31'
```

**Response:**
> Would you prefer to see the total revenue for the fiscal year instead of the calendar year?

**Analysis:** Genie picked `revenue` (1 of 7 possible revenue columns: `net_amt`, `net_sales`, `NET`, `net_revenue`, `revenue`, `REVENUE`, `REV`) and `sale_date` (1 of 5 date columns). It gave a result but hedged with a clarification question, uncertain if it chose correctly.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Revenue column | `net_amount` (only option) | `revenue` (1 of 7 -- could pick wrong one) |
| Date handling | Proper dimension join with `year` column | Hardcoded date range on `sale_date` (1 of 5 date columns) |
| Confidence | Direct answer | Hedged with clarification question |

---

## Question 2: Sales by Customer Segment

> **"Show total sales by customer segment"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT c.`segment`, SUM(f.`net_amount`) AS total_sales
FROM `sandbox`.`analytics`.`fact_sales` f
JOIN `sandbox`.`analytics`.`dim_customer` c ON f.`customer_key` = c.`customer_key`
WHERE c.`segment` IS NOT NULL AND f.`net_amount` IS NOT NULL
GROUP BY c.`segment`
ORDER BY total_sales DESC
```

**Response:**
> Total sales by customer segment are as follows:
> - **Small Business**: 393,182.66
> - **Independent**: 368,647.04
> - **Mid-Market**: 196,506.51
> - **Enterprise**: 104,766.02
>
> **Small Business** has the highest total sales, while **Enterprise** has the lowest among the segments.

**Analysis:** Clean segment names, clear hierarchy, confident answer with ranking.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT `segment`, SUM(`net_sales`) AS total_sales
FROM `sandbox`.`demo`.`super_table`
WHERE `segment` IS NOT NULL AND `net_sales` IS NOT NULL
GROUP BY `segment`
ORDER BY total_sales DESC
```

**Response:**
> Would you like to see total sales by customer segment using gross sales or revenue instead of net sales?

**Analysis:** Genie picked `net_sales` but was unsure -- asked if the user wanted `gross sales` or `revenue` instead. The `segment` column contains cryptic codes (`ENT`, `MID`, `SMB`, `IND`) rather than readable business names. The actual results were not shown, replaced by a clarification question.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Segment values | "Enterprise", "Small Business", etc. | Cryptic codes: `ENT`, `MID`, `SMB`, `IND` |
| Revenue column | `net_amount` (confident) | `net_sales` (uncertain, asked about alternatives) |
| Result shown | Full breakdown with dollar amounts | No data -- asked clarification instead |

---

## Question 3: Monthly Sales per Product (Top 10)

> **"Calculate the total sales per month per product for 2025, top 10 descending"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT d.year, d.month, p.brand, p.product_name, SUM(f.net_amount) AS total_sales
FROM `sandbox`.`analytics`.`fact_sales` f
JOIN `sandbox`.`analytics`.`dim_date` d ON f.date_key = d.date_key
JOIN `sandbox`.`analytics`.`dim_product` p ON f.product_key = p.product_key
WHERE d.year = 2025 AND d.month IS NOT NULL AND p.product_name IS NOT NULL AND p.brand IS NOT NULL
GROUP BY d.year, d.month, p.brand, p.product_name
ORDER BY total_sales DESC
LIMIT 10
```

**Response:**
> Would you prefer to see the top 10 vehicle make and model combinations for each month separately instead of overall?

**Analysis:** Proper 3-way join across fact, date, and product dimensions. Used the date dimension for clean year filtering and included both brand and product name.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT DATE_TRUNC('MONTH', `sale_date`) AS month, `product_name`, SUM(`net_sales`) AS total_sales
FROM `sandbox`.`demo`.`super_table`
WHERE `sale_date` >= '2025-01-01' AND `sale_date` < '2026-01-01'
  AND `product_name` IS NOT NULL AND `sale_date` IS NOT NULL
GROUP BY DATE_TRUNC('MONTH', `sale_date`), `product_name`
ORDER BY total_sales DESC
LIMIT 10
```

**Response:**
> Would you prefer to see the top 10 products for each month separately instead of the top 10 overall?

**Analysis:** Both spaces asked a clarification question here. But the SQL tells the story: the super table used `sale_date` (1 of 5 date columns) and `net_sales` (1 of 7 revenue columns) with no way to verify these are the "right" ones.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Joins | Proper 3-way dimension join | Single table, no join validation |
| Date column | `dim_date.year` (clean integer) | `sale_date` (1 of 5: `sale_date`, `SaleDate`, `trans_dt`, `order_date_iso`, `dt`) |
| Revenue column | `net_amount` | `net_sales` (1 of 7 possible) |

---

## Question 4: Seasonal Products (Mixed Boolean Formats)

> **"Show only seasonal products and their total revenue"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT p.product_sku, p.product_name, SUM(s.net_amount) AS total_revenue
FROM `sandbox`.`analytics`.`dim_product` p
JOIN `sandbox`.`analytics`.`fact_sales` s ON p.product_key = s.product_key
WHERE p.is_seasonal = TRUE AND p.product_name IS NOT NULL AND s.net_amount IS NOT NULL
GROUP BY p.product_sku, p.product_name
ORDER BY total_revenue DESC
```

**Response:**
> There are 18 **seasonal products** listed, each with their total revenue. The top 5 seasonal products by total revenue are:
> - **Northern Brew Stout 12-Pack**: $14,667.77
> - **Heritage Lager Ale Single**: $14,253.32
> - **Craft Select IPA 24-Pack**: $13,704.99
> - **Zero Proof Energy Drink 12-Pack**: $13,352.30
> - **Northern Brew Stout 24-Pack**: $13,263.11
>
> Total revenue for seasonal products ranges from $4,165.88 to $14,667.77.

**Analysis:** Clean boolean filter `is_seasonal = TRUE` captured all 18 seasonal products. Confident, complete answer.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT `product_code`, `product_name`, SUM(`revenue`) AS total_revenue
FROM `sandbox`.`demo`.`super_table`
WHERE (`is_seasonal` = 'True' OR `is_seasonal` = 'Y')
  AND `product_code` IS NOT NULL
  AND `product_name` IS NOT NULL
  AND `revenue` IS NOT NULL
GROUP BY `product_code`, `product_name`
```

**Response:**
> Would you like to see seasonal products identified by other flags or see total revenue calculated using gross or net revenue instead?

**Analysis:** The `is_seasonal` column contains mixed formats: `0`, `1`, `'Y'`, `'N'`, `True`, `False`. Genie only filtered for `'True' OR 'Y'` -- **silently missing records** where `is_seasonal` = `1` (integer) or `True` (boolean). This means an unknown number of seasonal products are excluded from the results, and the user would never know.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Boolean filter | `is_seasonal = TRUE` (clean) | `is_seasonal = 'True' OR 'Y'` (misses `1`, boolean `True`) |
| Products found | All 18 seasonal products | **Unknown subset** -- silent data loss |
| Confidence | Full ranked list | Asked clarification, no data shown |
| Risk | None | **Silent incorrect results** -- worst case scenario |

**This is the most dangerous failure mode: the query runs successfully but returns incomplete data with no warning.**

---

## Question 5: Top Enterprise Customers (Cryptic Codes + Column Ambiguity)

> **"Show me the top 5 enterprise customers by total spend"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT c.customer_name, SUM(f.net_amount) AS total_spend
FROM `sandbox`.`analytics`.`fact_sales` f
JOIN `sandbox`.`analytics`.`dim_customer` c ON f.customer_key = c.customer_key
WHERE c.segment = 'Enterprise' AND c.customer_name IS NOT NULL AND f.net_amount IS NOT NULL
GROUP BY c.customer_name
ORDER BY total_spend DESC
LIMIT 5
```

**Response:**
> The top 5 enterprise customers by total spend are:
> - **The Pine Stadium**: 5,317.50
> - **Royal Lion Hotel**: 3,690.90
> - **Corner Moon Bar**: 3,025.54
> - **Corner Lion Convenience Store**: 2,973.84
> - **The Star Bar**: 2,864.92
>
> The Pine Stadium leads by a significant margin, with a total spend notably higher than the other enterprise customers.

**Analysis:** Clean segment filter, real business names, single revenue column. Confident, actionable answer.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT
  customer_id,
  cust_nm AS customer_name,
  SUM(COALESCE(net_sales, net_amt, net_revenue, revenue, 0)) AS total_spend
FROM `sandbox`.`demo`.`super_table`
WHERE (segment = 'Enterprise' OR SEGMENT_CODE = 'ENT')
  AND customer_id IS NOT NULL
  AND cust_nm IS NOT NULL
GROUP BY customer_id, cust_nm
ORDER BY total_spend DESC
LIMIT 5
```

**Response:**
> The **top 5 enterprise customers by total spend** are:
> - **Customer 296**: $509.85
> - **Customer 220**: $422.41
> - **Customer 382**: $414.11
> - **Customer 217**: $395.83
> - **Customer 191**: $393.31
>
> Customer 296 leads with the highest total spend, and the difference between the top and fifth customer is about $116.54.

**Analysis:** Three compounding problems:

1. **Segment filter chaos**: `segment = 'Enterprise' OR SEGMENT_CODE = 'ENT'` -- had to check two different columns because the codes don't match the business term.

2. **Revenue COALESCE across 4 columns**: `SUM(COALESCE(net_sales, net_amt, net_revenue, revenue, 0))` -- Genie tried to be clever by falling back across columns, but this likely **double-counts** revenue if multiple columns have values for the same row.

3. **Customer names are IDs**: "Customer 296" instead of "The Pine Stadium" -- the `cust_nm` column contains generic identifiers, not business names.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Segment filter | `segment = 'Enterprise'` | `segment = 'Enterprise' OR SEGMENT_CODE = 'ENT'` (two columns) |
| Revenue calc | `SUM(net_amount)` | `SUM(COALESCE(net_sales, net_amt, net_revenue, revenue, 0))` -- potential double-counting |
| Top customer spend | $5,317.50 | $509.85 -- **10x lower, likely wrong** |
| Customer names | Real: "The Pine Stadium" | Generic: "Customer 296" |
| Actionable? | Yes -- can contact these businesses | No -- "Customer 296" means nothing |

---

## Question 6: Q1 Revenue (Fiscal vs Calendar Quarter)

> **"What was Q1 revenue?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT SUM(`fact_sales`.`net_amount`) AS q1_revenue
FROM `sandbox`.`analytics`.`fact_sales`
JOIN `sandbox`.`analytics`.`dim_date` ON `fact_sales`.`date_key` = `dim_date`.`date_key`
WHERE `dim_date`.`fiscal_quarter` = 1 AND `fact_sales`.`net_amount` IS NOT NULL;
```

**Response:**
> The total revenue for Q1 was **$256,409.06**. This figure represents the sum of all net sales amounts recorded for fiscal quarter 1.

**Analysis:** Used `fiscal_quarter` from the date dimension. The star schema's date table encodes fiscal calendar logic, so Genie correctly interprets "Q1" as fiscal Q1 (Feb-Apr for this business).

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT SUM(`revenue`) AS q1_revenue
FROM `sandbox`.`demo`.`super_table`
WHERE `Q` = 'Q1' AND `revenue` IS NOT NULL
```

**Response:**
> Would you like to see the revenue for Q1 using net revenue or gross revenue instead?

**Analysis:** Genie found a mystery column called `Q` and filtered on `'Q1'` -- but there's no documentation on whether this represents fiscal or calendar quarter. It also picked `revenue` (1 of 7) and asked about alternatives.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Quarter definition | `fiscal_quarter` from date dimension (explicit) | `Q = 'Q1'` -- mystery column, fiscal or calendar? |
| Revenue column | `net_amount` | `revenue` (1 of 7, uncertain) |
| Result | $256,409.06 with confidence | Unknown amount, asked clarification |

---

## Question 7: Profit Margin by Category

> **"What is the profit margin by product category?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT p.`category`,
  try_divide(SUM(s.`profit_amount`), SUM(s.`net_amount`)) AS profit_margin
FROM `sandbox`.`analytics`.`fact_sales` s
JOIN `sandbox`.`analytics`.`dim_product` p ON s.`product_key` = p.`product_key`
WHERE p.`category` IS NOT NULL AND s.`profit_amount` IS NOT NULL AND s.`net_amount` IS NOT NULL
GROUP BY p.`category`
```

**Response:**
> The profit margin by product category is as follows:
> - **Cider:** 38.4%
> - **Beer:** 37.0%
> - **Non-Alcoholic:** 32.1%
> - **Ready-to-Drink:** 30.1%
>
> Cider has the highest profit margin, while Ready-to-Drink has the lowest among the listed categories.

**Analysis:** Genie *calculated* margin from component columns: `profit_amount / net_amount`. Readable category names. Clear, actionable breakdown.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT `category`, AVG(`margin_pct`) AS avg_profit_margin
FROM `sandbox`.`demo`.`super_table`
WHERE `category` IS NOT NULL AND `margin_pct` IS NOT NULL
GROUP BY `category`
```

**Response:**
> Would you like to see the profit margin by product category using gross margin percentage or profit margin instead?

**Analysis:** Instead of calculating margin from components, Genie used a pre-calculated `margin_pct` column. But it could have picked `margin`, `gm_%`, or `profit_margin` -- all potentially calculated differently. The `category` column likely returns cryptic codes (`BER`, `CID`, `RTD`, `NAB`) instead of readable names.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Methodology | Calculated: `profit_amount / net_amount` | Pre-calculated: `AVG(margin_pct)` (1 of 4 margin columns) |
| Category names | "Beer", "Cider", "Non-Alcoholic", "Ready-to-Drink" | Likely codes: `BER`, `CID`, `NAB`, `RTD` |
| Transparency | Full audit trail (numerator and denominator visible) | Black box -- how was `margin_pct` computed? |

---

## Question 8: Units Sold per Sales Channel

> **"How many units were sold per sales channel last year?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT c.channel, SUM(s.units_sold) AS total_units_sold
FROM `sandbox`.`analytics`.`fact_sales` s
JOIN `sandbox`.`analytics`.`dim_date` d ON s.date_key = d.date_key
JOIN `sandbox`.`analytics`.`dim_customer` c ON s.customer_key = c.customer_key
WHERE d.year = 2023 AND c.channel IS NOT NULL
GROUP BY c.channel
ORDER BY total_units_sold DESC;
```

**Response:**
> In 2023, the number of units sold per sales channel was as follows:
> - **E-Commerce:** 353,229 units
> - **Off-Premise:** 342,709 units
> - **On-Premise:** 331,112 units
>
> E-Commerce had the highest sales, followed closely by Off-Premise and On-Premise channels.

**Analysis:** Readable channel names, proper date dimension join, single `units_sold` column. Clean and actionable.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT `channel`, SUM(`units`) AS units_sold
FROM `sandbox`.`demo`.`super_table`
WHERE `sale_date` >= date_trunc('YEAR', date_add(YEAR, -1, CURRENT_DATE))
  AND `sale_date` <= date_add(YEAR, -1, date_trunc('YEAR', CURRENT_DATE))
  AND `units` IS NOT NULL
  AND `channel` IS NOT NULL
GROUP BY `channel`
ORDER BY units_sold DESC
```

**Response:**
> Would you prefer to see units sold per sales channel for the last 12 months instead of the previous calendar year?

**Analysis:** Genie picked `units` (1 of 5 quantity columns: `qty`, `quantity`, `QTY_SOLD`, `units`, `unit_sold`). The `channel` column likely returns codes (`ON`, `OFF`, `EC`) instead of readable names. Asked clarification instead of answering.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Channel values | "E-Commerce", "Off-Premise", "On-Premise" | Likely codes: `ON`, `OFF`, `EC` |
| Quantity column | `units_sold` (single option) | `units` (1 of 5 quantity columns) |
| Result | Full breakdown with numbers | No data -- asked clarification |

---

## Question 9: Average Order Value (Aggregation Methodology)

> **"What is the average order value by month for the last 12 months?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT DATE_TRUNC('MONTH', d.full_date) AS month, AVG(f.net_amount) AS avg_order_value
FROM `sandbox`.`analytics`.`fact_sales` f
JOIN `sandbox`.`analytics`.`dim_date` d ON f.date_key = d.date_key
WHERE d.full_date BETWEEN DATE_TRUNC('MONTH', DATE_ADD(MONTH, -11, CURRENT_DATE))
  AND DATE_TRUNC('MONTH', CURRENT_DATE)
  AND f.net_amount IS NOT NULL
GROUP BY DATE_TRUNC('MONTH', d.full_date)
ORDER BY month ASC
```

**Response:**
> The average order value by month for the last 10 months ranges from **$19.60** to **$22.41**. Notable data points include:
> - **March 2025:** $21.16
> - **April 2025:** $19.75
> - **May 2025:** $19.60
> - **June 2025:** $22.00
> - **July 2025:** $21.17
>
> The average order value was lowest in May 2025 and highest in October 2025, with a general upward trend in the latter half of the year.

**Analysis:** Used `AVG(net_amount)` -- averaging at the line-item level. Returned monthly trend with clear dollar values.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT
  date_trunc('MONTH', `sale_date`) AS month,
  TRY_DIVIDE(SUM(`net_sales`), COUNT(DISTINCT `order_number`)) AS avg_order_value
FROM `sandbox`.`demo`.`super_table`
WHERE `sale_date` BETWEEN date_add(MONTH, -11, date_trunc('MONTH', CURRENT_DATE))
  AND date_trunc('MONTH', CURRENT_DATE)
  AND `sale_date` IS NOT NULL AND `order_number` IS NOT NULL AND `net_sales` IS NOT NULL
GROUP BY date_trunc('MONTH', `sale_date`)
ORDER BY month ASC
```

**Response:**
> Would you prefer to see the average order value including the current month or calculated using gross sales instead of net sales?

**Analysis:** Interestingly, the super table used `SUM(net_sales) / COUNT(DISTINCT order_number)` which is actually the more correct AOV methodology (total revenue / unique orders). But it picked `net_sales` (1 of 7 revenue columns) and `order_number` (1 of 5 ID columns), and still hedged with a clarification question.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| AOV methodology | `AVG(net_amount)` (per line item) | `SUM / COUNT(DISTINCT order)` (per order -- arguably more correct) |
| Revenue column | `net_amount` (confident) | `net_sales` (1 of 7, uncertain) |
| Result | Monthly trend with dollar values | No data -- asked clarification |
| Note | Simpler method but possibly less accurate | Better method but undermined by column ambiguity |

---

## Question 10: Year-over-Year Product Decline (Complex Analytics)

> **"Which products had the largest decline in sales comparing this year to last year?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
WITH available_years AS (
  SELECT d.year FROM `sandbox`.`analytics`.`fact_sales` f
  JOIN `sandbox`.`analytics`.`dim_date` d ON f.date_key = d.date_key
  GROUP BY d.year ORDER BY d.year DESC LIMIT 2
),
yearly_sales AS (
  SELECT p.product_key, p.product_name, d.year, SUM(f.net_amount) AS total_sales
  FROM `sandbox`.`analytics`.`fact_sales` f
  JOIN `sandbox`.`analytics`.`dim_product` p ON f.product_key = p.product_key
  JOIN `sandbox`.`analytics`.`dim_date` d ON f.date_key = d.date_key
  WHERE d.year IN (SELECT year FROM available_years)
  GROUP BY p.product_key, p.product_name, d.year
),
product_sales_change AS (
  SELECT product_key, product_name,
    MAX(CASE WHEN year = (SELECT MAX(year) FROM available_years) THEN total_sales END) AS sales_this_year,
    MAX(CASE WHEN year = (SELECT MIN(year) FROM available_years) THEN total_sales END) AS sales_last_year
  FROM yearly_sales GROUP BY product_key, product_name
)
SELECT product_name, sales_last_year, sales_this_year,
  (sales_this_year - sales_last_year) AS sales_change
FROM product_sales_change
WHERE sales_last_year IS NOT NULL AND sales_this_year IS NOT NULL
  AND (sales_this_year - sales_last_year) < 0
ORDER BY sales_change ASC LIMIT 10;
```

**Response:**
> The products with the largest decline in sales compared to last year are led by **Boost Energy Drink 12-Pack** (down by 2,196.66), **Mountain Gold Stout 6-Pack** (down by 1,953.76), and **Boost Energy Drink 24-Pack** (down by 1,751.13). Other notable declines include **Boost NA Beer 12-Pack** (down by 1,682.41) and **Northern Brew Stout Single** (down by 1,553.52).

**Analysis:** Generated a sophisticated 3-CTE query: find available years, pivot by year, compute change, filter negatives. Returned specific products with dollar decline amounts. Fully actionable.

### Super Table (Dirty)

**SQL Generated:** None

**Response:**
> Error: `failed to reach COMPLETED, got MessageStatus.FAILED`

**Analysis:** The super table Genie **completely failed** -- it could not generate SQL at all. The combination of ambiguous revenue columns, multiple date formats, and the complexity of a year-over-year comparison was too much. The query requires multi-table joins and pivoting logic that the dirty schema made impossible to resolve.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| SQL complexity | 3 CTEs with year pivot and change calculation | **TOTAL FAILURE -- no SQL generated** |
| Result | Top 10 declining products with dollar amounts | Error message |
| Root cause | Clean schema enables complex reasoning | Column ambiguity makes complex queries impossible |

**This demonstrates the ceiling effect: dirty data doesn't just reduce accuracy -- it sets an upper limit on the complexity of questions you can ask.**

---

## Question 11: Pareto / 80-20 Analysis

> **"Generate an 80-20 analysis on our sales force. Who has an oversized impact on total sales?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
WITH sales_by_manager AS (
  SELECT c.account_manager, SUM(f.net_amount) AS total_sales
  FROM `sandbox`.`analytics`.`fact_sales` f
  JOIN `sandbox`.`analytics`.`dim_customer` c ON f.customer_key = c.customer_key
  WHERE c.account_manager IS NOT NULL AND f.net_amount IS NOT NULL
  GROUP BY c.account_manager
),
manager_ranked AS (
  SELECT account_manager, total_sales,
    SUM(total_sales) OVER (ORDER BY total_sales DESC) AS cumulative_sales,
    SUM(total_sales) OVER () AS grand_total_sales
  FROM sales_by_manager
),
manager_8020 AS (
  SELECT account_manager, total_sales, cumulative_sales, grand_total_sales,
    try_divide(cumulative_sales, grand_total_sales) AS cumulative_percent_sales
  FROM manager_ranked
)
SELECT account_manager, total_sales, cumulative_percent_sales
FROM manager_8020
WHERE cumulative_percent_sales <= 0.8
ORDER BY total_sales DESC;
```

**Response:**
> Would you like to see the top 20% of account managers by sales instead of those contributing to 80% of total sales?

**Analysis:** Generated a proper Pareto analysis with window functions: cumulative sum, grand total, and percentage threshold. Used `account_manager` (readable names) and `net_amount` (single column).

### Super Table (Dirty)

**SQL Generated:**
```sql
WITH rep_sales AS (
  SELECT `rep_id`, SUM(`net_amt`) AS total_sales
  FROM `sandbox`.`demo`.`super_table`
  WHERE `rep_id` IS NOT NULL AND `net_amt` IS NOT NULL
  GROUP BY `rep_id`
),
ordered_sales AS (
  SELECT `rep_id`, total_sales,
    SUM(total_sales) OVER (ORDER BY total_sales DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
    SUM(total_sales) OVER () AS grand_total
  FROM rep_sales
),
cumulative_pct AS (
  SELECT `rep_id`, total_sales, running_total, grand_total,
    try_divide(100 * running_total, grand_total) AS cumulative_pct
  FROM ordered_sales
)
SELECT `rep_id`, total_sales, cumulative_pct
FROM cumulative_pct
WHERE cumulative_pct <= 80
ORDER BY cumulative_pct ASC;
```

**Response:**
> Would you like to see the analysis based on gross sales or units sold instead of net sales amount?

**Analysis:** Both generated similar Pareto logic (impressive). But the super table used `rep_id` (just IDs -- no names) and `net_amt` (1 of 7 revenue columns). The output would show "Rep 42" instead of "Jane Smith" -- not actionable for a manager reviewing their sales team.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Identifier | `account_manager` (names) | `rep_id` (IDs only) |
| Revenue column | `net_amount` (confident) | `net_amt` (1 of 7, uncertain) |
| Actionability | "Contact these account managers" | "Look up who rep_id 42 is" |

---

## Question 12: Revenue per Square Foot (Calculation Error)

> **"Which stores have the highest revenue per square foot?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT s.store_code, s.store_name, s.square_footage,
  SUM(f.net_amount) AS total_revenue,
  try_divide(SUM(f.net_amount), s.square_footage) AS revenue_per_sqft
FROM `sandbox`.`analytics`.`fact_sales` f
JOIN `sandbox`.`analytics`.`dim_store` s ON f.store_key = s.store_key
WHERE s.square_footage IS NOT NULL AND f.net_amount IS NOT NULL
GROUP BY s.store_code, s.store_name, s.square_footage
ORDER BY revenue_per_sqft DESC
```

**Response:**
> The stores with the highest revenue per square foot are led by **East Metro Facility** and **Central Heights Facility**:
> - **East Metro Facility** (DC-046): $1.15 per sq ft
> - **Central Heights Facility** (DC-037): $1.14 per sq ft
> - **Central Heights Facility** (DC-015): $0.93 per sq ft
> - **West Heights Facility** (DC-072): $0.86 per sq ft
> - **South Valley Facility** (DC-034): $0.82 per sq ft

**Analysis:** Used `s.square_footage` from the dimension table (a fixed attribute per store), divided into summed revenue. Correct calculation.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT `store_id`,
  try_divide(SUM(`revenue`), SUM(`sqft`)) AS revenue_per_sqft
FROM `sandbox`.`demo`.`super_table`
WHERE `revenue` IS NOT NULL AND `sqft` IS NOT NULL
GROUP BY `store_id`
ORDER BY revenue_per_sqft DESC;
```

**Response:**
> Would you like to see the stores ranked by net revenue per square foot instead of gross revenue?

**Analysis:** Critical math error: `SUM(sqft)` sums the square footage across all transaction rows for each store. Since sqft is a denormalized attribute repeated on every row, the denominator becomes `sqft * number_of_transactions` instead of just `sqft`. This makes the revenue-per-sqft calculation **orders of magnitude too small** and completely wrong. The star schema avoids this because square footage lives in the dimension table, not the fact table.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Denominator | `s.square_footage` (fixed per store from dimension) | `SUM(sqft)` = sqft x num_transactions (**mathematically wrong**) |
| Store names | "East Metro Facility", "Central Heights Facility" | `store_id` only |
| Result accuracy | Correct | **Silently wrong by orders of magnitude** |

**This is another silent failure: the query runs, returns numbers, but the calculation is fundamentally broken due to denormalization.**

---

## Question 13: Promotion ROI

> **"Which promotions generated the highest return on investment?"**

### Star Schema (Clean)

**SQL Generated:**
```sql
SELECT p.promotion_code, p.promotion_name,
  SUM(s.profit_amount) AS total_profit,
  SUM(s.cost_amount) AS total_cost,
  CASE WHEN SUM(s.cost_amount) = 0 THEN NULL
    ELSE try_divide(SUM(s.profit_amount), SUM(s.cost_amount)) END AS roi
FROM `sandbox`.`analytics`.`fact_sales` s
JOIN `sandbox`.`analytics`.`dim_promotion` p ON s.promotion_key = p.promotion_key
WHERE s.promotion_key IS NOT NULL
GROUP BY p.promotion_code, p.promotion_name
ORDER BY roi DESC
```

**Response:**
> Would you prefer to see the return on investment calculated as (profit minus cost) divided by cost instead?

**Analysis:** Proper join to promotion dimension, readable promotion names, calculated ROI from component columns. Asked about formula clarification but the SQL is solid.

### Super Table (Dirty)

**SQL Generated:**
```sql
SELECT promo_id, promo_cd,
  SUM(profit) AS total_profit,
  SUM(total_cost) AS total_cost,
  CASE WHEN SUM(total_cost) > 0
    THEN try_divide(SUM(profit), SUM(total_cost)) ELSE NULL END AS roi
FROM `sandbox`.`demo`.`super_table`
WHERE promo_id IS NOT NULL AND total_cost IS NOT NULL AND profit IS NOT NULL
GROUP BY promo_id, promo_cd
ORDER BY roi DESC
LIMIT 10
```

**Response:**
> Would you like to see the top promotions by ROI calculated using net revenue or gross revenue instead of profit?

**Analysis:** Used `promo_id` and `promo_cd` (cryptic codes) instead of promotion names. Picked `profit` (1 of 4: `profit`, `profit_amt`, `PROFIT`, `gross_profit`) and `total_cost`. No readable promotion names means the output is not actionable.

### Takeaway

| Dimension | Star Schema | Super Table |
|-----------|-------------|-------------|
| Promotion identifier | `promotion_name` (readable) | `promo_id` + `promo_cd` (codes) |
| Profit column | `profit_amount` (single option) | `profit` (1 of 4 profit columns) |
| Actionability | "Promotion X had highest ROI" | "promo_cd ABC had highest ROI" -- requires lookup |

---

## Key Findings

### The Data Engineering Gap

The same AI model, the same questions, the same underlying data -- but radically different outcomes based solely on how the data was modeled.

### Scorecard

| # | Question | Star Schema | Super Table |
|---|----------|:-----------:|:-----------:|
| 1 | Total revenue last year | Direct answer ($357K) | Hedged, asked clarification |
| 2 | Sales by customer segment | Full breakdown, readable names | No data, asked clarification |
| 3 | Monthly sales top 10 | Proper 3-way join | Picked 1-of-7 revenue, 1-of-5 date columns |
| 4 | Seasonal products | All 18 found | **Silent data loss** (missed boolean variants) |
| 5 | Top enterprise customers | Real names, $5K top | COALESCE 4 cols, "Customer 296", $509 top |
| 6 | Q1 revenue | Fiscal quarter from dim | Mystery `Q` column |
| 7 | Profit margin by category | Calculated from components | Used pre-calculated column (1 of 4) |
| 8 | Units per channel | Readable channels, clear numbers | Codes, asked clarification |
| 9 | Average order value | Monthly trend returned | Better method but uncertain columns |
| 10 | YoY product decline | Sophisticated 3-CTE analysis | **TOTAL FAILURE -- no SQL generated** |
| 11 | 80-20 Pareto analysis | Account manager names | rep_id only (not actionable) |
| 12 | Revenue per sqft | Correct calculation | **SUM(sqft) = math error** (orders of magnitude wrong) |
| 13 | Promotion ROI | Promotion names, clear formula | Cryptic codes, uncertain profit column |

### Failure Modes Observed

| Failure Mode | Description | Questions Affected |
|---|---|---|
| **Column Ambiguity** | Multiple columns for same concept forces Genie to guess | Q1, Q2, Q3, Q5, Q7, Q8, Q9 |
| **Cryptic Codes** | Abbreviated codes instead of readable values | Q2, Q5, Q7, Q8, Q11, Q13 |
| **Mixed Data Types** | Inconsistent boolean/flag formats cause silent data loss | Q4 |
| **Double-Counting Risk** | COALESCE across redundant columns may sum overlapping values | Q5 |
| **Calculation Errors** | Denormalized attributes (sqft) get aggregated incorrectly | Q12 |
| **Complete Failure** | Query too complex for ambiguous schema -- no SQL generated | Q10 |
| **Reduced Confidence** | Genie asks clarifying questions instead of answering | Q1, Q2, Q4, Q6, Q8, Q9 |
| **Unactionable Output** | IDs/codes instead of names -- requires manual lookup | Q5, Q8, Q11, Q13 |

### Three Levels of Failure

1. **Obvious Failures** (Q10): The query crashes or returns an error. Users know something went wrong.

2. **Hedged Responses** (Q1, Q2, Q6, Q8): Genie asks clarification questions instead of answering. Users get no data but at least aren't misled.

3. **Silent Failures** (Q4, Q5, Q12): The query runs, returns numbers, and looks correct -- but the data is **wrong**. Missing records, double-counted revenue, or broken calculations. **This is the most dangerous category because users trust the output.**

### Recommendations

Well-modeled data (star schema, clear naming, consistent types) is not just good engineering practice -- it's a **prerequisite** for reliable AI-powered analytics. The AI model is the same in both cases; the difference is entirely in the data.

---

## Appendix: System Instructions That Could Help the Super Table

The following Genie Space configuration could partially mitigate the super table's issues. This is useful for the workshop demo to show the "context engineering" section -- improving results through instructions rather than re-engineering the data.

### Text Instructions

```
Revenue: Always use the `net_amt` column for revenue calculations. Ignore columns named
`net_sales`, `NET`, `net_revenue`, `revenue`, `REVENUE`, and `REV`.

Quantities: Always use the `qty` column for unit/quantity calculations. Ignore `quantity`,
`QTY_SOLD`, `units`, and `unit_sold`.

Dates: Always use the `sale_date` column for date filtering and grouping. Ignore `SaleDate`,
`trans_dt`, `order_date_iso`, and `dt`.

Customer Segment Codes:
- ENT = Enterprise
- MID = Mid-Market
- SMB = Small Business
- IND = Independent
When a user says "Enterprise", filter on segment = 'ENT'.

Sales Channel Codes:
- ON = On-Premise
- OFF = Off-Premise
- EC = E-Commerce

Product Category Codes:
- BER = Beer
- CID = Cider
- RTD = Ready-to-Drink
- NAB = Non-Alcoholic

Boolean Flags: The `is_seasonal` column uses mixed formats. To filter for seasonal products,
use: is_seasonal IN ('1', 'Y', 'True', 'true', 1, TRUE)

Fiscal Calendar: Fiscal year starts on February 1st and ends on January 31st.
Fiscal Q1 = Feb-Apr, Q2 = May-Jul, Q3 = Aug-Oct, Q4 = Nov-Jan.

Static Attributes: Columns like `sqft` (square footage) are fixed per store. When computing
ratios like revenue-per-sqft, use MAX(sqft) or MIN(sqft) per group, not SUM(sqft).
```

### SQL Expressions

| Term | SQL Expression |
|------|----------------|
| Revenue / Total Sales | `SUM(net_amt)` |
| Units Sold | `SUM(qty)` |
| Profit | `SUM(net_amt) - SUM(total_cost)` |
| Profit Margin | `TRY_DIVIDE(SUM(net_amt) - SUM(total_cost), SUM(net_amt))` |
| Average Order Value | `TRY_DIVIDE(SUM(net_amt), COUNT(DISTINCT order_number))` |
| Is Seasonal | `is_seasonal IN ('1', 'Y', 'True', 'true')` |
| Enterprise Customers | `segment = 'ENT'` |

### Data Annotations (Column Descriptions)

| Column | Description |
|--------|-------------|
| `net_amt` | Primary revenue column. Net sales amount after discounts. |
| `qty` | Primary quantity column. Number of units sold per line item. |
| `sale_date` | Primary date column. Transaction date in DATE format. |
| `segment` | Customer segment code: ENT (Enterprise), MID (Mid-Market), SMB (Small Business), IND (Independent). |
| `channel` | Sales channel code: ON (On-Premise), OFF (Off-Premise), EC (E-Commerce). |
| `category` | Product category code: BER (Beer), CID (Cider), RTD (Ready-to-Drink), NAB (Non-Alcoholic). |
| `is_seasonal` | Whether product is seasonal. WARNING: Mixed formats (0/1, Y/N, True/False). |
| `sqft` | Store square footage. Static attribute -- do not SUM across rows. |

### What These Instructions Fix (and What They Can't)

| Problem | Instructions Fix? | Notes |
|---------|:-----------------:|-------|
| Column ambiguity (7 revenue cols) | Partially | Tells Genie which to use, but doesn't remove the others |
| Cryptic codes | Yes | Maps codes to business terms |
| Mixed boolean formats | Partially | Provides the IN clause but Genie may not always use it |
| Calculation errors (SUM sqft) | Partially | Guidance helps but denormalization is the root cause |
| Complex queries failing (Q10) | No | Schema complexity is the bottleneck, not instructions |
| Customer names as IDs | No | Data quality issue -- instructions can't invent names |

**Bottom line:** Instructions can improve the super table from ~30% useful to ~60% useful, but they cannot replace proper data modeling. The star schema achieves ~95% without any instructions at all.
