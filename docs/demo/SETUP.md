# Workshop Setup

Get from zero to running the demo in three steps: **download**, **load data**, **deploy Genie Spaces**.

---

## Prerequisites

| Requirement | Details |
|---|---|
| Databricks workspace | Unity Catalog enabled ([Free Trial](https://www.databricks.com/try-databricks) works) |
| SQL Warehouse | Any running warehouse (Serverless or Pro) |
| Permissions | CREATE CATALOG *or* write access to an existing catalog |
| Cluster | DBR 14.3+ with `databricks-langchain` installed |

> **Community Edition will not work** — it does not support Unity Catalog or Genie Spaces.

---

## Step 1: Download Workshop Materials

Paste this into a Databricks notebook cell and run it:

```python
import json, os, subprocess, urllib.request

REPO = "compassanalytics/ai-data-analyst-demo"
VERSION = "latest"

user = spark.sql("SELECT current_user()").first()[0]
target = f"/Workspace/Users/{user}/ai-data-analyst-workshop"

# Resolve latest version
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
    except Exception:
        version = "v1.0"

url = f"https://github.com/{REPO}/releases/download/workshop-{version}/workshop-materials-{version}.tar.gz"
print(f"Downloading {version} to {target} ...")
os.makedirs(target, exist_ok=True)
r = subprocess.run(
    f"curl -sL {url} | tar -xz -C {target} --strip-components=1",
    shell=True, capture_output=True, text=True,
)
if r.returncode != 0:
    raise RuntimeError(f"Download failed: {r.stderr}")
print(f"Workshop materials ready at: {target}")
```

After running, you should see the `notebooks/`, `src/`, `docs/` folders in your user workspace.

---

## Step 2: Load Data into Unity Catalog

Open **`notebooks/00a_setup_data.ipynb`** and run all cells.

### What it does

1. Creates a Unity Catalog and staging volume
2. Downloads 23 parquet files (Velocity Motors, Star Schema, Super Table)
3. Loads them as Delta tables
4. Adds column descriptions for Genie AI

### Configuration widgets

| Widget | Default | Description |
|---|---|---|
| **Dataset** | `all` | Which dataset(s) to load. Use `all` for the full demo. |
| **Catalog** | `workshop` | Target catalog name. Use an existing one if you can't create catalogs. |

### What gets loaded

| Dataset | Schema(s) | Tables | Purpose |
|---|---|---|---|
| velocity_motors | `sales`, `crm`, `operations` | 16 | Main demo dataset |
| star_schema | `analytics` | 6 | Clean data demo |
| super_table | `demo` | 1 | Dirty data demo |

### Verify

The notebook's final cell prints row counts per table. All 23 tables should show `OK`.

> **Can't create a catalog?** Run `SHOW CATALOGS` in a notebook cell, pick one you have access to (e.g., `main`), and enter that name in the Catalog widget.

---

## Step 3: Deploy Genie Spaces

Open **`notebooks/00c_setup_genie.ipynb`** and run all cells.

### What it does

1. Reads YAML configuration files from `infra/configs/`
2. Creates up to 6 Genie Spaces via the Databricks API
3. Outputs space IDs to use in the demo notebooks

### Configuration widgets

| Widget | Default | Description |
|---|---|---|
| **SQL Warehouse ID** | Auto-detected | The warehouse Genie uses to execute queries |
| **Catalog** | `workshop` | Must match what you used in Step 2 |
| **Parent Path** | Auto-populated | Workspace folder where Genie Spaces are created |
| **Spaces to Deploy** | `all` | Which spaces to create (`domain`, `unified`, `star_schema`, `super_table`, `all`) |

### Spaces deployed

| Space | Tables | Used in |
|---|---|---|
| Velocity Motors - Sales Analytics | 8 | Notebook 01 (Step 2-3) |
| Velocity Motors - Customer Intelligence | 4 | Notebook 01 (Step 3) |
| Velocity Motors - Operations & Inventory | 4 | Notebook 01 (Step 3) |
| Velocity Motors - Unified Analytics | 16 | Notebook 01 (Step 1-2) |
| Star Schema Analytics | 6 | Dirty vs Clean demo |
| Super Table Demo | 1 | Dirty vs Clean demo |

### After deployment

1. Copy the **Unified Analytics** space ID into notebook 01's `genie_space_id` widget
2. Copy the 3 domain space IDs into notebook 01's `DOMAIN_SPACES` list (cell 43)
3. **Important**: Open each space in the Genie UI and configure join keys between related tables (the API doesn't support this yet)

---

## Step 4: Verify Everything Works

Before the demo, run this quick check in a notebook cell:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
print(f"Connected to: {w.config.host}")

# List Genie Spaces
spaces = w.genie.list_spaces()
for space in spaces.spaces:
    if space.title.startswith("Velocity"):
        print(f"  {space.title}: {space.space_id}")
```

You should see your deployed spaces listed.

### Install notebook dependencies

The demo notebook installs this automatically (cell 2), but you can pre-install on your cluster:

```python
%pip install -qU databricks-langchain
```

---

## Troubleshooting

### "Authentication failed"
- Inside Databricks notebooks, auth is automatic (U2M). No token needed.
- If you see errors, ensure your cluster is running and attached to the notebook.

### "Catalog not found" or "Permission denied"
- You may not have CREATE CATALOG permission. Use an existing catalog instead.
- Run `SHOW CATALOGS` to see what's available.

### "Genie Space not found"
- Verify the space ID is correct (32-character hex string).
- Check you have **CAN USE** permission on the space.
- Space IDs change if you re-deploy — re-run `00c_setup_genie` and copy new IDs.

### "Download failed" (Step 1)
- Some workspaces block outbound internet. Try a non-serverless cluster.
- Alternative: Clone the repo with `git clone` if you have repository access.

### Genie returns errors or empty results
- Ensure the SQL Warehouse attached to the Genie Space is running.
- Rate limits: ~5 API queries/minute. Add `time.sleep(2)` between calls if hitting limits.
- If Genie says "I don't know", the join keys may not be configured — check the Genie Space UI.

### "Module not found: databricks_langchain"
- Run `%pip install -qU databricks-langchain` and restart the Python environment.

---

## File Map

```
ai-data-analyst-workshop/
  notebooks/
    00a_setup_data.ipynb          <-- Step 2: Load data
    00b_setup_rag.ipynb           <-- (Optional: Vector Search for RAG)
    00c_setup_genie.ipynb         <-- Step 3: Deploy Genie Spaces
    01_genie_sdk_demo.ipynb       <-- Main demo notebook (fill-in)
    02_multi_genie_orchestration.ipynb  <-- Bonus take-home
    03_build_your_agent.ipynb     <-- Take-home challenge
  docs/
    demo/SETUP.md                 <-- You are here
    demo/DEMO_GUIDE.md            <-- Follow-along guide
    demo/APPENDIX.md              <-- SDK reference
  infra/configs/                  <-- Genie Space YAML configs
  src/                            <-- Full agent codebase (reference)
  snippets/setup_download.py      <-- Alternative download script
```
