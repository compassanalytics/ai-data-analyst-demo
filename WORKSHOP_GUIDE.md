# AI Data Analyst Workshop Guide

**By Compass x Databricks**

Build AI-powered data analysts using Databricks Genie Spaces and LangGraph.

---

## Prerequisites

- A **Databricks account** with Unity Catalog enabled
  - [Databricks Free Edition](https://www.databricks.com/learn/free-edition) works (no credit card required)
  - Note: Community Edition does **not** support Unity Catalog — use Free Edition or a paid workspace
- A running **SQL Warehouse** (Serverless or Pro)

---

## Step 1: Download Workshop Materials

All workshop code, notebooks, and configuration files are bundled in a single download script. You'll paste it into a Databricks notebook and run it — everything gets unpacked into your workspace automatically.

### 1.1 Create a New Notebook

In your Databricks workspace, click **New** > **Notebook**.

<!-- screenshot: creating a new notebook in Databricks -->

### 1.2 Paste the Download Script

Copy the entire block below and paste it into the first cell of your new notebook:

```python
# Download AI Data Analyst Workshop materials — copy-paste into a Databricks notebook cell

import json
import os
import subprocess
import urllib.request

REPO = "compassanalytics/ai-data-analyst-demo"
VERSION = "latest"  # or pin to e.g. "v1.5"
TARGET_PATH = None  # auto-detected if None

# --- resolve target path ---
IN_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ

if TARGET_PATH:
    target = TARGET_PATH
elif IN_DATABRICKS:
    user = spark.sql("SELECT current_user()").first()[0]  # noqa: F821
    target = f"/Workspace/Users/{user}/ai-data-analyst-workshop"
else:
    target = os.path.join(os.getcwd(), "ai-data-analyst-workshop")

# --- resolve version ---
version = VERSION

if version == "latest":
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/releases/latest",
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            tag = json.loads(resp.read().decode()).get("tag_name", "")
            version = tag.replace("workshop-", "") if tag.startswith("workshop-") else tag
    except Exception as e:
        print(f"Could not fetch latest version ({e}), falling back to v1.0")
        version = "v1.0"

# --- download & extract ---
url = f"https://github.com/{REPO}/releases/download/workshop-{version}/workshop-materials-{version}.tar.gz"
print(f"Downloading {version} to {target} ...")
os.makedirs(target, exist_ok=True)
r = subprocess.run(
    f"curl -sL {url} | tar -xz -C {target} --strip-components=1",
    shell=True,
    capture_output=True,
    text=True,
)

if r.returncode != 0:
    raise RuntimeError(f"Download failed: {r.stderr}\nCheck: https://github.com/{REPO}/releases")

# --- verify ---
expected = {"src", "notebooks", "scripts", "config", "data", "docs", "pyproject.toml", "README.md"}
actual = set(os.listdir(target))
missing = expected - actual

for item in sorted(actual):
    p = os.path.join(target, item)
    info = f"/ ({len(os.listdir(p))} items)" if os.path.isdir(p) else f" ({os.path.getsize(p):,} bytes)"
    print(f"  {item}{info}")

if missing:
    print(f"\n⚠ Missing: {sorted(missing)}")
else:
    print(f"\nWorkshop materials ready at: {target}")
```

### 1.3 Run the Cell

Click **Run All** or press **Shift+Enter**. The script will:

1. Fetch the latest release from GitHub
2. Download and extract the workshop bundle into your workspace
3. Print a file listing to confirm everything is in place

<!-- screenshot: successful download output showing file listing -->

You should see output listing folders like `src/`, `notebooks/`, `config/`, `infra/`, etc. with a final message: **"Workshop materials ready at: ..."**

> **Tip:** Note the target path printed in the output — you'll navigate to it to find the workshop notebooks.

---

## Step 2: Load Data into Unity Catalog

Open **`notebooks/00a_setup_data.ipynb`** from the workshop materials you just downloaded.

This notebook downloads the Velocity Motors dataset (16 tables across Sales, CRM, and Operations domains) and loads them into Unity Catalog with column descriptions that help Genie AI understand your data.

### 2.1 Configure Widgets

After running the first few cells, you'll see configuration widgets at the top of the notebook:

| Widget | What to Set |
|--------|-------------|
| **Dataset** | `velocity_motors` (default) — or `all` to include star_schema and super_table demos |
| **Catalog** | `workshop` (default) — or use an existing catalog you have access to |

<!-- screenshot: 00b notebook widgets -->

### 2.2 Run All Cells

Click **Run All**. The notebook will:

1. Create the catalog and staging volume
2. Download 16 parquet files from Azure Blob Storage
3. Create tables in Unity Catalog (`workshop.sales.*`, `workshop.crm.*`, `workshop.operations.*`)
4. Add column comments for Genie AI context

<!-- screenshot: 00b setup summary output showing tables loaded -->

### 2.3 Verify

The verification cell at the end shows row counts for every table. You should see all tables with data (e.g., `sales.orders: 100,000+ rows`).

> **Troubleshooting:** If you see connection errors, your workspace may block outbound connections (common with serverless compute on new accounts). Try using a **classic compute cluster** instead of serverless, or ask your admin to allow outbound HTTPS to `compassagentemofiles.blob.core.windows.net`.

---

## Step 3: Set Up RAG Vector Search

Open **`notebooks/00b_setup_rag.ipynb`**.

This notebook creates a Vector Search index over company policy documents (warranty, financing, HR policies, etc.) so the AI agent can answer questions about documents — not just data.

### 3.1 Configure Widgets

| Widget | What to Set |
|--------|-------------|
| **Catalog** | Same catalog as Step 2 (e.g., `workshop`) |
| **Schema** | `rag` (default) |
| **VS Endpoint** | `rag-workshop-endpoint` (default) — a new endpoint will be created |
| **Embedding Model** | `databricks-bge-large-en` (default) |

### 3.2 Run All Cells

Click **Run All**. The notebook will:

1. Create a `document_chunks` table in Unity Catalog
2. Create a Vector Search endpoint (this can take **5-15 minutes** if it's new)
3. Read and chunk markdown policy documents
4. Create a Delta Sync index with managed embeddings

<!-- screenshot: 00c setup complete output -->

### 3.3 Verify

The verification cell runs a test similarity search query. You should see matching document chunks returned with source files and preview text.

> **Note:** If the index is still syncing, wait a few minutes and re-run the verification cell.

---

## Step 4: Deploy Genie Spaces

Open **`notebooks/00c_setup_genie.ipynb`**.

This notebook deploys pre-configured Genie Spaces using Infrastructure-as-Code YAML definitions. Each space is tuned to a specific business domain.

### 4.1 Configure Widgets

| Widget | What to Set |
|--------|-------------|
| **SQL Warehouse ID** | Your warehouse ID (find it: SQL Warehouses page > click a warehouse > copy ID from URL) |
| **Catalog** | Same catalog as previous steps (e.g., `workshop`) |
| **Parent Path** | Workspace folder for Genie Spaces (e.g., `/Workspace/Users/your.email@company.com/genie-spaces`) |
| **Spaces to Deploy** | `domain` (default) — deploys 3 domain-specific spaces: Sales, CRM, Operations |

<!-- screenshot: 00d notebook widgets -->

### 4.2 Run All Cells

Click **Run All**. The notebook will:

1. Read YAML configs from `infra/configs/velocity_motors/`
2. Create Genie Spaces via the Databricks API
3. Output the deployed Space IDs

<!-- screenshot: 00d deployment summary -->

### 4.3 Note the Space IDs

The deployment summary prints Space IDs for each domain. **Copy these** — you'll need them in the demo notebooks.

```
Sales Analytics:        <space-id-1>
Customer Intelligence:  <space-id-2>
Operations & Inventory: <space-id-3>
```

> **Important (Beta API Limitation):** After deployment, you need to manually configure join specifications in each Genie Space UI:
> 1. Open each space in the Genie UI
> 2. Go to **Settings** > **Data**
> 3. Add join keys between related tables

---

## Setup Complete!

At this point your workshop environment is fully configured:

- **16 tables** loaded into Unity Catalog with column descriptions
- **Vector Search** index with company policy documents
- **3 Genie Spaces** deployed (Sales, CRM, Operations)

Now proceed to the demo notebooks in order.

---

## Part 1: Agent Basics

Open **`notebooks/01_agent_basics.ipynb`**.

This is the core demo notebook. It builds a multi-agent AI data analyst with:
- A **Genie Agent** that translates natural language to SQL
- A **RAG Agent** that searches company policy documents
- A **Supervisor** that routes questions to the right agent

### Configuration

Set the widgets at the top of the notebook:

| Widget | What to Set |
|--------|-------------|
| **Genie Space ID** | One of the Space IDs from Step 4 (e.g., the Sales space) |
| **Warehouse ID** | Your SQL Warehouse ID |
| **Model Endpoint** | `databricks-meta-llama-3-3-70b-instruct` (default) |
| **Mock Mode** | `false` for real queries, `true` for demo without Genie |
| **Vector Search Endpoint** | Endpoint name from Step 3 |
| **Vector Search Index** | `workshop.rag.document_index` (or your catalog/schema) |

### What You'll Explore

The notebook is organized by progressive difficulty:

1. **Simple Queries** — Single-table aggregations ("How many customers do we have?")
2. **Business Logic** — Domain understanding required ("Total revenue by payment method")
3. **Complex Analytics** — Multi-table joins, CTEs, window functions
4. **Where AI Struggles** — Three failure patterns:
   - Correct refusal (data doesn't exist)
   - Ambiguous concepts (no definition of "luxury")
   - Hallucination (general knowledge override)
5. **RAG Queries** — Policy and document retrieval ("What warranty coverage for CPO?")
6. **Combined Queries** — Questions that need both data AND documents

### Activities

- **Activity 1:** Pick a question from a menu (or write your own) and observe how the AI handles it
- **Activity 2:** Try to stump the AI — write adversarial questions that expose limitations
- **Activity 3:** Predict which agent (Genie, RAG, or Both) handles each question before running it

<!-- screenshot: 01 notebook output example -->

---

## Part 2: Multi-Genie Orchestration

Open **`notebooks/02_multi_genie_orchestration.ipynb`**.

This notebook demonstrates the full multi-agent pipeline: a single question gets decomposed, routed to multiple Genie Spaces in parallel, synthesized into cross-domain insights, and rendered as a report.

### Configuration

| Widget | What to Set |
|--------|-------------|
| **Sales Space ID** | Sales space from Step 4 |
| **Customers Space ID** | CRM space from Step 4 |
| **Inventory Space ID** | Operations space from Step 4 |
| **Warehouse ID** | Your SQL Warehouse ID |
| **Mock Mode** | `true` for demo, `false` for real queries |

### Pipeline Stages

| Stage | Agent | What It Does |
|-------|-------|-------------|
| **Planning** | PlannerAgent | Decomposes the question into domain-specific sub-queries |
| **Querying** | MultiGenieOrchestrator | Executes parallel queries across Genie Spaces |
| **Synthesizing** | SynthesizerAgent | Generates cross-domain insights and correlations |
| **Reporting** | ReportWriter | Produces Markdown and HTML dashboard outputs |

### What You'll Explore

1. **End-to-End Pipeline** — Watch all 4 stages execute with progress tracking
2. **Generated Reports** — View the Markdown and HTML dashboard output
3. **Step-Through Mode** — Execute each stage individually to inspect intermediate data
4. **Activity 1** — Ask your own cross-domain question and watch how routing changes
5. **Activity 2** — Add a 4th Genie Space (Operations) and re-run the pipeline

<!-- screenshot: 02 pipeline progress cards -->

---

## Part 3: Build Your Own Agent

Open **`notebooks/03_build_your_agent.ipynb`**.

This is the hands-on coding session. You'll build LangGraph agents from scratch using a fluent `AgentBuilder` API.

### Exercises

| Exercise | Focus | What You Do |
|----------|-------|-------------|
| **1. Calculator Tool** | Add your first tool | Uncomment code, fill in name and description |
| **2. Multi-Tool Routing** | Multiple tools with priorities | Add `date_helper`, set routing rules |
| **3. Conversation Memory** | Context retention | Enable `enable_memory()`, observe follow-ups |
| **4. Playground** | Free experimentation | Build your own agent with all tools |

### Key Concepts

- **Tools** are functions the agent can call (calculator, date helper, web search)
- **Routing Rules** map keywords to tools (mock mode uses these instead of an LLM)
- **Memory** preserves conversation history across queries
- **AgentBuilder** provides a fluent API that wraps LangGraph complexity

### Bonus Challenge

Create your own custom tool:

```python
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """Description of what your tool does."""
    return f"Processed: {query}"
```

<!-- screenshot: 03 exercise output -->

---

## Summary

| Step | Notebook | What You Did |
|------|----------|-------------|
| Setup | Download script | Downloaded workshop materials into your workspace |
| Setup | `00a_setup_data` | Loaded 16 tables into Unity Catalog |
| Setup | `00b_setup_rag` | Created Vector Search index for policy documents |
| Setup | `00c_setup_genie` | Deployed Genie Spaces via Infrastructure-as-Code |
| Part 1 | `01_agent_basics` | Built a multi-agent AI analyst (Genie + RAG + Supervisor) |
| Part 2 | `02_multi_genie_orchestration` | Ran parallel queries across 3+ Genie Spaces with report generation |
| Part 3 | `03_build_your_agent` | Built LangGraph agents from scratch |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Download script fails** | Check that your workspace has outbound internet access. Try on a classic (non-serverless) cluster. |
| **Connection errors in 00b** | Serverless compute may block external egress. Use a classic cluster or configure network policies. |
| **"Unity Catalog not enabled"** | You need Free Edition or a paid workspace — Community Edition doesn't support Unity Catalog. |
| **Vector Search endpoint slow** | First-time creation takes 5-15 minutes. The notebook polls and waits automatically. |
| **Genie returns wrong answers** | Check that join specs are configured in the Genie Space UI (beta API limitation). |
| **Import errors** | Make sure you ran the `%pip install` cell at the top of each notebook. |
| **"Rate limit exceeded"** | Genie has rate limits (20 questions/min UI, 5/min API). Wait and retry. |

For more details, see [troubleshooting.md](troubleshooting.md).
