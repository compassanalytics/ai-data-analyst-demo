# Databricks Asset Bundles (DABs)

Infrastructure-as-code for deploying notebooks, jobs, and code to Databricks workspaces.

## Triggers
- "databricks bundle"
- "dabs"
- "deploy to databricks"
- "databricks.yml"

## Bundle Structure

```
project/
├── databricks.yml          # Bundle configuration
├── src/                    # Python code
├── notebooks/              # Jupyter notebooks
└── resources/              # Additional YAML configs (optional)
```

## databricks.yml Template

```yaml
bundle:
  name: my-project

variables:
  warehouse_id:
    description: "SQL Warehouse ID"
    default: "your-warehouse-id"

workspace:
  root_path: /Workspace/Users/${workspace.current_user.userName}/${bundle.name}

sync:
  include:
    - src/**
    - notebooks/**

resources:
  jobs:
    my_job:
      name: "My Job"
      tasks:
        - task_key: run_notebook
          notebook_task:
            notebook_path: notebooks/demo.ipynb
            warehouse_id: ${var.warehouse_id}

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://your-workspace.cloud.databricks.com

  prod:
    mode: production
    workspace:
      host: https://your-workspace.cloud.databricks.com
```

## Commands

```bash
# Set profile for authentication
export DATABRICKS_CONFIG_PROFILE="my-profile"

# Validate configuration
databricks bundle validate -t dev

# Deploy to workspace
databricks bundle deploy -t dev

# Run a job
databricks bundle run my_job -t dev

# Destroy deployed resources
databricks bundle destroy -t dev
```

## Key Learnings

### Free Tier / Serverless Only
For workspaces that only support serverless compute, use `warehouse_id` instead of `new_cluster`:

```yaml
# DON'T use new_cluster on serverless-only workspaces
tasks:
  - task_key: run_notebook
    notebook_task:
      notebook_path: notebooks/demo.ipynb
      warehouse_id: ${var.warehouse_id}  # Use warehouse instead
```

### Variables
```yaml
variables:
  my_var:
    description: "Description"
    default: "default_value"

# Use in config:
warehouse_id: ${var.my_var}
```

### Sync Include/Exclude
```yaml
sync:
  include:
    - src/**
    - notebooks/**
  exclude:
    - "**/__pycache__"
    - ".venv/**"
```

### Target-Specific Overrides
```yaml
targets:
  dev:
    variables:
      mock_mode: "true"
  prod:
    variables:
      mock_mode: "false"
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `RESOURCE_ALREADY_EXISTS` | Delete conflicting file: `databricks workspace delete "/path"` |
| `Only serverless compute supported` | Use `warehouse_id` instead of `new_cluster` |
| `host doesn't match` | Hardcode host in targets instead of using env vars |

## Tips

1. **Always validate before deploy**: `databricks bundle validate -t dev`
2. **Use targets** for dev/prod separation
3. **Files sync to**: `/Workspace/.../files/` subdirectory
4. **Notebooks accessible at**: `files/notebooks/name` (no .ipynb extension)
