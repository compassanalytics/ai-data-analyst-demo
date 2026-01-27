# Databricks CLI

Authentication and common commands for working with Databricks workspaces.

## Triggers
- "databricks cli"
- "databricks auth"
- "connect to databricks"
- "databricks workspace"

## Authentication

### OAuth Login (Recommended)
```bash
# Create/refresh a profile with OAuth
databricks auth login --host https://your-workspace.cloud.databricks.com --profile my-profile

# This opens browser for authentication and stores refresh token
```

### Check Auth Status
```bash
# Verify token is valid
databricks auth token --profile my-profile

# If expired, re-run auth login
```

### Profile Configuration
Profiles are stored in `~/.databrickscfg`:
```ini
[my-profile]
host      = https://dbc-xxxxx.cloud.databricks.com/
auth_type = databricks-cli
```

### Environment Variables
For scripts and CI/CD:
```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_CONFIG_PROFILE="my-profile"
```

## Common Commands

### Workspace Operations
```bash
# List workspace contents
databricks workspace list /Workspace/Users/user@example.com --profile my-profile

# Create directory
databricks workspace mkdirs /Workspace/Users/user@example.com/my-folder --profile my-profile

# Import notebook
databricks workspace import "/Workspace/path/notebook" \
  --file local/notebook.ipynb \
  --format JUPYTER \
  --overwrite \
  --profile my-profile

# Delete file/folder
databricks workspace delete "/Workspace/path/to/delete" --profile my-profile
```

### Catalog Operations
```bash
# List catalogs
databricks catalogs list --profile my-profile

# List schemas in catalog
databricks schemas list my_catalog --profile my-profile

# List tables (requires 2 args: catalog schema)
databricks tables list my_catalog my_schema --profile my-profile
```

### SQL Warehouses
```bash
# List warehouses
databricks warehouses list --profile my-profile
```

### Raw API Calls
```bash
# For APIs without dedicated CLI commands
databricks api get /api/2.0/genie/spaces --profile my-profile
databricks api post /api/2.0/genie/spaces --json '{"title": "..."}' --profile my-profile
```

## Tips

1. **Always specify --profile** to avoid confusion with multiple workspaces
2. **Token expiry**: OAuth tokens expire; re-run `auth login` when needed
3. **Path format**: Workspace paths start with `/Workspace/`
4. **Free tier**: Only supports serverless compute
