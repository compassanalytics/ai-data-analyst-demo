# AI Data Analyst Workshop

**By Compass x Databricks**

Build AI-powered data analysts using Databricks Genie Spaces and LangGraph.

## Workshop Overview

This hands-on workshop teaches you to build AI data analysts that can:

- Answer business questions in natural language
- Query structured data via Genie Spaces
- Search documents via RAG (Retrieval-Augmented Generation)
- Orchestrate multiple AI agents for complex workflows

**Duration:** 30 min presentation + 2.5 hour hands-on demo

**Audience:** Non-technical, semi-technical, and technical participants

## Workshop Structure

| Part       | Focus                                                               | Audience  |
| ---------- | ------------------------------------------------------------------- | --------- |
| **Part 1** | Genie Spaces UI - What works, what breaks, why data quality matters | Everyone  |
| **Part 2** | Genie as a LangGraph node - Building multi-agent systems            | Technical |
| **Part 3** | Multi-Genie + Report Generator - Advanced orchestration             | Technical |

## Quick Start

### Prerequisites

- Databricks account with Unity Catalog enabled ([Free Edition](https://www.databricks.com/learn/free-edition) works — Community Edition does **not**)
- A running SQL Warehouse (Serverless or Pro)

### Step 1: Download Workshop Materials

Create a new notebook in your Databricks workspace and paste this into the first cell:

```python
# Download AI Data Analyst Workshop materials
import json, os, subprocess, urllib.request

REPO = "compassanalytics/ai-data-analyst-demo"
VERSION = "latest"

user = spark.sql("SELECT current_user()").first()[0]
target = f"/Workspace/Users/{user}/ai-data-analyst-workshop"

# Resolve latest version
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

# Download and extract
url = f"https://github.com/{REPO}/releases/download/workshop-{version}/workshop-materials-{version}.tar.gz"
print(f"Downloading {version} to {target} ...")
os.makedirs(target, exist_ok=True)
r = subprocess.run(f"curl -sL {url} | tar -xz -C {target} --strip-components=1", shell=True, capture_output=True, text=True)
if r.returncode != 0:
    raise RuntimeError(f"Download failed: {r.stderr}")

for item in sorted(os.listdir(target)):
    p = os.path.join(target, item)
    info = f"/ ({len(os.listdir(p))} items)" if os.path.isdir(p) else f" ({os.path.getsize(p):,} bytes)"
    print(f"  {item}{info}")
print(f"\nWorkshop materials ready at: {target}")
```

Run the cell — all workshop materials will be unpacked into your workspace.

### Step 2: Run Setup Notebooks

Open each setup notebook in order and click **Run All**:

| Order | Notebook | What It Does |
|-------|----------|-------------|
| 1 | `notebooks/00a_setup_data.ipynb` | Loads 16 tables into Unity Catalog |
| 2 | `notebooks/00b_setup_rag.ipynb` | Creates Vector Search index for policy documents |
| 3 | `notebooks/00c_setup_genie.ipynb` | Deploys Genie Spaces via Infrastructure-as-Code |

**Or run all setup as a single job** — paste this into a new notebook cell:

```python
# Run Workshop Setup as a Databricks Job (serverless)
import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import NotebookTask, RunIf, Source, SubmitTask, TaskDependency

CATALOG = "workshop"
DATASET = "all"  # velocity_motors | star_schema | super_table | all
GENIE_SPACES = "all"         # domain | unified | all
SETUP_RAG = False             # Set True to include RAG Vector Search setup
EXISTING_CLUSTER_ID = ""      # Leave empty for serverless

w = WorkspaceClient()
user = w.current_user.me().user_name
nb = f"/Workspace/Users/{user}/ai-data-analyst-workshop/notebooks"
parent_path = f"{nb}/genie-space"

# Auto-discover a SQL Warehouse
warehouse_id = ""
for wh in w.warehouses.list():
    if str(wh.state).replace("State.", "") == "RUNNING":
        warehouse_id, _ = wh.id, print(f"Auto-selected warehouse: {wh.name} ({wh.id})")
        break
if not warehouse_id:
    whs = list(w.warehouses.list())
    if whs:
        warehouse_id, _ = whs[0].id, print(f"Defaulting to: {whs[0].name}")
if not warehouse_id:
    raise ValueError("No SQL Warehouse found. Set warehouse_id manually.")

ck = {"existing_cluster_id": EXISTING_CLUSTER_ID} if EXISTING_CLUSTER_ID else {}

tasks = [SubmitTask(task_key="setup_data", notebook_task=NotebookTask(
    notebook_path=f"{nb}/00a_setup_data", source=Source.WORKSPACE,
    base_parameters={"1_dataset": DATASET, "2_catalog": CATALOG}), timeout_seconds=1800, **ck)]

if SETUP_RAG:
    tasks.append(SubmitTask(task_key="setup_rag", depends_on=[TaskDependency(task_key="setup_data")],
        notebook_task=NotebookTask(notebook_path=f"{nb}/00b_setup_rag", source=Source.WORKSPACE,
        base_parameters={"1_catalog": CATALOG, "2_schema": "rag",
        "3_endpoint_name": "rag-workshop-endpoint", "4_embedding_model": "databricks-bge-large-en"}),
        timeout_seconds=1800, **ck))

tasks.append(SubmitTask(task_key="setup_genie",
    depends_on=[TaskDependency(task_key="setup_rag" if SETUP_RAG else "setup_data")],
    run_if=RunIf.NONE_FAILED, notebook_task=NotebookTask(
    notebook_path=f"{nb}/00c_setup_genie", source=Source.WORKSPACE,
    base_parameters={"1_warehouse_id": warehouse_id, "2_catalog": CATALOG,
    "3_parent_path": parent_path, "4_spaces": GENIE_SPACES}), timeout_seconds=600, **ck))

run_name = f"workshop-setup-{int(time.time())}"
print(f"\nSubmitting '{run_name}' with {len(tasks)} tasks...")
waiter = w.jobs.submit(run_name=run_name, tasks=tasks)
print(f"Run submitted! run_id = {waiter.run_id}")
print(f"Monitor: {w.jobs.get_run(waiter.run_id).run_page_url}")
print("Waiting for completion...")

result = waiter.result()
state = result.state.result_state.value if result.state.result_state else "UNKNOWN"
print(f"\nSETUP {'COMPLETE' if state == 'SUCCESS' else 'FAILED'}")
for t in result.tasks or []:
    s = t.state.result_state.value if t.state and t.state.result_state else "SKIPPED"
    print(f"  [{'+'if s=='SUCCESS' else 'x'}] {t.task_key}: {s}")
```

### Step 3: Run Workshop Notebooks

| Part | Notebook | Type | Focus |
|------|----------|------|-------|
| 1 | `01_agent_basics.ipynb` | Interactive | Genie + RAG multi-agent with progressive query difficulty |
| 2 | `02_multi_genie_orchestration.ipynb` | Showcase | Parallel multi-Genie queries, LangGraph concepts, report generation |
| 3 | `03_build_your_agent.ipynb` | Take-home (optional) | Build your own Genie + RAG agent from scratch |

See [WORKSHOP_GUIDE.md](WORKSHOP_GUIDE.md) for the full step-by-step guide with configuration details.

## Repository Structure

```
ai-data-analyst-workshop/
├── notebooks/              # Workshop notebooks (00a-00c setup, 01-03 exercises)
├── src/                    # Agent code, benchmark, evaluation, demo, workshop
├── dataset_generators/     # Generate Velocity Motors sample data (16 tables)
├── config/                 # Dataset schemas and Genie Space configurations
├── infra/                  # Genie Space Infrastructure-as-Code manager + configs
├── snippets/               # Condensed copy-paste setup scripts for Databricks
├── scripts/                # Setup, deployment, and testing scripts
├── tests/                  # Unit tests
├── docs/                   # Workshop documentation
└── databricks.yml          # Databricks Asset Bundle config
```

## Documentation

- [Workshop Guide](WORKSHOP_GUIDE.md) - Full step-by-step participant walkthrough
- [Setup Guide](docs/SETUP.md) - Environment setup details
- [Architecture](docs/ARCHITECTURE.md) - How the agents work
- [Genie Best Practices](docs/GENIE_BEST_PRACTICES.md) - Data quality and Knowledge Store

## Key Concepts

### Why Data Quality Matters

In Part 1, we demonstrate:

- **Dirty data** (139 columns, inconsistent naming) → Genie gets confused
- **Clean data** (star schema, 6 tables) → Same questions work perfectly

The AI didn't change. The data did.

### Multi-Agent Architecture

```
User Question
      │
      ▼
┌─────────────────────┐
│  Supervisor Agent   │  Routes based on intent
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌────────┐
│ Genie  │  │  RAG   │
│ (Data) │  │ (Docs) │
└────────┘  └────────┘
```

## Resources

- [Databricks Genie Spaces Documentation](https://docs.databricks.com/aws/en/genie/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Databricks Free Edition](https://www.databricks.com/learn/free-edition)
