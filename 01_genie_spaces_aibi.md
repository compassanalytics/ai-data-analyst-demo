# Databricks AI/BI Genie Spaces - Comprehensive Research Document

**Research Date:** January 26, 2026
**Purpose:** Workshop Demo Preparation

---

## Table of Contents

1. [Overview: What is AI/BI Genie Spaces?](#1-overview-what-is-aibi-genie-spaces)
2. [Setting Up Genie Spaces](#2-setting-up-genie-spaces)
3. [Writing System Prompts / Instructions](#3-writing-system-prompts--instructions)
4. [Custom SQL Expressions and Knowledge Store](#4-custom-sql-expressions-and-knowledge-store)
5. [Best Practices for Non-Technical Demos](#5-best-practices-for-non-technical-demos)
6. [Free Tier / Community Edition Availability](#6-free-tier--community-edition-availability)
7. [Limitations and Considerations](#7-limitations-and-considerations)
8. [Sources](#8-sources)

---

## 1. Overview: What is AI/BI Genie Spaces?

### Core Concept

AI/BI Genie is a Databricks feature that provides a **conversational interface for querying data using natural language**. It enables business and non-technical users to access, analyze, and visualize data without relying on expert analysts or writing SQL queries.

### How It Works

Genie uses a **compound AI system** (not a single LLM) that:
- Interprets business questions
- Selects relevant table/column names and descriptions from annotated metadata
- Converts natural language questions into equivalent SQL queries
- Returns generated queries with results tables and visualizations

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Self-Service Analytics** | Business users can get insights independently without SQL knowledge |
| **Faster Decision Making** | Reduces dependency on data analysts for ad-hoc questions |
| **Transparency** | "Thinking steps" explain SQL logic in plain language, building trust |
| **Continuous Improvement** | User feedback refines responses over time |
| **Integration Ready** | Works with Microsoft Teams, Slack, Glean via APIs |

### General Availability Status

AI/BI Genie is **Generally Available (GA)** as of 2024, with significant feature enhancements released throughout 2025.

---

## 2. Setting Up Genie Spaces

### Prerequisites

| Requirement | Details |
|------------|---------|
| **Data Registration** | Data must be registered to **Unity Catalog** |
| **SQL Warehouse** | Requires **Pro** or **Serverless SQL warehouse** |
| **Permissions** | Databricks SQL workspace entitlement |
| **Data Access** | SELECT privileges on data used in the space |
| **Partner AI Features** | Must be enabled at account and workspace levels |

### Step-by-Step Setup

#### 1. Create a New Genie Space

1. Click **Genie** in the sidebar
2. Click **New** in the upper-right corner
3. Choose data sources (tables/views from Unity Catalog)
4. Click **Create**

#### 2. Connect Data Sources

- Add up to **25 tables or views** per Genie space
- If you need more tables, **pre-join related tables into views** before adding
- Use metric views for pre-defined metrics and aggregations

#### 3. Configure the SQL Warehouse

- Assign a Pro or Serverless SQL warehouse
- Users interacting with the space need **CAN USE** access to the assigned warehouse

### Dashboard Integration (Automatic Creation)

When you create an AI/BI Dashboard, Databricks can **automatically create a companion Genie space**:

1. When publishing a dashboard, toggle **Enable Genie**
2. Databricks generates a Genie space based on dashboard datasets
3. Users see an "Ask Genie" button on published dashboards

**Key characteristics of companion spaces:**
- Don't appear in file browser or Genie listing
- Auto-update when dashboard is republished
- Inherit dashboard permissions
- Support embedded credentials (October 2025+)

### API-Based Creation

```http
POST /api/2.0/genie/spaces
Host: <DATABRICKS_INSTANCE>
Authorization: Bearer <token>

{
  "description": "Space for analyzing sales performance",
  "parent_path": "/Workspace/Users/<username>",
  "title": "Sales Analytics Space",
  "warehouse_id": "<warehouse-id>",
  "serialized_space": "{...configuration JSON...}"
}
```

---

## 3. Writing System Prompts / Instructions

### Instruction Hierarchy (Priority Order)

1. **SQL Expressions** - Highest priority for business terms, metrics, filters
2. **Example SQL Queries** - For complex multi-part questions
3. **Text Instructions** - General guidance that doesn't fit structured definitions

### Adding Text Instructions

Navigate to **Configure > Instructions** in your Genie space.

**Best Practices:**

```markdown
## Good Instructions

- "All monetary values are in USD"
- "Use fiscal quarters (Q1 = Feb-Apr, Q2 = May-Jul, etc.)"
- "Active customers are those with orders in the last 90 days"

## Bad Instructions (Too Vague)

- "Be helpful"
- "Answer questions accurately"
- "Use the right tables"
```

### Sample Questions

Add sample questions to guide users and help Genie learn patterns:

```json
{
  "sample_questions": [
    {"question": ["What were total sales last month?"]},
    {"question": ["Show top 10 customers by revenue"]},
    {"question": ["Compare sales by region for Q1 vs Q2"]},
    {"question": ["Which products have the highest return rate?"]},
    {"question": ["Show monthly revenue trend for the past year"]}
  ]
}
```

### Example SQL Queries

Example SQL teaches Genie how to approach common question formats:

```sql
-- Return our current total open pipeline by region.
-- Opportunities are only considered pipelines if they are tagged as such.
SELECT
  a.region__c AS `Region`,
  sum(o.amount) AS `Open Pipeline`
FROM
  sales.crm.opportunity o
  JOIN sales.crm.accounts a ON o.accountid = a.id
WHERE
  o.forecastcategory = 'Pipeline' AND
  o.stagename NOT ILIKE '%closed%'
GROUP BY ALL;
```

### Language Considerations

- Genie supports multiple languages (Portuguese, French, etc.)
- **Note:** The underlying system prompts are in English
- Responses might occasionally appear in English due to the system framework

---

## 4. Custom SQL Expressions and Knowledge Store

### What is the Knowledge Store?

A **collection of curated semantic definitions** that improves Genie's understanding of your data. It includes:

- Space-level metadata customization
- Join relationships
- SQL expressions (measures, filters, dimensions)
- Prompt matching for entity recognition

**All configurations are scoped to your Genie space** and don't affect Unity Catalog metadata.

### SQL Expression Types

#### 1. Measures (KPIs and Metrics)

```sql
-- Example: Gross Margin
Name: gross_margin
Code: (SUM(revenue) - SUM(cost)) / SUM(revenue) * 100
Synonyms: margin, profit margin, GP%
Instructions: Use for profitability analysis. Returns percentage.
```

#### 2. Filters (Boolean Conditions)

```sql
-- Example: Recent Sales
Name: recent_sales
Code: order_date >= DATE_SUB(CURRENT_DATE(), 30)
Synonyms: last 30 days, recent orders, new sales
Instructions: Filters to orders within the last 30 days.
```

#### 3. Dimensions (Grouping Attributes)

```sql
-- Example: Fiscal Quarter
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

### Defining Join Relationships

Define joins locally within the Knowledge Store:

1. Select left and right tables from dropdown menus
2. Enter join condition (e.g., `accounts.id = opportunity.accountid`)
3. Choose relationship type: **many-to-one**, **one-to-many**, or **one-to-one**

**Limit:** Up to 200 SQL snippets and JOIN relationships per Genie space (increased in 2025)

### Prompt Matching Features

| Feature | Description | Limits |
|---------|-------------|--------|
| **Format Assistance** | Representative values showing data formats | - |
| **Entity Matching** | Curated distinct values for categorical data | 120 columns, 1,024 values each, 127 chars max |

These help Genie match user terminology to actual data values, correcting misspellings and phrasing variations.

### Knowledge Extraction (2025 Feature)

When users give a **thumbs-up** to a generated query, Genie can:
1. Analyze the successful interaction
2. Propose knowledge snippets
3. Space authors review and approve before adding to Knowledge Store

---

## 5. Best Practices for Non-Technical Demos

### Demo Preparation Checklist

- [ ] **Start Small**: Use 5 or fewer well-documented tables
- [ ] **Clear Naming**: Ensure column names are business-friendly
- [ ] **Pre-define Metrics**: Use SQL expressions for key KPIs
- [ ] **Add Sample Questions**: Guide users with common queries
- [ ] **Test Thoroughly**: Run benchmark questions before the demo

### Demo Script Recommendations

#### Opening Questions (Simple)

```
"What were our total sales last month?"
"How many customers do we have?"
"Show me the top 5 products by revenue"
```

#### Follow-up Questions (Showing Natural Language Power)

```
"Break that down by region"
"Now filter to only enterprise customers"
"What was it compared to the same period last year?"
```

#### Visualization Capabilities

```
"Show me a trend chart of monthly revenue"
"Create a pie chart of sales by category"
"Plot customer growth over the past year"
```

### Tips for Non-Technical Audiences

1. **Emphasize No SQL Required**: Users type plain English questions
2. **Show "Thinking Steps"**: Demonstrates transparency and builds trust
3. **Highlight Self-Service**: No waiting for data team requests
4. **Demonstrate Iteration**: Show follow-up questions refining analysis
5. **Show Business Integrations**: Slack/Teams integration possibilities

### Data Preparation for Demos

| Action | Why |
|--------|-----|
| Pre-join complex tables into views | Simplifies queries, improves accuracy |
| Add descriptive column comments | Helps Genie understand context |
| Include sample values in metadata | Improves entity matching |
| Remove sensitive/irrelevant columns | Reduces noise and token usage |

---

## 6. Free Tier / Community Edition Availability

### Databricks Free Edition (Current Option)

**Good news:** Genie Spaces ARE available on Databricks Free Edition.

| Feature | Free Edition Support |
|---------|---------------------|
| **AI/BI Genie** | YES |
| **Dashboards** | YES |
| **SQL and Python** | YES |
| **Unity Catalog** | YES |
| **Model Serving** | YES |
| **Assistant** | YES |

### Free Edition Details

- **Launch Date:** June 2025
- **Cost:** Free, no credit card required
- **Expiration:** Access doesn't expire (inactive accounts may be deactivated after prolonged inactivity)
- **Target Users:** Students, hobbyists, aspiring data/AI professionals
- **Not for:** Commercial use

### Community Edition Status

**Important:** Community Edition is being **deprecated**. Databricks recommends migrating to Free Edition as soon as possible.

Free Edition runs on the modern serverless platform with:
- Better ease of use
- Improved reliability
- Expanded feature set

### Genie API Free Tier

When accessing Genie spaces via API:
- **Rate Limit:** Best effort 5 questions per minute per workspace
- **Status:** Public Preview

---

## 7. Limitations and Considerations

### Hard Limits

| Limit | Value |
|-------|-------|
| Tables/views per Genie space | 25 |
| SQL snippets and JOIN relationships | 200 |
| Entity matching columns | 120 |
| Values per entity matching column | 1,024 |
| Characters per entity value | 127 |
| Conversations per space | 10,000 |
| Messages per conversation | 10,000 |
| CSV download size | ~1 GB |

### Throughput Limits

| Access Method | Rate Limit |
|---------------|------------|
| Databricks UI | 20 questions/minute/workspace |
| Genie API (Free Tier) | 5 questions/minute/workspace (best effort) |

### Token Limits

- Text instructions and metadata are converted to tokens
- **Warning appears** when approaching token limit
- **Quality degrades** if important context is filtered out
- **Messages blocked** when token limit exceeded

**Mitigation:** Remove unnecessary columns, hide unneeded data, use views

### Permission Requirements

| Action | Required Permission |
|--------|-------------------|
| Create/edit Genie space | CAN EDIT |
| Manage Genie space | CAN MANAGE (automatic for creators) |
| Add tags | CAN EDIT + ASSIGN (for governed tags) |
| Use Genie space | CAN USE on assigned SQL warehouse |

### Language Limitations

- Non-English support available (Portuguese, French, etc.)
- System prompts are English-based
- Responses may occasionally appear in English

### What Genie Cannot Do

- Cannot edit instructions for auto-generated dashboard companion spaces
- Cannot search Genie spaces by tags
- Does not support file uploads without account team enablement (Public Preview)
- May struggle with very complex multi-part questions without proper SQL examples

### Security Considerations

- Customer-managed key support available (April 2025+)
- Embedded credentials support for dashboard companion spaces
- Permissions mirror underlying data access through Unity Catalog

---

## 8. Sources

### Official Databricks Documentation

- [What is an AI/BI Genie space (AWS)](https://docs.databricks.com/aws/en/genie/)
- [Set up and manage an AI/BI Genie space (AWS)](https://docs.databricks.com/aws/en/genie/set-up)
- [Curate an effective Genie space (Best Practices)](https://docs.databricks.com/aws/en/genie/best-practices)
- [Build a knowledge store for more reliable Genie spaces](https://docs.databricks.com/aws/en/genie/knowledge-store)
- [Use a Genie space to explore business data](https://docs.databricks.com/aws/en/genie/talk-to-genie)
- [Genie spaces with dashboards](https://docs.databricks.com/aws/en/dashboards/genie-spaces)
- [AI/BI release notes 2025](https://docs.databricks.com/aws/en/ai-bi/release-notes/2025)
- [Troubleshoot Genie spaces](https://docs.databricks.com/aws/en/genie/troubleshooting)

### Azure Databricks Documentation

- [What is an AI/BI Genie space (Azure)](https://learn.microsoft.com/en-us/azure/databricks/genie/)
- [Set up and manage an AI/BI Genie space (Azure)](https://learn.microsoft.com/en-us/azure/databricks/genie/set-up)
- [Curate an effective Genie space (Azure)](https://learn.microsoft.com/en-us/azure/databricks/genie/best-practices)
- [Build a knowledge store (Azure)](https://learn.microsoft.com/en-us/azure/databricks/genie/knowledge-store)

### Databricks Blog Posts

- [AI/BI Genie is now Generally Available](https://www.databricks.com/blog/aibi-genie-now-generally-available)
- [What's New in AI/BI - October 2025 Roundup](https://www.databricks.com/blog/whats-new-aibi-october-2025-roundup)

### Product Pages

- [GenAI-Powered Business Intelligence (Genie Product Page)](https://www.databricks.com/product/business-intelligence/ai-bi-genie)
- [Free Edition (Replacing Community Edition)](https://www.databricks.com/learn/free-edition)

### Community Resources

- [Free Edition FAQs - Databricks Community](https://community.databricks.com/t5/databricks-university-alliance/free-edition-frequently-asked-questions-faqs-consolitated/ta-p/128500)
- [Best Practices for AI/BI Genie Spaces (Medium)](https://medium.com/dbsql-sme-engineering/best-practices-for-ai-bi-genie-spaces-on-databricks-6f101612c792)

---

## Confidence Assessment

| Topic | Confidence | Notes |
|-------|------------|-------|
| Core Genie features | **High** | Well-documented across multiple official sources |
| Setup process | **High** | Consistent across AWS/Azure/GCP documentation |
| Knowledge Store / SQL expressions | **High** | Detailed official documentation available |
| Free Edition availability | **High** | Confirmed in multiple official sources |
| Limitations and limits | **High** | Documented in official release notes |
| Best practices | **High** | Multiple official and community sources |
| 2025 feature updates | **Medium-High** | Based on release notes, some features in Public Preview |

---

## Recommendations for Workshop Demo

1. **Use Free Edition** if a paid workspace isn't available - Genie is supported
2. **Prepare a focused dataset** with 3-5 well-documented tables
3. **Pre-define 5-10 sample questions** covering common use cases
4. **Add SQL expressions** for your key business metrics
5. **Test all demo questions** multiple times before the workshop
6. **Have backup questions** in case primary ones don't work as expected
7. **Show the "thinking steps"** to demonstrate transparency
8. **Demonstrate iteration** with follow-up questions to show conversational capability
9. **Consider dashboard integration** for a more complete AI/BI story
