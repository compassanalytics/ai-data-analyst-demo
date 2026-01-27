# Genie Space Infrastructure-as-Code

Create and manage Databricks Genie Spaces programmatically via REST API.

## Triggers
- "genie space"
- "create genie"
- "genie iac"
- "ai/bi space"

## Overview

Genie Spaces can be created via the REST API (Beta). This project includes IaC tooling in `infra/`.

## CLI Usage

```bash
# Set environment
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_CONFIG_PROFILE="my-profile"

# Deploy from YAML config
uv run python infra/cli.py deploy infra/configs/my_space.yaml

# Dry run (preview without creating)
uv run python infra/cli.py deploy infra/configs/my_space.yaml --dry-run

# Update existing space
uv run python infra/cli.py deploy config.yaml --update SPACE_ID

# List all spaces
uv run python infra/cli.py list

# Get space details
uv run python infra/cli.py get SPACE_ID

# Export existing space to YAML
uv run python infra/cli.py export SPACE_ID --output my_space.yaml

# Delete space
uv run python infra/cli.py delete SPACE_ID
```

## YAML Configuration

```yaml
title: "My Analytics Space"
description: "AI-powered data analysis"
warehouse_id: "your-warehouse-id"
parent_path: "/Workspace/Users/user@example.com/genie-spaces"

tables:
  - identifier: "catalog.schema.table1"
  - identifier: "catalog.schema.table2"

sample_questions:
  - id: "q1"
    question: ["What are total sales by region?"]
  - id: "q2"
    question: ["Show top 10 customers"]

instructions: |
  Business context and rules go here.
  - All amounts in USD
  - Dates use YYYY-MM-DD format
```

## API Requirements (Learned)

The Genie API has specific requirements for `serialized_space`:

1. **Version required**: Must include `"version": 1`
2. **Tables must be sorted**: Alphabetically by identifier
3. **Question IDs must be UUIDs**: 32-char lowercase hex (no hyphens)

### Valid Structure
```json
{
  "version": 1,
  "data_sources": {
    "tables": [
      {"identifier": "catalog.schema.table1"},
      {"identifier": "catalog.schema.table2"}
    ]
  },
  "config": {
    "sample_questions": [
      {"id": "a1b2c3d4e5f6...", "question": ["Your question?"]}
    ]
  }
}
```

## REST API Endpoints

| Operation | Endpoint | Status |
|-----------|----------|--------|
| Create | `POST /api/2.0/genie/spaces` | Beta |
| Update | `PUT /api/2.0/genie/spaces/{id}` | Beta |
| Get | `GET /api/2.0/genie/spaces/{id}` | GA |
| List | `GET /api/2.0/genie/spaces` | GA |
| Delete | `DELETE /api/2.0/genie/spaces/{id}` | GA |

## Python SDK Usage

```python
from databricks.sdk import WorkspaceClient
import json

w = WorkspaceClient()

# Create space
response = w.api_client.do(
    method="POST",
    path="/api/2.0/genie/spaces",
    body={
        "title": "My Space",
        "warehouse_id": "warehouse-id",
        "parent_path": "/Workspace/Users/user@example.com/spaces",
        "serialized_space": json.dumps({
            "version": 1,
            "data_sources": {
                "tables": [{"identifier": "catalog.schema.table"}]
            }
        })
    }
)
space_id = response.get("space_id")
```

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Cannot find field: instructions` | Invalid top-level field | Remove `instructions` from serialized_space |
| `ExportConverter supports versions 1 and 2` | Missing version | Add `"version": 1` |
| `tables must be sorted` | Tables not alphabetical | Sort tables by identifier |
| `Expected lowercase 32-hex UUID` | Invalid question ID | Use MD5 hash or UUID without hyphens |
| `RESOURCE_DOES_NOT_EXIST` | Parent path missing | Create directory first with `workspace mkdirs` |

## Tips

1. **Create parent directory first**: `databricks workspace mkdirs "/path"`
2. **Use sample data**: `samples.tpch.*` tables available in most workspaces
3. **Instructions via UI**: Advanced instructions may need UI configuration
4. **Test with dry-run**: Always preview before creating
