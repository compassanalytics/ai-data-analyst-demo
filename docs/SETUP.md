# Workshop Setup Guide

This guide helps you set up your environment for the AI Data Analyst Workshop.

## Prerequisites

- **Databricks Account** - [Free Edition](https://www.databricks.com/learn/free-edition) (no credit card required)
- **Python 3.10+** - For local development
- **uv** - Python environment manager ([install guide](https://docs.astral.sh/uv/))

## Option A: Databricks Only (Recommended for Non-Technical)

If you just want to follow along with the Genie Spaces UI demo (Part 1):

### 1. Create Databricks Free Edition Account

1. Go to [Databricks Free Edition](https://www.databricks.com/learn/free-edition)
2. Sign up with your email
3. Complete the workspace setup

### 2. Access Genie Spaces

1. In your workspace, click **Genie** in the left sidebar
2. You're ready for Part 1!

### 3. Import Workshop Data

**Option A: Use built-in sample data**
- Databricks includes sample datasets like `samples.tpch.*`
- No upload needed

**Option B: Upload workshop data**
1. Download the data files from the workshop repository
2. Navigate to **Catalog** > **Create Table**
3. Upload the parquet files

---

## Option B: Full Setup (For Technical Parts)

For Parts 2 and 3, you'll need the full codebase.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/ai-data-analyst-workshop.git
cd ai-data-analyst-workshop
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .  # Or with uv: uv pip install -e .
```

### 3. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your Databricks credentials:

```env
# Required
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token

# For Part 2+
GENIE_SPACE_ID=your-genie-space-id

# Optional (defaults work for most cases)
MODEL_ENDPOINT=databricks-meta-llama-3-3-70b-instruct
MOCK_MODE=false
```

### 4. Get Your Databricks Token

1. In Databricks, click your profile icon (top right)
2. Select **Settings**
3. Go to **Developer** > **Access tokens**
4. Click **Generate new token**
5. Copy the token to your `.env` file

### 5. Find Your Genie Space ID

1. Navigate to **Genie** in Databricks
2. Open a Genie Space
3. Copy the ID from the URL: `spaces/[THIS-IS-THE-ID]/conversations`

---

## Generate Sample Data

The workshop includes data generators for the "dirty vs clean" demo.

### Generate Star Schema (Clean Data)

```bash
uv run python dataset_generators/star_schema_generator.py
```

Creates 6 well-structured tables:
- `dim_date` - Fiscal calendar
- `dim_product` - Products with hierarchy
- `dim_customer` - Customer segments
- `dim_store` - Distribution centers
- `dim_promotion` - Campaigns
- `fact_sales` - Sales transactions

### Generate Super Table (Dirty Data)

```bash
uv run python dataset_generators/super_table_generator.py
```

Creates 1 messy table with 139 columns demonstrating anti-patterns:
- 7 different revenue columns
- Cryptic codes (ENT, MID, SMB)
- Inconsistent date formats
- Mixed boolean representations

---

## Data Setup (Recommended)

Use the automated setup notebook to load workshop data with column descriptions for Genie AI.

### Quick Start

1. Open `notebooks/00b_setup_data.ipynb` in Databricks
2. Configure widgets:
   - **Dataset**: Choose `velocity_motors`, `star_schema`, `super_table`, or `all`
   - **Catalog**: Name of the Unity Catalog to create/use (default: `workshop`)
3. Run all cells
4. Verify data loaded (row counts shown in verification cell)
5. Create your Genie Space using the loaded tables

### Requirements

- **Databricks with Unity Catalog** (not Community Edition)
- Permission to create catalogs OR use an existing catalog

> **Note:** Databricks Community Edition does not support Unity Catalog.
> Use the [Free Trial](https://www.databricks.com/try-databricks) for full Unity Catalog features.

### Finding Your Catalog

If you cannot create new catalogs, use an existing one:

1. Run in a notebook cell: `SHOW CATALOGS`
2. Pick a catalog you have access to (e.g., `main`, `hive_metastore`)
3. Enter that name in the Catalog widget

### What Gets Loaded

| Dataset | Catalog.Schema | Tables | Description |
|---------|---------------|--------|-------------|
| velocity_motors | workshop.sales, .crm, .operations | 16 | Automotive dealership data |
| star_schema | workshop.analytics | 6 | Clean dimensional model |
| super_table | workshop.demo | 1 | Messy data for anti-pattern demo |

### Column Descriptions

The setup notebook automatically adds column comments to all tables, which helps Genie AI understand your data better. These descriptions are sourced from `config/dataset_schemas.py`.

---

## Manual Data Upload (Alternative)

If the automated setup does not work, you can manually upload data.

### Using the Databricks UI

1. Go to **Catalog** > **Create Table**
2. Select **Upload file**
3. Upload each parquet file from `dataset_generators/data/`
4. Choose your catalog and schema

### Using Databricks CLI

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure
databricks configure --host https://your-workspace.cloud.databricks.com

# Upload (example)
databricks fs cp dataset_generators/data/star_schema/ dbfs:/workshop/star_schema/ --recursive
```

---

## Create Genie Spaces

### For Part 1 Demo

Create two Genie Spaces:

1. **"Dirty Data Demo"**
   - Add only the `super_table`
   - Minimal configuration (no instructions)

2. **"Clean Data Demo"**
   - Add all 6 star schema tables
   - Add business instructions (see [GENIE_BEST_PRACTICES.md](GENIE_BEST_PRACTICES.md))

### For Parts 2 & 3

The technical demos use the API, so you'll need:
- At least one configured Genie Space
- The Space ID for your `.env` file

---

## Verify Setup

### Test Mock Mode (No Databricks Required)

```bash
MOCK_MODE=true uv run python -c "
from src.config import Config
from src.agents.supervisor import create_simple_supervisor

config = Config.from_env()
supervisor = create_simple_supervisor(config)
response = supervisor.query('What are our top products?')
print(response)
"
```

### Test Real Connection

```bash
uv run python -c "
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
print(f'Connected to: {w.config.host}')
print(f'Genie spaces: {len(list(w.genie.list_spaces()))}')
"
```

---

## Troubleshooting

### "Authentication failed"
- Check your `DATABRICKS_HOST` includes `https://`
- Verify your token hasn't expired
- Ensure token has correct permissions

### "Genie Space not found"
- Verify the Space ID is correct
- Check you have CAN USE permission
- Ensure the space exists in your workspace

### "Import errors"
- Run `uv sync` to install all dependencies
- Check Python version is 3.10+

### "Rate limit exceeded"
- Genie has rate limits (20 questions/minute UI, 5/minute API)
- Wait a moment and retry

---

## Next Steps

Once setup is complete:

1. **Part 1:** Open Genie in Databricks and try the demo queries
2. **Part 2:** Open `notebooks/01_agent_basics.ipynb`
3. **Part 3:** Open `notebooks/02_multi_genie_orchestration.ipynb`

See [ARCHITECTURE.md](ARCHITECTURE.md) to understand how the agents work.
