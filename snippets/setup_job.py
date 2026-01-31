# Run Workshop Setup as a Databricks Job — copy-paste into a Databricks notebook cell
#
# Submits a one-time multi-task job that runs the setup notebooks in sequence:
#   00a_setup_data  →  (optionally) 00b_setup_rag  →  00c_setup_genie
#
# Serverless compute is used by default (no cluster config needed).
# To use an existing cluster instead, set EXISTING_CLUSTER_ID below.

# ── Configuration ────────────────────────────────────────────────────────────
CATALOG = "workshop"  # Unity Catalog name
DATASET = "velocity_motors"  # velocity_motors | star_schema | super_table | all
GENIE_SPACES = "all"  # domain | unified | all
SETUP_RAG = False  # Set True to include RAG Vector Search setup
EXISTING_CLUSTER_ID = ""  # Leave empty for serverless, or set a cluster ID
# ─────────────────────────────────────────────────────────────────────────────

import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import (
    NotebookTask,
    RunIf,
    Source,
    SubmitTask,
    TaskDependency,
)

w = WorkspaceClient()

# ── Resolve paths ────────────────────────────────────────────────────────────
user = w.current_user.me().user_name
notebook_base = f"/Workspace/Users/{user}/ai-data-analyst-workshop/notebooks"

# Auto-discover a running SQL Warehouse for Genie setup
warehouse_id = ""
try:
    for wh in w.warehouses.list():
        state = str(wh.state).replace("State.", "")
        if state == "RUNNING":
            warehouse_id = wh.id
            print(f"Auto-selected warehouse: {wh.name} ({wh.id})")
            break
    if not warehouse_id:
        warehouses = list(w.warehouses.list())
        if warehouses:
            warehouse_id = warehouses[0].id
            print(f"No running warehouse found, defaulting to: {warehouses[0].name}")
except Exception as e:
    print(f"Could not auto-discover warehouses: {e}")

if not warehouse_id:
    raise ValueError("No SQL Warehouse found. Set warehouse_id manually:\n  warehouse_id = 'your-warehouse-id'")

parent_path = f"{notebook_base}/genie-space"

# ── Compute config ───────────────────────────────────────────────────────────
# Serverless: omit cluster config entirely. Existing cluster: pass the ID.
cluster_kwargs = {}
if EXISTING_CLUSTER_ID:
    cluster_kwargs = {"existing_cluster_id": EXISTING_CLUSTER_ID}
    print(f"Using existing cluster: {EXISTING_CLUSTER_ID}")
else:
    print("Using serverless compute")

# ── Build tasks ──────────────────────────────────────────────────────────────
tasks = []

# Task 1: Setup Data (always runs)
tasks.append(
    SubmitTask(
        task_key="setup_data",
        notebook_task=NotebookTask(
            notebook_path=f"{notebook_base}/00a_setup_data",
            base_parameters={
                "1_dataset": DATASET,
                "2_catalog": CATALOG,
            },
            source=Source.WORKSPACE,
        ),
        timeout_seconds=1800,
        **cluster_kwargs,
    )
)

# Task 2 (optional): Setup RAG
if SETUP_RAG:
    tasks.append(
        SubmitTask(
            task_key="setup_rag",
            depends_on=[TaskDependency(task_key="setup_data")],
            notebook_task=NotebookTask(
                notebook_path=f"{notebook_base}/00b_setup_rag",
                base_parameters={
                    "1_catalog": CATALOG,
                    "2_schema": "rag",
                    "3_endpoint_name": "rag-workshop-endpoint",
                    "4_embedding_model": "databricks-bge-large-en",
                },
                source=Source.WORKSPACE,
            ),
            timeout_seconds=1800,
            **cluster_kwargs,
        )
    )

# Task 3: Setup Genie Spaces
genie_depends_on = "setup_rag" if SETUP_RAG else "setup_data"
tasks.append(
    SubmitTask(
        task_key="setup_genie",
        depends_on=[TaskDependency(task_key=genie_depends_on)],
        run_if=RunIf.NONE_FAILED,
        notebook_task=NotebookTask(
            notebook_path=f"{notebook_base}/00c_setup_genie",
            base_parameters={
                "1_warehouse_id": warehouse_id,
                "2_catalog": CATALOG,
                "3_parent_path": parent_path,
                "4_spaces": GENIE_SPACES,
            },
            source=Source.WORKSPACE,
        ),
        timeout_seconds=600,
        **cluster_kwargs,
    )
)

# ── Submit ───────────────────────────────────────────────────────────────────
run_name = f"workshop-setup-{int(time.time())}"
print(f"\nSubmitting job '{run_name}' with {len(tasks)} tasks...")
for t in tasks:
    print(f"  → {t.task_key}")

waiter = w.jobs.submit(run_name=run_name, tasks=tasks)

run_id = waiter.run_id
run_info = w.jobs.get_run(run_id)
print(f"\nRun submitted! run_id = {run_id}")
print(f"Monitor: {run_info.run_page_url}")
print("\nWaiting for completion (this may take several minutes)...")

# ── Wait & report ────────────────────────────────────────────────────────────
result = waiter.result()
state = result.state.result_state.value if result.state.result_state else "UNKNOWN"

print(f"\n{'=' * 60}")
print(f"SETUP {'COMPLETE' if state == 'SUCCESS' else 'FAILED'}")
print(f"{'=' * 60}")

for task in result.tasks or []:
    task_state = task.state.result_state.value if task.state and task.state.result_state else "SKIPPED"
    icon = "+" if task_state == "SUCCESS" else ("-" if task_state == "SKIPPED" else "x")
    print(f"  [{icon}] {task.task_key}: {task_state}")

if state == "SUCCESS":
    print("\nAll setup notebooks completed successfully!")
    print(f"Your Genie Spaces are ready in: {parent_path}")
else:
    msg = result.state.state_message if result.state else "Unknown error"
    print(f"\nRun failed: {msg}")
    print(f"Check the run details: {run_info.run_page_url}")
