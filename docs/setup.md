# AI Data Analyst Demo - Setup Guide

This guide covers local development setup and Databricks deployment.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for Python environment management
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) for deployment
- Access to a Databricks workspace with Genie Spaces enabled

## Local Development

### 1. Clone and Setup Environment

```bash
cd research_dbx_demo

# Create virtual environment and install dependencies
uv sync

# Or install dependencies directly
uv pip install -e .
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Databricks connection
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token

# Genie Space configuration
GENIE_SPACE_ID=your-genie-space-id

# Model endpoint (optional, defaults to Llama 3.3 70B)
MODEL_ENDPOINT=databricks-meta-llama-3-3-70b-instruct

# Enable mock mode for testing without real Genie access
MOCK_MODE=true

# Optional: Vector Search configuration
# VECTOR_SEARCH_ENDPOINT=your-vs-endpoint
# VECTOR_SEARCH_INDEX=your-vs-index
```

### 3. Run in Mock Mode

For testing without Databricks access:

```bash
MOCK_MODE=true uv run python -c "
from src.config import Config
from src.agents.supervisor import create_simple_supervisor

config = Config.from_env()
supervisor = create_simple_supervisor(config)
response = supervisor.query('What are our top 10 products by revenue?')
print(response)
"
```

### 4. Run Tests

```bash
uv run pytest
```

## Databricks Deployment

### 1. Configure Databricks CLI

```bash
# Configure authentication
databricks configure --host https://your-workspace.cloud.databricks.com

# Or use environment variables
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-token
```

### 2. Set Bundle Variables

Edit `databricks.yml` or set via CLI:

```bash
# Validate the bundle
databricks bundle validate -t dev

# Deploy to dev target (mock mode enabled)
databricks bundle deploy -t dev

# Deploy to prod target (real Genie)
databricks bundle deploy -t prod \
  --var genie_space_id=your-space-id \
  --var model_endpoint=databricks-meta-llama-3-3-70b-instruct
```

### 3. Create Databricks Secrets (Optional)

For production deployments, use Databricks secrets:

```bash
# Create secret scope
databricks secrets create-scope ai-data-analyst

# Add secrets
databricks secrets put-secret ai-data-analyst genie_space_id --string-value "your-space-id"
databricks secrets put-secret ai-data-analyst model_endpoint --string-value "databricks-meta-llama-3-3-70b-instruct"
databricks secrets put-secret ai-data-analyst mock_mode --string-value "false"
```

### 4. Run the Demo Notebook

After deployment:

1. Navigate to `/Workspace/Users/your-email/ai-data-analyst-demo/notebooks/demo`
2. Attach to a cluster with the required libraries
3. Run all cells

Or run via the job:

```bash
databricks bundle run demo_setup -t dev
```

## Genie Space Setup

### Option A: Infrastructure-as-Code (Recommended)

The project includes an IaC CLI for managing Genie Spaces via YAML configuration files.

#### Prerequisites

```bash
# Ensure dependencies are installed
uv sync

# Set required environment variables
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-personal-access-token
export WAREHOUSE_ID=your-sql-warehouse-id
```

#### Deploy a New Space

```bash
# Deploy from the sample configuration
uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml

# Preview what would be created (dry run)
uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml --dry-run
```

#### Update an Existing Space

```bash
# Update a space by its ID
uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml --update SPACE_ID
```

#### Other CLI Commands

```bash
# List all Genie Spaces
uv run python infra/cli.py list

# Get details of a specific space
uv run python infra/cli.py get SPACE_ID

# Export a space to YAML (useful for importing existing spaces into IaC)
uv run python infra/cli.py export SPACE_ID --output my_space.yaml

# Delete a space (moves to trash)
uv run python infra/cli.py delete SPACE_ID
```

#### Configuration File Format

Create a YAML file (see `infra/configs/sample_genie_space.yaml` for a full example):

```yaml
title: "My Analytics Space"
description: "AI-powered analytics"
warehouse_id: "${WAREHOUSE_ID}"  # Environment variable substitution
parent_path: "/Workspace/Shared/genie-spaces"

tables:
  - identifier: "catalog.schema.table1"
  - identifier: "catalog.schema.table2"

sample_questions:
  - id: "q1"
    question: ["What were our total sales?"]

instructions: |
  Business rules and context for the AI...

join_specs:
  - left_table: "catalog.schema.table1"
    right_table: "catalog.schema.table2"
    join_keys: ["join_column"]

example_sqls:
  - question: "Total sales"
    sql: |
      SELECT SUM(amount) FROM catalog.schema.table1
```

### Option B: Manual UI Setup

1. In your Databricks workspace, navigate to **SQL > Genie Spaces**
2. Click **Create Genie Space**
3. Select the tables/views to include
4. Configure the space name and description
5. Copy the Space ID from the URL (format: `spaces/abc123/conversations`)

### Required Permissions

- Genie Space: CAN USE permission
- Underlying tables: SELECT permission
- Model endpoint: CAN QUERY permission

## Troubleshooting

### "Genie Space not found" Error

- Verify the `GENIE_SPACE_ID` is correct
- Check you have CAN USE permission on the space
- Ensure the space is in the same workspace as your connection

### "Model endpoint not available" Error

- Verify the model endpoint exists in your workspace
- Check you have CAN QUERY permission
- Try using a different endpoint: `databricks-meta-llama-3-1-70b-instruct`

### Slow Query Response

- Genie queries can take 30-60 seconds for complex questions
- Consider increasing the timeout in `genie_agent.query()`
- Enable mock mode for faster demo iteration

### Import Errors in Notebook

Ensure all dependencies are installed:

```python
%pip install databricks-sdk>=0.40.0 databricks-langchain>=0.1.0 langgraph>=0.2.0
```

## Architecture Overview

```
User Question
      │
      ▼
┌─────────────────────┐
│  Supervisor Agent   │  (LangGraph + ChatDatabricks)
│  Routes based on    │
│  question intent    │
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌────────┐  ┌────────┐
│ Genie  │  │  RAG   │
│ Agent  │  │ Agent  │
│ (Data) │  │ (Docs) │
└────────┘  └────────┘
```

The supervisor uses function calling to route queries:
- **query_data**: Routes to Genie for SQL/analytics questions
- **search_documents**: Routes to RAG for policy/documentation questions
