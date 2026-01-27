# Databricks AI/BI Workshop - Complete Research Document

**Research Date:** January 26, 2026
**Workshop:** DBX x Compass AI Workshop - Building AI-Powered Data Analysts
**Authors:** Compass Analytics Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Critical Findings for Demo Planning](#critical-findings-for-demo-planning)
3. [Part 1: Genie Spaces & AI/BI](#part-1-genie-spaces--aibi)
4. [Part 2: Databricks Agent Framework & MCP](#part-2-databricks-agent-framework--mcp)
5. [Part 3: LangGraph + Databricks Integration](#part-3-langgraph--databricks-integration)
6. [Part 4: Free Tier & Workshop Setup](#part-4-free-tier--workshop-setup)
7. [Part 5: AI Data Analyst Enterprise Patterns](#part-5-ai-data-analyst-enterprise-patterns)
8. [Appendix: All Sources](#appendix-all-sources)

---

# Executive Summary

This document consolidates research on Databricks agentic capabilities for the DBX x Compass AI Workshop. The workshop aims to demonstrate how to build AI-powered data analysts using Databricks, targeting 40-50 participants with a mix of business and technical personas.

## Key Research Topics

| Topic | Key Takeaway |
|-------|--------------|
| Genie Spaces & AI/BI | Available on Free Edition; 25 tables max; excellent for non-technical demos |
| Mosaic AI Agent Framework & MCP | GA with native MCP support; Agent Bricks for no-code agent creation |
| LangGraph + Databricks Integration | Full notebook patterns; GenieAgent + supervisor architecture |
| Free Tier & Workshop Setup | Community Edition retired Jan 2026; use Free Edition or Trial |
| Enterprise AI Analyst Patterns | TAG architecture; 6% real-world vs 86% benchmark accuracy gap |

---

# Critical Findings for Demo Planning

## 1. Environment Strategy (40-50 Participants)

**IMPORTANT:** Databricks Community Edition was **retired January 1, 2026**.

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| **Free Edition** (each participant) | No cost, includes Genie | No centralized control, self-registration required |
| **14-Day Trial** | $400 credits, full features | Requires work email for full access |
| **Enterprise Credits** | Managed environment | Requires Databricks coordination |

**Recommendation:** Coordinate with Databricks (Vincent/Felix) to provision workshop-specific environments or use CloudLabs for managed provisioning.

---

## 2. Two-Stage Demo Architecture

### Stage 1: Non-Technical (Genie Spaces) - Business Persona

**What Genie Provides:**
- Conversational natural language to SQL
- "Thinking steps" transparency (great for trust-building)
- System prompts + custom SQL expressions
- Dashboard integration

**Demo Flow:**
1. Connect to sample dataset (TPC-H or custom Molson-style)
2. Define system prompt with business context
3. Create SQL expressions for key KPIs
4. Live Q&A with natural language queries
5. Show thinking steps to demystify AI

**Constraints:**
- 25 tables/views max per space
- 20 questions/minute via UI
- Pre-test benchmark questions before demo

### Stage 2: Technical (LangGraph + Genie API) - Technical Persona

**Architecture:**
```
+-----------------+
|   LangGraph     |
|   Supervisor    |
+--------+--------+
         |
    +----+----+
    v         v
+-------+ +-------------+
| Genie | |VectorSearch |
| Agent | |   Agent     |
+-------+ +-------------+
```

**Key Code Pattern:**
```python
from databricks_langchain.genie import GenieAgent
from langgraph_supervisor import create_supervisor

# Genie for structured data
genie_agent = GenieAgent(
    space_id="your-genie-space-id",
    name="SQLAnalyst",
    description="Queries structured business data"
)

# Supervisor orchestrates multiple agents
supervisor = create_supervisor(
    agents=[genie_agent, vector_search_agent],
    model="databricks-meta-llama-3-3-70b-instruct"
)
```

**Notebook Deployment:**
```python
import mlflow
mlflow.langchain.autolog()  # Required on serverless

# Deploy to Model Serving
from databricks.agents import deploy
deploy(model_fqn="catalog.schema.my_agent", uc_function_tools=["catalog.schema.*"])
```

---

## 3. Demo Dataset Recommendations

**Built-in Options:**
- `samples.nyctaxi.trips` - NYC taxi data (good for analytics demos)
- `samples.tpch.*` - TPC-H benchmark (classic BI queries)
- `samples.tpcds_sf1.*` - TPC-DS retail scenario

**For Molson-style Use Case:**
Consider creating a simplified CPG/beverage analytics dataset with:
- Sales transactions
- Inventory levels
- Regional performance
- Seasonal trends

---

## 4. Key Talking Points (Lessons Learned)

Based on research from production deployments:

1. **The Accuracy Gap:** Benchmarks show 86% accuracy, real-world is ~6%. The gap = missing business context, not LLM capability.

2. **Data Engineering Layer is Critical:** Speed and SQL complexity require pre-aggregated views, semantic layer, and well-documented schemas.

3. **Trust Through Transparency:** Genie's "thinking steps" are essential for business adoption - always show the reasoning.

4. **Start Small:** 5 or fewer well-documented tables outperforms 25 poorly-documented ones.

5. **ROI Timeline:** Set expectations for 12-24 month horizon; PoC is easy, production is 6+ months (you cut to 10 weeks).

---

## 5. Technical Requirements Checklist

**For Genie Spaces:**
- [ ] Unity Catalog enabled workspace
- [ ] Pro SQL Warehouse or Serverless
- [ ] Tables registered in UC with comments/descriptions
- [ ] System prompt drafted
- [ ] Custom SQL expressions for key metrics

**For LangGraph Notebooks:**
- [ ] Python packages: `langgraph`, `databricks-langchain`, `mlflow>=3.1`
- [ ] Genie Space ID for API access
- [ ] Vector Search index (if using RAG)
- [ ] MLflow experiment for tracing

**Workshop Materials:**
- [ ] Git repo with notebooks
- [ ] Sample data uploaded to UC
- [ ] Step-by-step instructions document
- [ ] Fallback screenshots/recordings

---

## 6. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| WiFi issues | Have hotspot backup; pre-download notebooks |
| Genie rate limits | Space out demos; have pre-recorded backup |
| Compute quota | Test with 50 concurrent users beforehand |
| LLM hallucinations | Use well-tested questions; show "uncertain" handling |
| Time overrun | Have modular sections; cut technical deep-dive if needed |

---

## Next Steps

1. **Confirm with DBX (Vincent/Felix):** Environment provisioning approach
2. **Create Demo Dataset:** Anonymized Molson-style or use built-in samples
3. **Build Genie Space:** Configure with system prompts and SQL expressions
4. **Develop Notebooks:** LangGraph + Genie API integration
5. **Test End-to-End:** Simulate 50 concurrent users
6. **Prepare Fallbacks:** Screenshots, recordings, offline notebooks

---

# Part 1: Genie Spaces & AI/BI

## 1.1 Overview: What is AI/BI Genie Spaces?

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

## 1.2 Setting Up Genie Spaces

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

## 1.3 Writing System Prompts / Instructions

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

## 1.4 Custom SQL Expressions and Knowledge Store

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

## 1.5 Best Practices for Non-Technical Demos

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

## 1.6 Free Tier / Community Edition Availability

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

## 1.7 Limitations and Considerations

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

# Part 2: Databricks Agent Framework & MCP

## 2.1 Executive Summary

Databricks has evolved into a comprehensive AI agent platform with the following key capabilities as of January 2026:

- **Mosaic AI Agent Framework** (GA): Production-grade framework for building, evaluating, and deploying AI agents
- **Agent Bricks** (Beta, launched June 2025): Automated agent creation platform with pre-built templates
- **MCP Integration**: Native support for Model Context Protocol with managed servers and custom hosting
- **MLflow 3**: Redesigned for GenAI with agent observability, prompt versioning, and cross-platform monitoring
- **Mosaic AI Gateway** (GA): Unified entry point with guardrails, governance, and multi-provider support
- **Multi-Agent Supervisor**: Orchestration system for coordinating multiple specialized agents

---

## 2.2 Mosaic AI Agent Framework

### Overview

The Mosaic AI Agent Framework is now generally available and provides an end-to-end solution for building production-quality AI agents. It integrates tightly with Unity Catalog for governance and MLflow for tracking and evaluation.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **Agent Development** | Build agents using Python, LangChain, LangGraph, or custom frameworks |
| **Tool Integration** | Connect to Unity Catalog functions, MCP servers, Vector Search |
| **Governance** | End-to-end governance through Unity Catalog |
| **Evaluation** | Built-in LLM judges and human feedback integration |
| **Deployment** | One-click deployment to Model Serving endpoints |
| **Observability** | Real-time tracing with MLflow 3 |

### Supported Agent Authoring Libraries

- **LangGraph/LangChain**: Native integration via `databricks-langchain` package
- **LlamaIndex**: Supported for RAG-based agents
- **AutoGen**: Tool-calling agent support with Databricks tools
- **DSPy**: Single-turn tool-calling agents
- **Custom Python**: Full flexibility with MLflow ResponsesAgent interface

### Key Components

```
Mosaic AI Agent Framework
|-- Agent Development
|   |-- AI Playground (prototyping)
|   |-- Code-based authoring
|   +-- Agent Bricks (no-code/low-code)
|-- Tools & Integration
|   |-- Unity Catalog Functions
|   |-- MCP Servers (managed & custom)
|   |-- Vector Search
|   +-- Genie Spaces
|-- Evaluation
|   |-- LLM Judges
|   |-- Human Feedback (Review App)
|   +-- Custom Metrics
|-- Deployment
|   |-- Model Serving
|   |-- Auto-scaling
|   +-- Authentication
+-- Governance
    |-- Unity Catalog
    |-- AI Gateway
    +-- Guardrails
```

---

## 2.3 Agent Bricks Platform

### Introduction

Agent Bricks was announced at Data + AI Summit 2025 (June 11, 2025) as an automated approach to creating high-performing AI agents. It uses Mosaic AI Research techniques including TAO (Task-Aware Optimization) and ALHF (Automated Learning from Human Feedback).

### Agent Types

#### 1. Information Extraction
Extract structured data from unstructured documents:
- PDFs, emails, scanned forms
- No labeled training data required
- Outputs to structured tables

**Customer Example**: AstraZeneca parsed 400,000+ clinical trial documents and extracted structured data in under 60 minutes without writing code.

#### 2. Knowledge Assistant
Reliable Q&A over enterprise documents:
- Automatic content indexing
- Quality evaluation built-in
- Fast, accurate answers grounded in enterprise data
- Ideal for manuals, policies, technical guides

#### 3. Multi-Agent Supervisor
Orchestration system for complex tasks:
- Coordinates Genie Spaces, agent endpoints, UC functions, MCP servers
- Advanced AI orchestration patterns
- Task delegation and result synthesis

### Key Features

- **Declarative Configuration**: Build agents using natural language descriptions
- **Auto-Optimization**: Automatically generates synthetic data and benchmarks
- **Built-in Evaluation**: MLflow integration for quality assessment
- **MCP Integration**: Native support for MCP servers in agent workflows

---

## 2.4 MCP (Model Context Protocol) on Databricks

### Overview

MCP is an open-source standard that connects AI agents to tools, resources, prompts, and contextual information. Databricks provides comprehensive MCP support with both managed servers and custom hosting options.

### MCP Server Types on Databricks

#### 1. Managed MCP Servers

Databricks provides ready-to-use managed servers:

| Server Type | Purpose | URL Pattern |
|-------------|---------|-------------|
| **Unity Catalog Functions** | Execute UC functions as tools | `uc-functions` endpoint |
| **Vector Search** | Search unstructured data | `vector-search` endpoint |
| **Genie Spaces** | Query structured data via Genie | `genie` endpoint |

**Key Benefits**:
- Unity Catalog permissions enforced automatically
- No infrastructure management
- Secure by default with authentication

#### 2. Custom MCP Servers (Databricks Apps)

Host your own MCP servers as Databricks Apps:

**Requirements**:
- HTTP-compatible transport (streamable HTTP)
- App name prefixed with `mcp-`
- OAuth authentication for M2M communication

**Deployment Steps**:
1. Authenticate using `databricks auth login`
2. Create `requirements.txt` with dependencies
3. Configure `app.yaml` with server command
4. Deploy using Databricks CLI
5. Access at `https://<app-url>/mcp`

#### 3. External MCP Servers

Connect to third-party MCP servers through the MCP Marketplace (Public Preview).

### MCP Catalog (Beta)

New in 2025: The MCP Servers tab in Databricks provides:
- Discovery and governance of all MCP servers
- Built on Unity Catalog for security
- Access control consistent with enterprise standards

### databricks-mcp Python Library

The `databricks-mcp` library simplifies MCP authentication:

```python
# Installation
pip install databricks-mcp

# Key classes
from databricks_mcp import DatabricksMCPClient, DatabricksOAuthClientProvider
```

**Authentication Methods**:
- Databricks CLI profile (development)
- Service principal (production M2M)
- On-behalf-of-user (runtime user context)

---

## 2.5 Unity Catalog Integration

### Governance Model

Unity Catalog provides end-to-end governance for AI agents:

| Feature | Description |
|---------|-------------|
| **Function Registration** | Register Python/SQL functions as tools |
| **Access Control** | Per-column ACLs, row-level filters |
| **Audit Logging** | Complete audit trail of data access |
| **Credential Management** | Scoped, time-bound credentials |
| **Tool Discovery** | Centralized tool catalog |

### Creating UC Functions as Tools

Requirements for Python functions:
- **Type hints**: All arguments and return values must have type hints
- **Docstrings**: Google-style docstrings for LLM understanding
- **No variable arguments**: `*args` and `**kwargs` not supported

### Execution Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Serverless** (default) | Remote execution on Spark Connect serverless | Production |
| **Local** | Local subprocess execution | Development/debugging |

### Built-in AI Tools

Databricks provides built-in tools in Unity Catalog:

- `system.ai.python_exec`: Sandboxed Python code execution
- External connections for API integrations
- AI functions for common operations

---

## 2.6 Function Calling and Tool Use

### Tool Types

1. **Unity Catalog Functions**
   - SQL UDFs
   - Python UDFs (with type hints)
   - Pre-built system functions

2. **Vector Search Retrievers**
   - Unstructured data search
   - Automatic source citation

3. **MCP Tools**
   - Managed Databricks MCP servers
   - Custom MCP servers
   - External MCP servers (marketplace)

4. **Function Definitions**
   - Custom function schemas
   - Direct LLM tool definitions

### AI Playground Tool Options

Maximum 20 tools per agent:
- UC Function selection
- Function Definition (custom)
- Vector Search indexes
- MCP servers (managed and external)

### UCFunctionToolkit

```python
from databricks.agent_framework.tools import UCFunctionToolkit

# Initialize toolkit with UC function names
UC_TOOL_NAMES = ["system.ai.python_exec", "my_catalog.schema.my_function"]
uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)

# Get tool specifications
tools = uc_toolkit.tools
```

### LangChain Integration

```python
from databricks_langchain import UCFunctionToolkit

# Create toolkit for LangChain agents
toolkit = UCFunctionToolkit(function_names=["my_catalog.schema.keyword_extractor"])
tools = toolkit.get_tools()
```

---

## 2.7 Agent Evaluation

### Mosaic AI Agent Evaluation

Comprehensive evaluation framework integrated with MLflow:

#### Built-in LLM Judges

| Judge | Purpose |
|-------|---------|
| `relevance_to_query` | Check if response answers the query |
| `groundedness` | Verify response is grounded in provided context |
| `chunk_relevance` | Assess retrieved document relevance |
| `safety` | Detect toxic or harmful content |
| `guideline_adherence` | Verify custom guideline compliance |
| `context_sufficiency` | Check if context was sufficient (requires labels) |
| `correctness` | Verify factual accuracy (requires labels) |

#### Custom Evaluation

```python
import mlflow
from mlflow.genai.scorers import RelevanceToQuery, Safety

eval_dataset = [
    {
        "inputs": {"messages": [{"role": "user", "content": "What is an LLM?"}]},
        "expected_response": None,
    }
]

eval_results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=lambda messages: agent.predict({"messages": messages}),
    scorers=[RelevanceToQuery(), Safety()]
)
```

#### Advanced Evaluation Configuration

```python
guidelines = {
    'pricing': ["The agent should never provide pricing information."]
}

eval_results = mlflow.evaluate(
    model=lambda inputs: agent.predict(inputs),
    data=spark.table("evaluation_table"),
    model_type="databricks-agent",
    evaluator_config={
        "databricks-agent": {
            "global_guidelines": guidelines,
            "metrics": [
                "chunk_relevance",
                "guideline_adherence",
                "safety",
            ],
        },
    },
)
```

### Review App

The Agent Evaluation Review App enables:
- Domain expert assessment and labeling
- Custom criteria definition
- Structured feedback collection
- No spreadsheets or custom tools needed

### MLflow 3 Evaluation Features

- Evaluation datasets with versioning and lineage
- Integration with Unity Catalog
- Conversion of production traces to evaluation records
- Continuous improvement cycle with human feedback

---

## 2.8 Agent Deployment and Serving

### Deployment Methods

#### 1. Agent Framework deploy() API

```python
from databricks.agents import deploy

# Deploy agent to Model Serving
deployment = deploy(
    model_uri="models:/my_agent/1",
    endpoint_name="my-agent-endpoint"
)
```

**What deploy() does**:
- Creates Model Serving endpoint with auto-scaling
- Provisions secure authentication
- Enables MLflow tracing and monitoring
- Integrates with Review App

#### 2. Model Serving Endpoints

**Supported Model Types**:
- Custom models (MLflow format)
- Foundation models (Databricks-hosted)
- External models (via AI Gateway)

**Serving Features**:
- Serverless, auto-scaling architecture
- Scale-to-zero capability
- Pay-per-token pricing for foundation models

### Deployment Strategies

| Strategy | Description |
|----------|-------------|
| **Canary** | Gradual rollout to subset of traffic |
| **Blue/Green** | Parallel deployments with instant switch |
| **Shadow** | Test new version against production traffic |

### Production Tracing

Agents deployed on Databricks automatically:
- Log traces to MLflow experiment
- Support real-time viewing
- Optional long-term storage in Delta tables
- Automated quality assessment via Production Monitoring

### Prerequisites

- MLflow 3.1.3+ for `deploy()` API
- `databricks-agents` SDK 1.1.0+ for external notebook deployment
- Serverless compute enabled in workspace

---

## 2.9 AI Gateway and Guardrails

### Mosaic AI Gateway (GA)

Unified entry point for all AI services:

| Feature | Description |
|---------|-------------|
| **Multi-Provider Support** | OpenAI, Anthropic, Databricks-hosted, custom |
| **Automatic Fallback** | Switch between providers on failure |
| **Rate Limiting** | Control usage across teams |
| **Usage Logging** | Detailed telemetry in Unity Catalog |
| **Guardrails** | Safety, PII, keyword, topic filtering |

### Guardrail Types

#### 1. Safety Filtering
Filters harmful content:
- Hate speech
- Insults
- Sexual content
- Violence
- Misconduct

#### 2. PII Detection

```python
gateway_request_data = {
    "guardrails": {
        "input": {"pii": {"behavior": "BLOCK"}},
        "output": {"pii": {"behavior": "BLOCK"}},
    }
}
```

#### 3. Keyword Filters
Block specific topics or terms in requests/responses.

#### 4. Topic Filters
Keep applications focused on intended scope.

#### 5. Custom Guardrails
Bring your own guardrail logic for inputs and outputs.

### Security Framework

Databricks AI Security Framework (DASF) v2.0:
- Maps 62 technical security risks
- Covers 12 AI system components
- Addresses prompt injection and jailbreaks
- Prevents accidental data exposure

---

## 2.10 Multi-Agent Architecture

### Design Patterns

#### 1. Supervisor Pattern

```
                    +-----------------+
                    |   Supervisor    |
                    |     Agent       |
                    +--------+--------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
+---------------+    +---------------+    +---------------+
|  Genie Space  |    |   Knowledge   |    |   Custom      |
|    Agent      |    |   Assistant   |    |   Agent       |
+---------------+    +---------------+    +---------------+
```

#### 2. Hierarchical Multi-Agent

```
              +-----------------------------+
              |   Organization Orchestrator |
              |   (Supervisor of Supervisors)|
              +--------------+--------------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
+---------------+    +---------------+    +---------------+
|  Division A   |    |  Division B   |    |  Division C   |
|  Supervisor   |    |  Supervisor   |    |  Supervisor   |
+-------+-------+    +-------+-------+    +-------+-------+
        |                    |                    |
   +----+----+          +----+----+          +----+----+
   | Workers |          | Workers |          | Workers |
   +---------+          +---------+          +---------+
```

### Agent Roles

| Role | Description |
|------|-------------|
| **Supervisor Agents** | Strategic planning, dependency management, multi-stage orchestration |
| **Manager Agents** | Team coordination, goal-oriented task management |
| **Worker/Specialist Agents** | Domain expertise, specific task execution |

### Multi-Agent Supervisor Configuration

The Multi-Agent Supervisor coordinates:
- Genie Spaces (structured data queries)
- Knowledge Assistant endpoints
- Unity Catalog functions
- MCP servers

**Capabilities**:
- Task delegation
- Context management
- Result synthesis
- Natural language feedback integration

---

## 2.11 Code Examples

### Example 1: Basic Agent with UC Tools

```python
from databricks.agent_framework.tools import UCFunctionToolkit
from databricks_model_serving_client import DatabricksModelServingClient
import mlflow

# Enable tracing
mlflow.autogen.autolog(log_traces=True)

# Initialize tools
UC_TOOL_NAMES = ["system.ai.python_exec"]
uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)

# Custom tool definition
def weather_in_california_city(city: str) -> str:
    """Get the weather description of a city in California."""
    return f"The weather in {city} is sunny."

tools = [weather_in_california_city]
tools.extend(uc_toolkit.tools)

# LLM endpoint
LLM_ENDPOINT_NAME = "databricks-meta-llama-3-3-70b-instruct"
```

### Example 2: MCP Server Connection

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

# Managed MCP server
client = DatabricksMCPClient()

# Custom MCP server (Databricks App)
import os
workspace_client = WorkspaceClient(
    host="<DATABRICKS_WORKSPACE_URL>",
    client_id=os.getenv("DATABRICKS_CLIENT_ID"),
    client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
    auth_type="oauth-m2m",
)

CUSTOM_MCP_SERVER_URLS = [
    "https://<custom-mcp-app-url>/mcp"
]
```

### Example 3: LangChain Integration

```python
from databricks_langchain import UCFunctionToolkit, ChatDatabricks
from langchain_core.messages import HumanMessage

# Initialize LLM
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

# Initialize toolkit
toolkit = UCFunctionToolkit(
    function_names=["my_catalog.schema.keyword_extractor"]
)
tools = toolkit.get_tools()

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Invoke
response = llm_with_tools.invoke([
    HumanMessage(content="Extract keywords from: AI is transforming industries")
])
```

### Example 4: Agent Deployment

```python
from databricks.agents import deploy
import mlflow

# Log the agent
with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model=my_agent,
        registered_model_name="my_agent_model"
    )

# Deploy to serving endpoint
deployment = deploy(
    model_uri="models:/my_agent_model/1",
    endpoint_name="my-agent-endpoint"
)

print(f"Endpoint URL: {deployment.endpoint_url}")
```

### Example 5: PII Guardrails Configuration

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Update endpoint with guardrails
w.serving_endpoints.update_config(
    name="my-agent-endpoint",
    served_entities=[...],
    ai_gateway={
        "guardrails": {
            "input": {
                "pii": {"behavior": "BLOCK"},
                "safety": {"behavior": "BLOCK"}
            },
            "output": {
                "pii": {"behavior": "BLOCK"},
                "safety": {"behavior": "BLOCK"}
            }
        }
    }
)
```

---

# Part 3: LangGraph + Databricks Integration

## 3.1 Executive Summary

LangGraph is an open-source framework for building stateful, multi-actor applications with LLMs. It enables creating agent and multi-agent workflows using graph-based state machines. Databricks provides first-class integration with LangGraph through:

- **Mosaic AI Agent Framework**: Full lifecycle support for building, evaluating, and deploying LangGraph agents
- **MLflow 3 Tracing**: Automatic capture of graph execution with deep observability
- **Unity Catalog Integration**: Use governed SQL/Python functions as agent tools
- **Genie Space API**: Query structured data through natural language within LangGraph workflows
- **Vector Search**: Serverless similarity search for RAG applications
- **MCP Server Support**: Model Context Protocol integration for standardized tool access

**Key Requirements:**
- Python 3.10+
- Databricks Runtime 13.3 LTS+ or Serverless Compute
- MLflow 3.1.3+ for deployment features
- `databricks-langchain` package for native integrations

---

## 3.2 Running LangGraph Agents in Databricks Notebooks

### Environment Setup

```python
# Cell 1: Install dependencies
%pip install --upgrade \
    "mlflow[databricks]>=3.1" \
    langgraph \
    langchain_core \
    langchain_openai \
    databricks-langchain \
    unitycatalog-langchain[databricks]

dbutils.library.restartPython()
```

### Basic LangGraph Agent in Notebook

```python
# Cell 2: Import and configure
import mlflow
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from databricks_langchain import ChatDatabricks

# Enable automatic tracing (required on serverless compute)
mlflow.langchain.autolog()

# Set MLflow tracking
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/langgraph-workshop-demo")
```

```python
# Cell 3: Define tools and create agent
@tool
def get_customer_info(customer_id: str) -> str:
    """Retrieve customer information from the database."""
    # In production, this would query your Delta tables
    return f"Customer {customer_id}: Premium tier, Active since 2023"

@tool
def calculate_discount(amount: float, tier: str) -> float:
    """Calculate discount based on customer tier."""
    discounts = {"Premium": 0.20, "Standard": 0.10, "Basic": 0.05}
    return amount * discounts.get(tier, 0)

# Use Databricks Foundation Model API
llm = ChatDatabricks(
    endpoint="databricks-meta-llama-3-3-70b-instruct",
    temperature=0.1
)

# Create the ReAct agent
agent = create_react_agent(
    model=llm,
    tools=[get_customer_info, calculate_discount],
    prompt="You are a helpful customer service assistant."
)
```

```python
# Cell 4: Run the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "What discount can customer C123 get on a $500 purchase?"}]
})

print(result["messages"][-1].content)
```

### Streaming Output in Notebooks

```python
# Cell 5: Stream agent execution for real-time feedback
inputs = {"messages": [{"role": "user", "content": "Help me understand my account status"}]}

for chunk in agent.stream(inputs, stream_mode="updates"):
    print(chunk)
    print("---")
```

---

## 3.3 LangGraph + Genie Space API Integration

### Overview

The Genie Conversation API enables natural language queries against structured data. Combined with LangGraph, you can build multi-agent systems that handle both structured (SQL) and unstructured (documents) data queries.

### GenieAgent Setup

```python
from databricks_langchain.genie import GenieAgent

# Create a Genie agent for structured data queries
genie_agent = GenieAgent(
    genie_space_id="your-genie-space-id",  # From Genie Space URL
    genie_agent_name="SalesDataAgent",
    description="Queries structured sales data including revenue, orders, and customer metrics"
)
```

### Multi-Agent Supervisor with Genie

This pattern creates a supervisor that routes queries to specialized agents:

```python
from typing import Literal
from langchain_core.runnables import Runnable
from pydantic import BaseModel
from databricks_langchain.agent import UCFunctionToolkit, create_agent, create_supervisor
from databricks_langchain.chat_models import ChatDatabricks
from databricks_langchain.genie import GenieAgent

# Define agent types
class Genie(BaseModel):
    space_id: str
    name: str
    description: str

class InCodeSubAgent(BaseModel):
    tools: list[str]
    name: str
    description: str

def create_multi_agent_system(llm: Runnable):
    """Create a supervisor agent with Genie and tool-calling sub-agents."""

    agents = []
    agent_descriptions = ""

    # Add Genie agent for structured data
    genie_config = Genie(
        space_id="abc123-your-space-id",
        name="StructuredDataAgent",
        description="Queries sales metrics, revenue data, and customer analytics from Delta tables"
    )

    genie_agent = GenieAgent(
        genie_space_id=genie_config.space_id,
        genie_agent_name=genie_config.name,
        description=genie_config.description,
    )
    agents.append(genie_agent)
    agent_descriptions += f"- {genie_config.name}: {genie_config.description}\n"

    # Add in-code agent with Unity Catalog tools
    uc_toolkit = UCFunctionToolkit(
        function_names=["catalog.schema.calculate_metrics", "catalog.schema.send_notification"]
    )

    tool_agent = create_agent(
        llm,
        tools=uc_toolkit.tools,
        name="ToolAgent"
    )
    agents.append(tool_agent)
    agent_descriptions += "- ToolAgent: Executes calculations and sends notifications\n"

    # Create supervisor prompt
    supervisor_prompt = f"""
    You are a supervisor coordinating a team of specialized agents.

    Available agents:
    {agent_descriptions}

    Route queries to the appropriate agent:
    - Use StructuredDataAgent for numeric/metric questions about sales, revenue, orders
    - Use ToolAgent for calculations and actions

    Synthesize responses from multiple agents when needed.
    """

    return create_supervisor(
        agents=agents,
        model=llm,
        prompt=supervisor_prompt,
        output_mode="full_history",
    ).compile()

# Create and run the multi-agent system
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
supervisor = create_multi_agent_system(llm)

result = supervisor.invoke({
    "messages": [{"role": "user", "content": "What was Q4 revenue and how does it compare to our target?"}]
})
```

### Genie API Direct Integration

For more control, use the Genie Conversation API directly:

```python
import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

def query_genie_space(space_id: str, question: str) -> dict:
    """Query a Genie Space and return the response."""

    # Start a new conversation
    conversation = w.genie.start_conversation(
        space_id=space_id,
        content=question
    )

    # Poll for completion
    while conversation.status == "PENDING":
        conversation = w.genie.get_conversation(
            space_id=space_id,
            conversation_id=conversation.conversation_id
        )

    return {
        "answer": conversation.response.content,
        "sql_query": conversation.response.sql_query if hasattr(conversation.response, 'sql_query') else None,
        "data": conversation.response.data if hasattr(conversation.response, 'data') else None
    }
```

---

## 3.4 Best Practices for LangGraph in Databricks

### State Management

```python
from typing import Annotated, TypedDict
from operator import add
from langgraph.graph import StateGraph, START, END

# Use TypedDict for explicit state schemas
class AgentState(TypedDict):
    messages: Annotated[list, add]  # Accumulate messages
    context: str                     # Current context
    iteration_count: int             # Track iterations

# Keep state minimal - avoid dumping transient values
def process_node(state: AgentState) -> dict:
    # Only return what needs to persist
    return {
        "messages": [{"role": "assistant", "content": "Processed"}],
        "iteration_count": state["iteration_count"] + 1
    }
```

### Memory Configuration

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# Development: InMemorySaver (fast but non-persistent)
dev_checkpointer = InMemorySaver()

# Production: SqliteSaver or PostgresSaver
# For Databricks notebooks, SQLite works well for demos
prod_checkpointer = SqliteSaver.from_conn_string("/dbfs/tmp/checkpoints.db")

# Compile graph with checkpointer
graph = builder.compile(checkpointer=prod_checkpointer)

# Use thread_id for conversation continuity
config = {"configurable": {"thread_id": "user-123-session-456"}}
result = graph.invoke({"messages": []}, config)

# Resume later with same thread_id
saved_state = graph.get_state(config)
```

### Error Handling

```python
from langgraph.graph import StateGraph

def safe_node(state):
    """Node with error handling."""
    try:
        # Your logic here
        result = process_data(state)
        return {"status": "success", "data": result}
    except Exception as e:
        # Log to MLflow
        mlflow.log_param("error_node", "safe_node")
        mlflow.log_param("error_message", str(e))
        return {"status": "error", "error": str(e)}

def should_retry(state) -> str:
    """Conditional edge for retry logic."""
    if state.get("status") == "error" and state.get("retry_count", 0) < 3:
        return "retry"
    return "continue"

builder = StateGraph(AgentState)
builder.add_node("process", safe_node)
builder.add_conditional_edges("process", should_retry, {"retry": "process", "continue": END})
```

### Streaming Best Practices

```python
# Choose stream mode based on use case

# For chatbots - stream individual tokens
for chunk in agent.stream(inputs, stream_mode="messages"):
    print(chunk, end="", flush=True)

# For long-running agents - stream state updates
for update in agent.stream(inputs, stream_mode="updates"):
    print(f"Node: {update.get('node')}, Status: {update.get('status')}")

# For debugging - stream full values
for state in agent.stream(inputs, stream_mode="values"):
    print(f"Full state: {state}")
```

### Databricks-Specific Best Practices

1. **Use Serverless Compute**: Provides automatic scaling and latest runtime features
2. **Explicitly Enable Autolog**: On serverless, call `mlflow.langchain.autolog()` explicitly
3. **Leverage Unity Catalog**: Store tools as governed functions for discoverability
4. **Use ChatDatabricks**: Native integration with Foundation Model APIs
5. **Configure Timeouts**: Set appropriate timeouts for tool calls to external systems

---

## 3.5 MLflow Integration with LangGraph

### Automatic Tracing Setup

```python
import mlflow
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Enable autologging - this traces all LangGraph executions
mlflow.langchain.autolog()

# Configure MLflow to use Databricks
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/langgraph-tracing-demo")

@tool
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    return f"It's sunny in {city}"

llm = ChatOpenAI(model="gpt-4o-mini")
graph = create_react_agent(llm, [get_weather])

# This invocation is automatically traced
result = graph.invoke({
    "messages": [{"role": "user", "content": "What's the weather in SF?"}]
})

# View traces in MLflow UI: Experiment -> Traces tab
```

### Manual Span Creation

For more granular control:

```python
import mlflow

def custom_node(state):
    """Node with custom tracing spans."""

    with mlflow.start_span(name="data_validation") as span:
        span.set_attribute("input_length", len(state.get("messages", [])))
        validated = validate_input(state)
        span.set_attribute("validation_passed", validated)

    with mlflow.start_span(name="processing") as span:
        result = process_data(state)
        span.set_attribute("result_type", type(result).__name__)

    return {"processed_data": result}
```

### Logging Models for Deployment

```python
import mlflow
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksFunction

# Define resources the agent needs
resources = [
    DatabricksServingEndpoint(endpoint_name="databricks-meta-llama-3-3-70b-instruct"),
    DatabricksFunction(function_name="catalog.schema.my_tool"),
]

# Log the agent
with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model="agent.py",  # Your agent code file
        pip_requirements=[
            "mlflow>=3.1",
            "langchain",
            "langgraph",
            "databricks-langchain",
        ],
        resources=resources,
    )

    # Register to Unity Catalog
    mlflow.register_model(
        f"runs:/{mlflow.active_run().info.run_id}/agent",
        "catalog.schema.my_langgraph_agent"
    )
```

### Disabling Auto-Tracing

```python
# Disable globally
mlflow.langchain.autolog(disable=True)

# Or disable all autologging
mlflow.autolog(disable=True)
```

---

## 3.6 Databricks as Vector Store with LangGraph

### VectorSearchRetrieverTool Setup

```python
from databricks_langchain import VectorSearchRetrieverTool, ChatDatabricks
from langgraph.prebuilt import create_react_agent

# Create vector search retriever tool
retriever_tool = VectorSearchRetrieverTool(
    index_name="catalog.schema.document_index",
    tool_description="Search company documentation for policies, procedures, and technical guides",
    # Optional: Add filters
    # filters={"department": "engineering"}
)

# Create agent with retrieval capability
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
rag_agent = create_react_agent(
    model=llm,
    tools=[retriever_tool],
    prompt="You are a helpful assistant that answers questions using company documentation."
)

# Query with RAG
result = rag_agent.invoke({
    "messages": [{"role": "user", "content": "What is our vacation policy?"}]
})
```

### Custom Retriever Integration

```python
from databricks_langchain import DatabricksVectorSearch
from langchain_core.tools import tool

# Create vector store
vector_store = DatabricksVectorSearch(
    index_name="catalog.schema.knowledge_base",
    embedding_model="databricks-bge-large-en"  # Or your embedding endpoint
)

# Convert to retriever
retriever = vector_store.as_retriever(
    search_kwargs={"k": 5}
)

# Create custom retrieval tool with post-processing
@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information."""
    docs = retriever.invoke(query)

    # Format results
    results = []
    for i, doc in enumerate(docs, 1):
        results.append(f"{i}. {doc.page_content[:200]}...")

    return "\n\n".join(results)
```

### Agentic RAG Pattern

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from operator import add

class RAGState(TypedDict):
    messages: Annotated[list, add]
    retrieved_docs: list
    should_retrieve: bool

def route_query(state) -> str:
    """Decide whether to retrieve or answer directly."""
    last_message = state["messages"][-1]["content"]

    # Simple heuristic - in production, use LLM routing
    if any(word in last_message.lower() for word in ["policy", "procedure", "document", "guide"]):
        return "retrieve"
    return "answer"

def retrieve_docs(state):
    """Retrieve relevant documents."""
    query = state["messages"][-1]["content"]
    docs = retriever.invoke(query)
    return {"retrieved_docs": docs}

def generate_answer(state):
    """Generate answer using retrieved docs or LLM knowledge."""
    context = "\n".join([d.page_content for d in state.get("retrieved_docs", [])])

    messages = state["messages"] + [
        {"role": "system", "content": f"Context:\n{context}" if context else "No additional context."}
    ]

    response = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": response.content}]}

# Build the graph
builder = StateGraph(RAGState)
builder.add_node("retrieve", retrieve_docs)
builder.add_node("answer", generate_answer)

builder.add_conditional_edges(START, route_query, {"retrieve": "retrieve", "answer": "answer"})
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)

rag_graph = builder.compile()
```

### Reranking for Better Results

Databricks Vector Search supports built-in reranking (Public Preview):

```python
# Enable reranking for higher quality retrieval
retriever_tool = VectorSearchRetrieverTool(
    index_name="catalog.schema.document_index",
    tool_description="Search documents with reranking",
    rerank=True,  # Enable reranking
    rerank_top_k=20,  # Retrieve 20, rerank to return top k
)
```

---

## 3.7 Deploying LangGraph Agents on Databricks

### Step 1: Wrap Agent with ResponsesAgent

```python
# agent.py - Your agent code file
from mlflow.pyfunc import PythonModel
from mlflow.types.agent import ResponsesAgentRequest, ResponsesAgentResponse

class MyLangGraphAgent(PythonModel):
    def load_context(self, context):
        """Load the agent when the model is loaded."""
        import mlflow
        from langgraph.prebuilt import create_react_agent
        from databricks_langchain import ChatDatabricks

        mlflow.langchain.autolog()

        self.llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
        self.agent = create_react_agent(
            model=self.llm,
            tools=self._create_tools(),
            prompt="You are a helpful assistant."
        )

    def _create_tools(self):
        """Define your tools here."""
        from langchain_core.tools import tool

        @tool
        def get_info(query: str) -> str:
            """Get information."""
            return f"Info for: {query}"

        return [get_info]

    def predict(self, context, model_input: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Handle prediction requests."""
        messages = [{"role": m.role, "content": m.content} for m in model_input.messages]

        result = self.agent.invoke({"messages": messages})

        return ResponsesAgentResponse(
            messages=[{
                "role": "assistant",
                "content": result["messages"][-1].content
            }]
        )
```

### Step 2: Log and Register the Model

```python
import mlflow
from mlflow.models.resources import DatabricksServingEndpoint

# Define resources
resources = [
    DatabricksServingEndpoint(endpoint_name="databricks-meta-llama-3-3-70b-instruct"),
]

# Log the model
with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        artifact_path="langgraph_agent",
        python_model="agent.py",
        pip_requirements=[
            "mlflow>=3.1",
            "langgraph",
            "langchain",
            "databricks-langchain",
        ],
        resources=resources,
        registered_model_name="catalog.schema.my_langgraph_agent"
    )
```

### Step 3: Deploy to Model Serving

```python
from databricks import agents

# Deploy the registered model
deployment_info = agents.deploy(
    model_name="catalog.schema.my_langgraph_agent",
    model_version=1,
    scale_to_zero=True,  # Cost-effective for demos
    environment_vars={
        "DATABRICKS_HOST": "{{secrets/scope/host}}",
        "DATABRICKS_TOKEN": "{{secrets/scope/token}}"
    }
)

print(f"Endpoint: {deployment_info.endpoint_name}")
print(f"Status: {deployment_info.status}")
```

### Step 4: Test the Deployed Agent

```python
# Test via REST API
import requests

endpoint_url = f"https://{workspace_url}/serving-endpoints/{deployment_info.endpoint_name}/invocations"

response = requests.post(
    endpoint_url,
    headers={"Authorization": f"Bearer {token}"},
    json={
        "messages": [{"role": "user", "content": "Hello, how can you help me?"}]
    }
)

print(response.json())
```

### State Management Considerations

**Important:** Databricks Model Serving is distributed. The same replica may not handle all requests in a multi-turn conversation. Design accordingly:

```python
class StatefulAgent(PythonModel):
    def predict(self, context, model_input):
        # Use external state store for multi-turn conversations
        thread_id = model_input.thread_id

        # Retrieve state from external store (Redis, DynamoDB, etc.)
        state = self.state_store.get(thread_id)

        # Process with state
        result = self.agent.invoke({"messages": messages}, config={"thread_id": thread_id})

        # Save updated state
        self.state_store.put(thread_id, result)

        return result
```

---

## 3.8 Sample Notebook Code Patterns

### Pattern 1: Quick Start Agent

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph langchain databricks-langchain
dbutils.library.restartPython()

# Cmd 2: Imports and Config
import mlflow
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from databricks_langchain import ChatDatabricks

mlflow.langchain.autolog()
mlflow.set_experiment("/Users/your-email/langgraph-demo")

# Cmd 3: Define Tools
@tool
def search_products(query: str) -> str:
    """Search product catalog."""
    # Replace with actual Spark SQL query
    return f"Found products matching: {query}"

@tool
def check_inventory(product_id: str) -> str:
    """Check product inventory."""
    return f"Product {product_id}: 150 units in stock"

# Cmd 4: Create Agent
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
agent = create_react_agent(llm, [search_products, check_inventory])

# Cmd 5: Test
result = agent.invoke({
    "messages": [{"role": "user", "content": "Find laptops and check inventory for the first one"}]
})
display(result)
```

### Pattern 2: RAG with Vector Search

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph databricks-langchain
dbutils.library.restartPython()

# Cmd 2: Configure
import mlflow
from databricks_langchain import ChatDatabricks, VectorSearchRetrieverTool
from langgraph.prebuilt import create_react_agent

mlflow.langchain.autolog()

# Cmd 3: Create RAG Agent
retriever = VectorSearchRetrieverTool(
    index_name="main.docs.company_policies",
    tool_description="Search company policies and procedures"
)

llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

rag_agent = create_react_agent(
    model=llm,
    tools=[retriever],
    prompt="""You are an HR assistant. Use the search tool to find relevant policies
    before answering questions. Always cite the source document."""
)

# Cmd 4: Query
result = rag_agent.invoke({
    "messages": [{"role": "user", "content": "What is our remote work policy?"}]
})
print(result["messages"][-1].content)
```

### Pattern 3: Multi-Agent with Genie

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph databricks-langchain
dbutils.library.restartPython()

# Cmd 2: Imports
import mlflow
from databricks_langchain import ChatDatabricks
from databricks_langchain.genie import GenieAgent
from databricks_langchain.agent import create_supervisor

mlflow.langchain.autolog()

# Cmd 3: Create Agents
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

# Genie agent for structured data
sales_genie = GenieAgent(
    genie_space_id="your-genie-space-id",
    genie_agent_name="SalesAnalyst",
    description="Queries sales data, revenue metrics, and customer analytics"
)

# Cmd 4: Create Supervisor
supervisor = create_supervisor(
    agents=[sales_genie],
    model=llm,
    prompt="""You coordinate data analysis. Route questions about sales,
    revenue, and metrics to the SalesAnalyst agent.""",
    output_mode="full_history"
).compile()

# Cmd 5: Query
result = supervisor.invoke({
    "messages": [{"role": "user", "content": "What was our total revenue last quarter?"}]
})
print(result["messages"][-1].content)
```

### Pattern 4: Unity Catalog Tools

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph databricks-langchain unitycatalog-langchain[databricks]
dbutils.library.restartPython()

# Cmd 2: Create UC Function (run once)
spark.sql("""
CREATE OR REPLACE FUNCTION main.default.calculate_tax(amount DOUBLE, rate DOUBLE)
RETURNS DOUBLE
LANGUAGE PYTHON
AS $$
    return amount * rate
$$
""")

# Cmd 3: Create Agent with UC Tools
import mlflow
from databricks_langchain import ChatDatabricks, UCFunctionToolkit
from langgraph.prebuilt import create_react_agent

mlflow.langchain.autolog()

# Load tools from Unity Catalog
toolkit = UCFunctionToolkit(
    function_names=["main.default.calculate_tax"]
)

llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

agent = create_react_agent(
    model=llm,
    tools=toolkit.tools,
    prompt="You are a tax calculation assistant."
)

# Cmd 4: Test
result = agent.invoke({
    "messages": [{"role": "user", "content": "Calculate 8% tax on $1500"}]
})
print(result["messages"][-1].content)
```

### Pattern 5: Full Production Pipeline

```python
# Cmd 1: Setup
%pip install -U "mlflow[databricks]>=3.1" langgraph databricks-langchain databricks-agents
dbutils.library.restartPython()

# Cmd 2: Define Agent
import mlflow
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from databricks_langchain import ChatDatabricks

@tool
def get_order_status(order_id: str) -> str:
    """Get status of an order."""
    # In production, query Delta table
    return f"Order {order_id}: Shipped, arriving tomorrow"

def create_agent():
    llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
    return create_react_agent(llm, [get_order_status])

# Cmd 3: Log to MLflow
from mlflow.models.resources import DatabricksServingEndpoint

mlflow.langchain.autolog()
mlflow.set_experiment("/Shared/production-agent")

with mlflow.start_run():
    # Log the agent
    model_info = mlflow.langchain.log_model(
        lc_model=create_agent(),
        artifact_path="agent",
        pip_requirements=["langgraph", "databricks-langchain"],
        resources=[
            DatabricksServingEndpoint(endpoint_name="databricks-meta-llama-3-3-70b-instruct")
        ],
        registered_model_name="main.default.order_assistant"
    )

# Cmd 4: Deploy
from databricks import agents

deployment = agents.deploy(
    model_name="main.default.order_assistant",
    model_version=1,
    scale_to_zero=True
)

print(f"Deployed to: {deployment.endpoint_name}")

# Cmd 5: Test Endpoint
import requests

response = requests.post(
    f"{deployment.endpoint_url}/invocations",
    headers={"Authorization": f"Bearer {dbutils.secrets.get('scope', 'token')}"},
    json={"messages": [{"role": "user", "content": "Where is order ORD-123?"}]}
)
print(response.json())
```

---

# Part 4: Free Tier & Workshop Setup

## 4.1 IMPORTANT: Community Edition Has Been Retired

**Community Edition was officially retired on January 1, 2026.** All users have been encouraged to migrate to the new **Databricks Free Edition**.

Key changes from Community Edition to Free Edition:
- Free Edition uses **serverless compute only** (no classic clusters)
- **Scala and RDDs are not supported** (Python and SQL only)
- **Unity Catalog is included** (major upgrade from CE)
- Modern features like MLflow, Delta Live Tables, Dashboards, and AI Assistant are available
- Cloud mounts (DBFS mounts) are not supported

**Migration Path:** Users with Community Edition accounts can migrate with a one-click tool at [login.databricks.com](https://login.databricks.com) or create fresh Free Edition accounts at [signup.databricks.com](https://signup.databricks.com).

---

## 4.2 Databricks Free Edition - Current Features and Limitations

### Features Included

| Feature | Availability |
|---------|--------------|
| Python notebooks | Yes |
| SQL notebooks | Yes |
| Unity Catalog | Yes |
| Serverless compute | Yes (managed by Databricks) |
| Databricks Assistant (AI) | Yes |
| MLflow | Yes |
| Delta Live Tables | Yes (1 active pipeline per type) |
| Dashboards | Yes |
| Model Serving | Yes (CPU only, limited) |
| Genie | Yes |
| Jobs/Workflows | Yes (max 5 concurrent tasks) |
| SQL Warehouse | Yes (1 warehouse, 2X-Small max) |
| Vector Search | Yes (1 endpoint, 1 unit) |
| Databricks Apps | Yes (1 app, auto-stops after 24 hours) |

### Limitations

#### Compute Restrictions
- **Serverless only** - No custom cluster configurations
- **No GPUs** - CPU-only workloads
- **Small cluster sizes** - Limited to small serverless compute
- **One all-purpose cluster** (CPU-only)
- **One SQL warehouse** capped at 2X-Small size
- **Max 5 concurrent job tasks** per account

#### Language/Feature Restrictions
- **No Scala support**
- **No R support**
- **No RDD APIs** - Only Spark DataFrame/SQL APIs via Spark Connect
- **No JAR libraries** in notebooks (JAR tasks in jobs are supported)
- **No cloud mounts** - Cannot mount external storage
- **Limited DBFS access** - Use Unity Catalog volumes or workspace files instead
- **Restricted outbound internet** - Limited to trusted domains only

#### Administrative Limitations
- **One workspace per account**
- **One metastore per account**
- **No account console access**
- **No account-level APIs**
- **No SSO/SCIM** - Only email OTP, Google, or Microsoft sign-in
- **Cannot be Marketplace providers**

#### Unsupported Features
- Online tables
- Clean rooms
- Agent Bricks
- Lakebase database instances
- Legacy features
- Provisioned throughput for model serving

#### Usage Policies
- **Non-commercial use only**
- **No SLA or official support**
- **Inactive accounts may be deleted** after prolonged inactivity
- Contact: free_edition_help@databricks.com

---

## 4.3 Free Trial Options

### 14-Day Free Trial with $400 Credits

| Aspect | Details |
|--------|---------|
| Duration | 14 days |
| Credits | Up to $400 in Databricks usage |
| Platform | Full Databricks platform access |
| Cloud Providers | AWS, Azure, GCP |
| Billing | Pay-as-you-go after trial ends |

#### What's Included in the Trial
- Full access to all Databricks features
- Premium tier features (on Azure)
- Custom cluster configurations
- GPU compute (subject to availability)
- All language support (Python, SQL, Scala, R)
- Full administrative capabilities
- Unity Catalog
- Account console access

#### Personal Email Limitations
If signing up with a personal email address (Gmail, Yahoo, etc.):
- Serverless SQL warehouses capped at 50 DBUs/hour (max one per workspace)
- Notebook and job compute limited to 50 DBUs/hour
- No GPU access
- Vector search restricted to one endpoint at 1 unit
- Limited external network connectivity

**Recommendation:** Use a business/corporate email to avoid these restrictions.

#### Trial Signup Options

1. **Express Signup** - No cloud account needed, immediate serverless workspace
2. **AWS Marketplace** - Integrates with existing AWS billing
3. **Azure Portal** - Create workspace with Trial (Premium) pricing tier
4. **GCP Console** - Standard signup process

#### After Trial Ends
- Automatic conversion to pay-as-you-go
- To avoid charges: terminate all compute, remove payment methods, cancel subscription

---

## 4.4 What's Included vs. Excluded Comparison

| Feature | Free Edition | 14-Day Trial |
|---------|--------------|--------------|
| **Cost** | Free forever | $400 credits (14 days) |
| **Unity Catalog** | Yes | Yes |
| **Python/SQL** | Yes | Yes |
| **Scala/R** | No | Yes |
| **RDD APIs** | No | Yes |
| **GPUs** | No | Yes |
| **Custom Clusters** | No | Yes |
| **Serverless Compute** | Yes | Yes |
| **Admin Console** | No | Yes |
| **SSO/SCIM** | No | Yes |
| **Multiple Workspaces** | No (1 only) | Yes |
| **Commercial Use** | No | Yes |
| **SLA/Support** | No | Yes (during trial) |
| **Cloud Mounts** | No | Yes |
| **Classic Compute** | No | Yes |
| **Jobs** | 5 concurrent max | Full capabilities |
| **SQL Warehouse Size** | 2X-Small max | Any size |

---

## 4.5 Workshop Environment Setup Best Practices

### For Free Edition Workshops (40-50 Participants)

#### Setup Approach
Since Free Edition requires **individual accounts per user**, the recommended setup is:

1. **Pre-workshop Communication**
   - Send signup instructions 1-2 days before the workshop
   - Provide link: [signup.databricks.com](https://signup.databricks.com)
   - Request participants create accounts using their email addresses
   - Share a video walkthrough of the signup process

2. **Account Configuration**
   - Each participant gets their own workspace
   - No centralized admin control possible
   - Participants manage their own environments

3. **Content Distribution Options**
   - **Option A (Recommended):** Create a Databricks Marketplace listing for your workshop datasets and notebooks
   - **Option B:** Host notebooks on GitHub, have participants import via URL
   - **Option C:** Provide downloadable notebook archives (.dbc files)

4. **Daily Quota Management**
   - 99% of users will not hit rate limits under normal use
   - If quotas are exceeded, compute pauses until next day reset
   - Plan multi-day workshops to spread compute usage
   - Avoid having all 40-50 participants run heavy workloads simultaneously

#### Important Considerations
- **No shared workspaces** - Each account is isolated
- **Cannot pre-provision accounts** - Students must self-register
- **No instructor monitoring** - Cannot see participant progress centrally
- **Language restrictions** - Ensure all materials use Python/SQL only

### For 14-Day Trial Workshops (Enterprise Setup)

If you need centralized control and full features:

1. **Option A: Individual Trial Accounts**
   - Each participant signs up for their own trial
   - Similar to Free Edition but with full features
   - Participants use their own $400 credits
   - Risk: Participants may need to provide payment info

2. **Option B: Organizational/Partner Setup**
   - Contact Databricks for workshop credits
   - Use enterprise workspace with multiple users
   - Centralized admin control
   - Requires Databricks partnership or sales engagement

3. **Option C: Third-Party Lab Platforms**
   - **CloudLabs + Databricks**: Managed lab environments with instructor controls
   - **Vocareum**: Pre-provisioned sandbox environments
   - **Databricks Academy Labs**: Guided lab experiences (limited availability)

### Enterprise/Partner Workshop Setup

For professional workshops with full control:

1. **Databricks Academy Labs**
   - Guided lab experiences
   - Available through partner programs
   - Access via Partner Labs enrollment

2. **CloudLabs Integration**
   - Custom lab duration and cluster runtime
   - Pre-installed libraries
   - Instructor dashboards for monitoring
   - Can host on AWS, Azure, or GCP
   - Catalog and permission management

3. **Manual Enterprise Setup**
   - Create dedicated workspace for workshop
   - Use cluster policies to limit resource consumption
   - Set up user groups via Identity Provider
   - Pre-load datasets to shared storage
   - Use ARM templates or Terraform for provisioning

---

## 4.6 Provisioning for 40-50 Participants

### Option 1: Free Edition (Decentralized)

**Pros:**
- Zero cost
- No administrative overhead for provisioning
- Each participant has their own isolated environment
- Good for learning-focused workshops

**Cons:**
- No centralized monitoring or control
- Participants must self-register
- Daily quota limits may affect intensive workshops
- No Scala/R/RDD support

**Implementation Steps:**
1. Create workshop materials in Python/SQL only
2. Upload workshop datasets to Databricks Marketplace
3. Send registration instructions to all participants
4. Provide notebook import instructions
5. Have backup plan for quota-exceeded scenarios

### Option 2: 14-Day Trial (Decentralized with Full Features)

**Pros:**
- Full Databricks features
- $400 credits per participant
- All languages supported

**Cons:**
- Participants may need payment information
- 14-day time limit
- No centralized control

### Option 3: Enterprise/Partner Workshop (Centralized)

**Pros:**
- Full administrative control
- Centralized user management
- Pre-provisioned environments
- Progress monitoring
- Custom cluster policies

**Cons:**
- Requires partnership or commercial arrangement
- Potential costs involved
- More complex setup

**Implementation Steps:**
1. Contact Databricks sales/partnerships or use CloudLabs
2. Set up enterprise workspace
3. Configure Identity Provider groups
4. Create cluster policies with resource limits
5. Pre-load datasets to Unity Catalog
6. Provision user accounts via SCIM or manual import
7. Set up monitoring dashboards

### Recommended Approach for 40-50 Participants

| Workshop Type | Recommended Option |
|---------------|-------------------|
| **University/Education** | Free Edition (individual accounts) |
| **Corporate Training** | 14-Day Trial or Enterprise Setup |
| **Partner/Customer Workshop** | CloudLabs or Databricks Partnership |
| **Conference Demo** | Free Edition (demo account) |
| **Multi-day Bootcamp** | Enterprise Setup with CloudLabs |

---

## 4.7 Sample Datasets Available in Databricks

### Unity Catalog Sample Datasets (Recommended)

All Free Edition and Trial accounts have access to the `samples` catalog in Unity Catalog:

```sql
-- Access pattern: samples.<schema>.<table>
SELECT * FROM samples.nyctaxi.trips LIMIT 10;
```

#### Available Schemas and Tables

| Catalog | Schema | Tables | Description |
|---------|--------|--------|-------------|
| samples | nyctaxi | trips | NYC taxi ride data (pickup/dropoff, fares, tips) |
| samples | tpch | Multiple tables | TPC-H benchmark data (orders, customers, suppliers) |
| samples | tpcds_sf1 | Multiple tables | TPC-DS benchmark data (web sales, inventory, stores) |

#### Listing Available Tables
```sql
-- List all tables in nyctaxi schema
SHOW TABLES IN samples.nyctaxi;

-- List all tables in TPC-H schema
SHOW TABLES IN samples.tpch;

-- List all tables in TPC-DS schema
SHOW TABLES IN samples.tpcds_sf1;
```

### Workshop Dataset Recommendations

| Workshop Topic | Recommended Dataset |
|----------------|---------------------|
| SQL Basics | samples.nyctaxi.trips |
| Data Engineering | samples.tpch (multiple tables for joins) |
| Performance Testing | samples.tpcds_sf1 |
| Machine Learning | scikit-learn built-in datasets |
| Streaming (simulated) | Convert nyctaxi to streaming source |

---

## 4.8 Unity Catalog Access in Free/Trial Tiers

### Unity Catalog in Free Edition

**Good news:** Unity Catalog is included in Free Edition at no additional cost.

Features available:
- Centralized data catalog
- Access control
- Data lineage
- Quality monitoring
- Data discovery
- Three-level namespace (catalog.schema.table)

Limitations:
- One metastore per account
- One workspace per account
- No account-level administration
- Cannot create external locations (cloud storage mounts)

### Unity Catalog in 14-Day Trial

Full Unity Catalog capabilities:
- Multiple workspaces
- Multiple metastores
- External locations
- Full admin console
- Complete governance features

---

## 4.9 Time Limits and Compute Restrictions Summary

### Free Edition Quotas

| Resource | Limit |
|----------|-------|
| Daily compute usage | Subject to "fair usage policy" |
| Concurrent job tasks | 5 maximum |
| SQL warehouses | 1 (2X-Small max) |
| All-purpose clusters | 1 (small, CPU-only) |
| Vector search endpoints | 1 (1 unit) |
| DLT pipelines | 1 per type |
| Databricks Apps | 1 (auto-stops after 24 hours) |
| Workspaces | 1 per account |

**What happens when quota is exceeded:**
- Compute resources shut down for remainder of the day
- In extreme cases, shutdown extends through the month
- Data and settings are preserved
- Access resumes when quota resets (next day)

**Note:** Databricks states that "99% or more of users will not experience rate limitations or throttling" under normal use.

### 14-Day Trial Limits

| Resource | Limit |
|----------|-------|
| Duration | 14 days |
| Credits | $400 worth of DBUs |
| Compute (personal email) | 50 DBUs/hour max |
| SQL warehouse (personal email) | 50 DBUs/hour max, 1 per workspace |
| GPUs (personal email) | Not available |

Trial ends when:
- 14 days elapse, OR
- $400 credits exhausted

---

## 4.10 Workshop Checklist

### Pre-Workshop Preparation (1-2 Weeks Before)

- [ ] Decide on Free Edition vs Trial vs Enterprise setup
- [ ] Prepare all materials in supported languages (Python/SQL for Free Edition)
- [ ] Test materials in target environment
- [ ] Create Marketplace listing for datasets (optional)
- [ ] Prepare GitHub repository with notebooks
- [ ] Send registration instructions to participants
- [ ] Create backup plan for quota/credit issues

### Day Before Workshop

- [ ] Verify all participants have registered
- [ ] Test sample dataset access
- [ ] Prepare troubleshooting guide
- [ ] Set up communication channel (Slack/Teams/email)

### Workshop Day

- [ ] Have participants verify account access
- [ ] Walk through notebook import process
- [ ] Monitor for quota issues
- [ ] Provide alternative exercises if compute unavailable
- [ ] Document common issues for future workshops

### Post-Workshop

- [ ] Collect feedback on environment
- [ ] Document lessons learned
- [ ] Update materials based on experience
- [ ] Clean up any temporary resources

---

## 4.11 Quick Reference Commands

### Unity Catalog Sample Data Access
```sql
-- NYC Taxi Data
SELECT * FROM samples.nyctaxi.trips LIMIT 100;

-- TPC-H Data
SELECT * FROM samples.tpch.customer LIMIT 100;
SELECT * FROM samples.tpch.orders LIMIT 100;

-- List available schemas
SHOW SCHEMAS IN samples;

-- List tables in a schema
SHOW TABLES IN samples.nyctaxi;
```

### Python Notebook Setup
```python
# Read sample data as DataFrame
df = spark.table("samples.nyctaxi.trips")
df.display()

# Check available tables
spark.sql("SHOW TABLES IN samples.nyctaxi").display()
```

### Import External Datasets
```python
# From URL (CSV)
df = spark.read.csv("https://example.com/data.csv", header=True, inferSchema=True)

# From Python package
from sklearn import datasets
iris = datasets.load_iris()
```

---

# Part 5: AI Data Analyst Enterprise Patterns

## 5.1 Architecture Patterns

### Text-to-SQL Core Architecture

Modern AI Data Analyst systems are built on three foundational components: natural language understanding, SQL generation, and result interpretation.

#### Table-Augmented Generation (TAG) Framework

Unlike traditional RAG which primarily focuses on schema and template retrieval, **Table-Augmented Generation (TAG)** incorporates actual table data into the generation process:

- Retrieves sample rows from relevant tables
- Provides LLMs with concrete examples of data values, formats, and patterns
- Significantly improves accuracy over pure schema-based approaches

#### Multi-Agent Architectures

Production systems increasingly use **specialized LLM agents**:

| Agent | Responsibility |
|-------|----------------|
| Schema Understanding Agent | Interprets database structure, relationships, and semantics |
| SQL Generation Agent | Produces syntactically correct queries |
| Validation Agent | Verifies query correctness and security |
| Explanation Agent | Provides reasoning and summarization |

Multi-agent architectures show improved accuracy and explainability compared to single-model approaches.

### Semantic Layer Integration

The integration of LLMs with enterprise semantic layers represents a **proven path to production-ready accuracy**:

- Snowflake Cortex Analyst + AtScale achieves 90%+ SQL accuracy on real-world use cases
- Semantic layers translate business terminology to technical schemas
- Enables consistent metric definitions across all queries

**Key Components:**
- Centralized metrics definition (YAML-based, versioned)
- Business context integration (ARR, CLV, gross margin)
- Schema simplification for AI consumption

### Databricks AI/BI Genie Architecture

Databricks' production-ready text-to-SQL implementation offers:

**Core Features:**
- Natural language interface for business users (no coding required)
- Unity Catalog integration for governance
- Conversation APIs for application integration
- Management APIs for CI/CD pipelines

**Capacity Specifications:**
- 20 questions/minute per workspace (UI)
- 5 questions/minute per workspace (API free tier)
- 10,000 conversations per Genie space
- 10,000 messages per conversation

**Best Practices:**
- Minimum 5 tested example SQL queries per space
- At least 5 benchmark questions based on anticipated user queries
- Treat spaces as long-term collaboration tools that accumulate knowledge

### Multi-Dimensional Summarization Pattern

For advanced analytics, the **multi-agent summarization framework** achieves:
- 83% faithfulness to underlying data
- 4.4/5 relevance scores for decision-critical insights
- Superior coverage of significant changes

**Agent Pipeline:**
1. Slicing Agent - Extracts relevant dimensions
2. Variance Detection Agent - Identifies significant changes
3. Context Construction Agent - Builds analytical context
4. Generation Agent - Produces natural language summaries

---

## 5.2 Enterprise Use Cases by Industry

### Airlines Industry

**Market Context:** Aviation analytics market projected to reach **$10.75 billion by 2032** (11.86% CAGR).

| Use Case | Example | Business Impact |
|----------|---------|-----------------|
| **Predictive Maintenance** | Delta Air Lines + Airbus Skywise + IBM | Reduced cancellations from 5,600 to <100 annually |
| **Revenue Optimization** | EasyJet AI-based pricing | 22% of total revenue from ancillaries |
| **Fuel Efficiency** | Qantas Constellation system | $90M+ annual savings (2% fuel reduction) |
| **Operations Automation** | Swissport AI baggage robots | Reduced manual sorting time |
| **Fraud Detection** | ML-based transaction analysis | Address 46% of travel-related fraud |

**Japan Airlines Case Study:** "Failure Prediction Project" (since 2016) uses big data from flight sensors to detect signs of failures before they occur.

**Southwest Implementation:** GE Aviation flight analytics for 700+ Boeing 737s, enabling cloud-based fuel consumption optimization.

### Construction Industry

**Market Context:** AI construction market will reach **$11.85 billion by 2029** (24.31% CAGR).

| Use Case | AI Application | ROI Timeline |
|----------|----------------|--------------|
| **Project Management** | Resource optimization, scheduling | 3-6 months |
| **Predictive Analytics** | Delay prediction, early warnings | Immediate |
| **Risk Management** | Contract analysis, pattern detection | 3-6 months |
| **Cost Optimization** | Material usage analysis | 15% total cost savings |
| **Safety Monitoring** | Video analytics + sensor data | Immediate |

**Key Technologies:**
- Machine Learning for timeline prediction
- Computer Vision for safety and progress tracking
- NLP for RFIs, daily logs, and contract analysis
- Predictive Analytics for maintenance and cost overruns

**Case Study - Shawmut Design and Construction:** AI-driven safety systems analyze site data and detect patterns associated with previous incidents, resulting in noticeable reduction in workplace injuries.

### Consumer Packaged Goods (CPG)

**Market Context:** $2.4 trillion US CPG market with operations across dozens of countries.

**Key AI Analytics Applications:**

| Area | Impact |
|------|--------|
| Demand Planning | Automated predictions save significant time |
| Trade Pricing | Dynamic contract terms optimization |
| Promotion Planning | Improved ROI measurement |
| Customer Segmentation | 360-degree customer view |

**BCG Research Finding:** AI and advanced analytics at scale generate **>10% revenue growth** through:
- More predictive demand forecasting
- More relevant local assortments
- Personalized consumer services
- Optimized marketing and promotion ROI
- Faster innovation cycles

**Maturity Note:** CPG ranks among the lowest in Digital & AI maturity compared to banking, retail, and high-tech sectors - presenting significant opportunity.

### Pharmaceutical Industry

**Key Impact Areas:**

| Use Case | Example | Business Value |
|----------|---------|----------------|
| Drug Discovery | Insilico Medicine | 18 months from target to candidate ($2.6M vs. typical $billions) |
| Clinical Trials | Patient matching, protocol optimization | Reduced trial duration |
| Commercial Analytics | Sales forecasting, territory optimization | 10%+ top/bottom line impact |
| Supply Chain | Demand forecasting, cold chain monitoring | Reduced waste |

**GlaxoSmithKline Insight:** An advanced analytics capability could deliver "at least a **10% net impact** from a top- and bottom-line perspective."

---

## 5.3 Production Challenges and Lessons Learned

### The Benchmark vs. Production Gap

**Critical Insight:** The gap between **86% benchmark accuracy** and **6% real-world accuracy** stems from:

| Challenge | Description |
|-----------|-------------|
| Schema Complexity | Enterprise data lakes contain millions of tables, 100+ column tables |
| Documentation Gaps | ELT practices mean sparse metadata and documentation |
| External Knowledge | Business rules scattered across unstructured documents |
| Query Scope | Tens of thousands of tables from diverse sources |
| Naming Conventions | Domain-specific, abbreviated, lengthy names |

### Key Production Lessons

#### Lesson 1: Metadata is the Foundation

One production deployment processed **100,000+ natural language queries** in 2024, analyzing **6 trillion+ rows** of real-world business data.

**Critical Success Factor:** Comprehensive metadata management, not just LLM capability.

#### Lesson 2: Multi-Agent Framework for Production

Post-launch requirements extend beyond text-to-SQL:
- Query writing
- Data finding
- Query fixing
- Follow-up handling
- Code explanation

**Solution:** Intent-specific agents for each common use case.

#### Lesson 3: Error Handling is Critical

Robust systems require:
- Automated schema discovery when initial queries fail
- Query correction based on execution output
- Self-reflection and regeneration capabilities

### Common Failure Modes

| Failure Mode | Root Cause | Mitigation |
|--------------|------------|------------|
| Incorrect JOINs | Missing relationship documentation | Semantic layer with explicit relationships |
| Wrong aggregations | Ambiguous business terminology | Metric definitions in semantic layer |
| Filter errors | Date/time format mismatches | Sample data in context |
| Security violations | Missing access controls | Pre-query permission validation |
| Performance issues | Unbounded queries | Query complexity limits |

---

## 5.4 Data Engineering Layer Requirements

### Lakehouse as the Foundation

The data lakehouse architecture provides the unified foundation for AI Data Analysts:

**Core Components:**

| Layer | Technology | Purpose |
|-------|------------|---------|
| Storage | S3, GCS, Azure Blob | Low-cost, scalable foundation |
| Table Format | Delta Lake, Iceberg, Hudi | ACID transactions, time travel |
| Compute | Spark, Photon | Distributed processing |
| Catalog | Unity Catalog | Governance, lineage, discovery |
| Semantic | dbt, Looker, AtScale | Business logic, metrics |

### Essential Data Engineering Capabilities

#### For AI-Ready Data:

1. **Schema Documentation**
   - Table and column descriptions
   - Relationship documentation
   - Sample values for categorical columns

2. **Data Quality**
   - Automated validation rules
   - Data freshness monitoring
   - Completeness checks

3. **Semantic Layer**
   - Centralized metric definitions
   - Business glossary
   - Calculation logic

4. **Access Patterns**
   - Pre-built aggregations for common queries
   - Materialized views for performance
   - Query history for optimization

### Required Team Skills

| Role | Key Skills |
|------|------------|
| Data Engineer | Pipelines, streaming, Spark, open formats |
| Analytics Engineer | dbt, SQL, semantic modeling |
| Data Scientist | Python, ML frameworks, evaluation |
| Platform Engineer | Cloud infrastructure, security, networking |

### Databricks-Specific Requirements

For AI/BI Genie deployment:

- **Unity Catalog**: Required for governance and metadata
- **SQL Warehouse**: Serverless recommended for best performance
- **Table Documentation**: Rich descriptions in Unity Catalog
- **Sample Values**: Curated examples for key columns
- **Access Controls**: Fine-grained permissions at table/column level

---

## 5.5 Demo Datasets and Scenarios

### Best Demo Datasets

#### Option 1: Retail/E-Commerce Dataset

**Why It Works:**
- Universally understood business domain
- Rich analytical scenarios (sales, inventory, customers)
- Clear metrics (revenue, conversion, AOV)

**Recommended Tables:**
- `orders` - Transaction history
- `order_items` - Line-level details
- `products` - Product catalog
- `customers` - Customer demographics
- `inventory` - Stock levels by location
- `promotions` - Marketing campaigns

**Demo Questions:**
1. "What were our top 10 products by revenue last quarter?"
2. "Which customer segments have the highest lifetime value?"
3. "Show me inventory levels for products with less than 2 weeks of stock"
4. "Compare conversion rates across marketing channels"
5. "What's the trend in average order value by month?"

#### Option 2: Airline Operations Dataset

**Why It Works:**
- Complex operational metrics
- Time-series patterns (delays, maintenance)
- Multiple stakeholders (ops, finance, customer service)

**Recommended Tables:**
- `flights` - Flight schedules and actuals
- `delays` - Delay causes and durations
- `aircraft` - Fleet information
- `maintenance` - Service records
- `bookings` - Passenger reservations
- `weather` - Conditions by airport/time

**Demo Questions:**
1. "What percentage of flights were delayed last month by cause?"
2. "Which aircraft have the highest maintenance costs?"
3. "Show on-time performance trend by route"
4. "Predict which flights are at risk of delay today"
5. "What's our fuel efficiency by aircraft type?"

#### Option 3: Construction Project Dataset

**Why It Works:**
- Project-based analytics
- Budget vs. actual tracking
- Safety and compliance metrics

**Recommended Tables:**
- `projects` - Project master data
- `tasks` - Work breakdown structure
- `costs` - Budget and actuals
- `resources` - Labor and equipment
- `incidents` - Safety events
- `change_orders` - Scope changes

### Demo Scenario Patterns

#### Pattern A: Executive Dashboard Drill-Down

1. Start with high-level KPIs
2. Ask follow-up questions to investigate anomalies
3. Demonstrate conversational context retention
4. Show natural language explanation of findings

#### Pattern B: Ad-Hoc Investigation

1. Present a business problem (e.g., "Revenue dropped last week")
2. Use natural language to explore hypotheses
3. Demonstrate multi-table JOINs without SQL knowledge
4. Show comparison against historical periods

#### Pattern C: Self-Service Reporting

1. Business user needs a specific report
2. Describe requirements in natural language
3. AI generates SQL and results
4. User refines with follow-up questions

### Evaluation Dataset Guidelines

**Minimum Requirements:**
- At least **30 evaluation cases per agent**
- Coverage of success cases, edge cases, and failure scenarios
- Balanced class frequencies
- Version-controlled with changelogs

**Best Practices:**
- Start systematic logging from day one
- Curate test cases during feature development
- Establish clear quality criteria early
- Build human review workflows proactively

---

## 5.6 Evaluation Metrics

### Core Metrics

#### Exact Match (EM) / Exact Set Match (ESM)

**Definition:** Decomposes each SQL into clauses and conducts set comparison.

**Limitation:** False negatives - semantically equivalent queries with different syntax fail.

Example of equivalent queries that would fail EM:
```sql
-- Query A
SELECT * FROM table WHERE age > 25

-- Query B (semantically identical, different syntax)
SELECT * FROM table WHERE 25 < age
```

#### Execution Accuracy (EX)

**Definition:** Output SQL is correct if it returns identical results to the reference.

**Limitation:** False positives - different queries may coincidentally produce identical results on specific data.

**Current Benchmarks (2025-2026):**
| Model | Complex Query Accuracy |
|-------|----------------------|
| Grok-3 | 80% |
| GPT-4o | 72% |
| Deepseek-R1 | 71% |
| Claude Sonnet | 68% |

#### Test Suite Accuracy

**Definition:** Validates queries across multiple diverse database instances generated through systematic fuzzing.

**Advantage:** Dramatically reduces false positives from execution accuracy.

**Status:** Official evaluation metric for Spider, SParC, and CoSQL since November 2020.

### Benchmark Overview

#### Spider 1.0
- **Focus:** Complex, cross-domain text-to-SQL
- **Achievement:** 91.2% by current state-of-the-art
- **Limitation:** Toy schemas, single-dialect SQL

#### Spider 2.0
- **Focus:** Enterprise-realistic workflows
- **Current Performance:** Only 21.3% success rate
- **Innovations:** Massive schema complexity, multi-dialect SQL, agentic interfaces

#### BIRD Benchmark
- **Innovation:** Valid Efficiency Score (VES)
- **Purpose:** Measures efficiency alongside correctness
- **Use Case:** Production systems where query performance matters

### Production Evaluation Framework

For enterprise deployments, evaluate across multiple dimensions:

| Dimension | Metrics |
|-----------|---------|
| Accuracy | Execution accuracy, semantic correctness |
| Efficiency | Query execution time, resource utilization |
| Usability | User satisfaction, task completion rate |
| Reliability | Error rate, recovery success |
| Security | Access control violations, data leakage |

**Databricks Genie Benchmarks:**
- Curated test questions with expected SQL answers
- Systematic evaluation over time
- "Ask for Review" feature for continuous improvement

---

## 5.7 Security and Governance

### Access Control Framework

#### Role-Based Access Controls (RBAC)

Implement granular controls at all stages:

| Layer | Control |
|-------|---------|
| User Level | Authentication, authorization |
| Data Level | Table/column permissions |
| Query Level | Result filtering, aggregation enforcement |
| Model Level | Which AI models can access which data |

**Zero Trust Approach:** Apply continuous authentication across all AI workflow stages.

### Data Protection

#### Key Concerns

**#1 Concern:** Overexposed data when using generative AI solutions.

**Risks:**
- Unintended disclosure of employee compensation
- Exposure of unannounced product plans
- Customer PII in query responses
- Regulatory violations (GDPR, CCPA)

#### Mitigation Strategies

1. **Metadata Labeling**
   - Flag sensitive data before training
   - Automated classification tools for PII, financial data

2. **Query Validation**
   - Validate user access before processing
   - Enforce application-level access controls

3. **Data Masking**
   - Dynamic masking in query results
   - Anonymization for aggregated outputs

### Compliance Frameworks

**Relevant Regulations:**
- NIST AI RMF
- EU AI Act
- OWASP Top 10 for LLMs
- NIST Adversarial Machine Learning
- Industry-specific (HIPAA, SOX, PCI-DSS)

**Key Requirements:**
- Model decision traceability
- Audit logging for all queries
- Data lineage documentation
- Bias monitoring and mitigation

### Unity Catalog Integration

Databricks' governance layer provides:

- **Fine-grained access controls**: Table, column, row-level
- **Data lineage**: Track data flow through transformations
- **Audit logging**: Complete query history
- **Compliance**: Built-in regulatory support

---

## 5.8 ROI and Business Value Frameworks

### Current State of AI ROI

**Reality Check:**
- 2023: Enterprise AI initiatives achieved only **5.9% ROI** with 10% capital investment
- 2024: **74% of organizations** report advanced AI projects meeting/exceeding ROI expectations
- Challenge: **97% of enterprises** still face difficulties demonstrating value from early-stage AI

**Gartner Finding:** Nearly half of business leaders say proving generative AI's business value is the **single biggest hurdle** to adoption.

### ROI Categories

#### Hard ROI (Tangible)

| Category | Metric | Typical Impact |
|----------|--------|----------------|
| Labor Cost Reduction | Analyst hours saved | 40-60% reduction in routine queries |
| Faster Decision Making | Time to insight | 10x faster than traditional BI |
| Error Reduction | Query accuracy | Fewer incorrect business decisions |
| Self-Service Adoption | IT ticket reduction | 30-50% fewer data requests |

#### Soft ROI (Intangible)

| Category | Benefit |
|----------|---------|
| Employee Experience | Reduced frustration with data access |
| Data Democratization | More users making data-driven decisions |
| Innovation Velocity | Faster hypothesis testing |
| Competitive Advantage | Quicker response to market changes |

### Measurement Framework

#### Step 1: Establish Baselines

**Before Implementation:**
- Average time to answer data questions
- Number of IT/analyst tickets for data requests
- Accuracy of current reporting
- User satisfaction with data access

#### Step 2: Define Success Metrics

| Timeframe | Metric Type | Examples |
|-----------|-------------|----------|
| 30 days | Adoption | Active users, queries per day |
| 90 days | Efficiency | Time saved, tickets reduced |
| 180 days | Accuracy | Query correctness, user validation |
| 1 year | Business Impact | Revenue influence, cost savings |

#### Step 3: Account for Complexity

**Challenge:** AI changes how work happens, making impact isolation difficult.

**Solution:** Use proxy metrics and controlled pilots.

### Industry-Specific Value Frameworks

#### Airlines
| Metric | Target |
|--------|--------|
| Maintenance cost reduction | 15-20% |
| Delay prediction accuracy | >80% |
| Fuel optimization | 2-5% savings |
| Customer service resolution | 30% faster |

#### Construction
| Metric | Target |
|--------|--------|
| Project cost savings | 15% of total |
| Safety incident reduction | 20-30% |
| Schedule optimization | 10% improvement |
| Change order reduction | 25% fewer |

#### CPG
| Metric | Target |
|--------|--------|
| Revenue growth | >10% |
| Forecast accuracy | 50% improvement |
| Promotion ROI | 11% improvement |
| Time to insight | 10x faster |

#### Pharmaceutical
| Metric | Target |
|--------|--------|
| Top/bottom line impact | 10%+ |
| Drug discovery time | 50% reduction |
| Clinical trial efficiency | 20% improvement |
| Commercial planning accuracy | 30% improvement |

### Workshop ROI Demonstration

**For Demo Purposes:**

1. **Before/After Scenario**
   - Show traditional workflow: request ticket, wait for analyst, receive report
   - Show AI-powered workflow: ask question, get instant answer

2. **Time Savings Calculator**
   ```
   Annual Value = (Questions/Day) x (Time Saved/Question) x
                  (Hourly Rate) x (Working Days/Year)
   ```

3. **Democratization Multiplier**
   - Every business user becomes data-capable
   - 10x more questions asked = 10x more decisions informed by data

---

## Summary: Key Takeaways for Workshop

### Architecture
- Use semantic layer as foundation for production accuracy
- Multi-agent architectures provide flexibility and specialization
- Databricks AI/BI Genie offers production-ready implementation

### Industry Applications
- Airlines: Predictive maintenance, revenue optimization
- Construction: Project management, safety, cost control
- CPG: Demand planning, personalization, promotion optimization
- Pharmaceutical: Drug discovery acceleration, commercial analytics

### Success Factors
1. Start with comprehensive metadata and semantic layer
2. Plan for multi-agent architecture from the beginning
3. Build evaluation framework before deployment
4. Implement security and governance from day one
5. Set realistic ROI expectations (12-24 month horizon)

### Demo Strategy
1. Use universally understood datasets (retail, airline)
2. Show progressive complexity: simple query to investigation
3. Demonstrate conversational context retention
4. Highlight governance and security features
5. Connect to business value with ROI framework

---

# Appendix: All Sources

## Official Databricks Documentation

### Genie Spaces / AI/BI
- [What is an AI/BI Genie space (AWS)](https://docs.databricks.com/aws/en/genie/)
- [Set up and manage an AI/BI Genie space (AWS)](https://docs.databricks.com/aws/en/genie/set-up)
- [Curate an effective Genie space (Best Practices)](https://docs.databricks.com/aws/en/genie/best-practices)
- [Build a knowledge store for more reliable Genie spaces](https://docs.databricks.com/aws/en/genie/knowledge-store)
- [Use a Genie space to explore business data](https://docs.databricks.com/aws/en/genie/talk-to-genie)
- [Genie spaces with dashboards](https://docs.databricks.com/aws/en/dashboards/genie-spaces)
- [AI/BI release notes 2025](https://docs.databricks.com/aws/en/ai-bi/release-notes/2025)
- [Troubleshoot Genie spaces](https://docs.databricks.com/aws/en/genie/troubleshooting)
- [What is an AI/BI Genie space (Azure)](https://learn.microsoft.com/en-us/azure/databricks/genie/)

### Agent Framework & MCP
- [Model Context Protocol (MCP) on Databricks](https://docs.databricks.com/aws/en/generative-ai/mcp/)
- [Host custom MCP servers using Databricks apps](https://docs.databricks.com/aws/en/generative-ai/mcp/custom-mcp)
- [Use Databricks managed MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp)
- [Create AI agent tools using Unity Catalog functions](https://docs.databricks.com/aws/en/generative-ai/agent-framework/create-custom-tool)
- [Deploy an agent for generative AI applications](https://docs.databricks.com/aws/en/generative-ai/agent-framework/deploy-agent)
- [Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/)
- [Multi-Agent Supervisor](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [AI Gateway introduction](https://docs.databricks.com/aws/en/ai-gateway/)
- [Integrate LangChain with Databricks Unity Catalog tools](https://docs.databricks.com/aws/en/generative-ai/agent-framework/langchain-uc-integration)
- [Agent system design patterns](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns)

### LangGraph Integration
- [Tutorial: Build, evaluate, and deploy a retrieval agent](https://docs.databricks.com/aws/en/generative-ai/tutorials/agent-framework-notebook)
- [Author AI agents in code](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)
- [Tracing LangGraph](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/integrations/langgraph)
- [LangChain on Databricks](https://docs.databricks.com/aws/en/large-language-models/langchain)
- [Use Genie in multi-agent systems](https://docs.databricks.com/aws/en/generative-ai/agent-framework/multi-agent-genie)
- [Genie Conversation API](https://docs.databricks.com/aws/en/genie/conversation-api)
- [Build and trace retriever tools](https://docs.databricks.com/aws/en/generative-ai/agent-framework/unstructured-retrieval-tools)

### Free Tier & Setup
- [Databricks Free Edition Limitations (AWS)](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
- [Databricks Free Edition Limitations (Azure)](https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-edition-limitations)
- [Databricks Free Trial (AWS)](https://docs.databricks.com/aws/en/getting-started/free-trial)
- [Databricks Free Trial (Azure)](https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial)
- [Databricks Sample Datasets (AWS)](https://docs.databricks.com/aws/en/discover/databricks-datasets)
- [Unity Catalog Overview](https://www.databricks.com/product/unity-catalog)

## Databricks Blog Posts
- [AI/BI Genie is now Generally Available](https://www.databricks.com/blog/aibi-genie-now-generally-available)
- [What's New in AI/BI - October 2025 Roundup](https://www.databricks.com/blog/whats-new-aibi-october-2025-roundup)
- [Mosaic AI Announcements at Data + AI Summit 2025](https://www.databricks.com/blog/mosaic-ai-announcements-data-ai-summit-2025)
- [Multi-Agent Supervisor Architecture: Orchestrating Enterprise AI at Scale](https://www.databricks.com/blog/multi-agent-supervisor-architecture-orchestrating-enterprise-ai-scale)
- [MLflow 3.0: Build, Evaluate, and Deploy Generative AI with Confidence](https://www.databricks.com/blog/mlflow-30-unified-ai-experimentation-observability-and-governance)
- [Accelerate AI Development with Databricks: Discover, Govern, and Build with MCP and Agent Bricks](https://www.databricks.com/blog/accelerate-ai-development-databricks-discover-govern-and-build-mcp-and-agent-bricks)
- [Announcing Advanced Security and Governance in Mosaic AI Gateway](https://www.databricks.com/blog/new-updates-mosaic-ai-gateway-bring-security-and-governance-genai-models)
- [Announcing Genie Conversation APIs](https://www.databricks.com/blog/genie-conversation-apis-public-preview)
- [Reranking in Mosaic AI Vector Search](https://www.databricks.com/blog/reranking-mosaic-ai-vector-search-faster-smarter-retrieval-rag-agents)

## LangChain/LangGraph Documentation
- [LangChain Databricks Integration](https://python.langchain.com/docs/integrations/providers/databricks/)
- [Databricks Unity Catalog Tools](https://python.langchain.com/docs/integrations/tools/databricks/)
- [Databricks Vector Search](https://python.langchain.com/docs/integrations/vectorstores/databricks_vector_search/)
- [Build a custom RAG agent with LangGraph](https://docs.langchain.com/oss/python/langgraph/agentic-rag)

## MLflow Resources
- [LangGraph with Model From Code](https://mlflow.org/blog/langgraph-model-from-code)
- [MLflow Tracing Integrations](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/integrations/)

## Community & Industry Resources
- [Community Edition Retirement Announcement](https://community.databricks.com/t5/announcements/psa-community-edition-retires-at-the-end-of-2025-move-to-free/td-p/141888)
- [Free Edition FAQs - Databricks Community](https://community.databricks.com/t5/databricks-university-alliance/free-edition-frequently-asked-questions-faqs-consolitated/ta-p/128500)
- [CloudLabs Databricks Lab Quick Start Guide](https://cloudlabs.ai/blog/cloudlabs-databricks-lab-quick-start-guide/)

## Enterprise Use Case References
- [Symphony Solutions - Airline Data Analytics](https://symphony-solutions.com/insights/data-analytics-airline-industry)
- [AltexSoft - AI Airlines](https://www.altexsoft.com/blog/engineering/ai-airlines/)
- [Mastt - 43 AI Use Cases in Construction](https://www.mastt.com/blogs/ai-use-cases-in-construction)
- [BCG - Unlocking Growth in CPG with AI](https://www.bcg.com/publications/2018/unlocking-growth-cpg-ai-advanced-analytics)
- [PwC - Advanced Analytics in Pharmaceutical Industry](https://www.pwc.com/us/en/industries/health-industries/health-research-institute/commercial-pharma-analytics.html)

## Technical References
- [Promethium - LLM & AI Models for Text-to-SQL](https://promethium.ai/guides/llm-ai-models-text-to-sql/)
- [Cube Blog - Semantic Layer and AI](https://cube.dev/blog/semantic-layer-and-ai-the-future-of-data-querying-with-natural-language)
- [Dataherald - Why Enterprise NL-to-SQL is Hard](https://medium.com/dataherald/why-enterprise-natural-language-to-sql-is-hard-8849414f41c)
- [Yale - Spider Challenge](https://yale-lily.github.io/spider)
- [AI Multiple - Text-to-SQL Comparison 2026](https://research.aimultiple.com/text-to-sql/)
- [Atlan - Data Governance for AI](https://atlan.com/know/data-governance/for-ai/)
- [BigID - AI Security & Governance](https://bigid.com/ai-security-governance/)
- [Agility at Scale - ROI of Enterprise AI](https://agility-at-scale.com/implementing/roi-of-enterprise-ai/)
- [Querio - Measuring ROI of AI in BI](https://querio.ai/articles/measuring-roi-ai-bi-key-metrics)

---

**Document Version:** 1.0
**Last Updated:** January 26, 2026
**Total Research Sources:** 60+
**Confidence Level:** High (based on official documentation, blog posts, and community sources)
