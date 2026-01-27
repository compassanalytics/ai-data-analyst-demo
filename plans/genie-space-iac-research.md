# Research: Programmatic Databricks Genie Space Management (Infrastructure as Code)

**Research Date:** 2026-01-26
**Confidence Level:** High (based on official Databricks documentation and SDK sources)

---

## Research Summary

Databricks provides multiple approaches for programmatically creating and managing Genie Spaces. The **Genie Management APIs** (Create and Update) are in **Beta** as of 2025, enabling full infrastructure-as-code workflows. However, native Terraform support for Genie Spaces is currently limited.

---

## 1. Databricks REST API

### Key Findings

The Genie REST API provides full CRUD operations for Genie Spaces.

### API Endpoints

| Operation | Method | Endpoint | Status |
|-----------|--------|----------|--------|
| Create Space | POST | `/api/2.0/genie/spaces` | Beta |
| Update Space | PUT | `/api/2.0/genie/spaces/{space_id}` | Beta |
| Get Space | GET | `/api/2.0/genie/spaces/{space_id}` | GA |
| List Spaces | GET | `/api/2.0/genie/spaces` | GA |
| Trash Space | DELETE | `/api/2.0/genie/spaces/{space_id}` | GA |

### Create Space API - Full Specification

**Endpoint:** `POST /api/2.0/genie/spaces`

**Request Body:**
```json
{
  "title": "Sales Analytics Space",
  "description": "Space for analyzing sales performance and trends",
  "parent_path": "/Workspace/Users/<username>",
  "warehouse_id": "<warehouse-id>",
  "serialized_space": "<JSON string - see structure below>"
}
```

**Parameters:**
- `title` (string, optional) - Display name for the space
- `description` (string, optional) - Description of the Genie Space
- `parent_path` (string, optional) - Workspace folder path where the space will be registered
- `warehouse_id` (string, **required**) - SQL warehouse ID (pro or serverless recommended)
- `serialized_space` (string, **required**) - JSON string containing the space configuration

### Serialized Space Structure

```json
{
  "version": 1,
  "config": {
    "sample_questions": [
      {
        "id": "unique_identifier",
        "question": ["What were total sales last month?"]
      },
      {
        "id": "b2c3d4e5f6g7",
        "question": ["Show top 10 customers by revenue"]
      }
    ],
    "instructions": "Business rules and guidelines as a string"
  },
  "data_sources": {
    "tables": [
      {
        "identifier": "catalog.schema.table_name",
        "description": ["Description of the table purpose"],
        "column_configs": [
          {
            "column_name": "status",
            "get_example_values": true,
            "build_value_dictionary": true
          }
        ]
      }
    ]
  },
  "instructions": {
    "text_instructions": [
      {
        "id": "instruction_id",
        "content": ["Detailed business rules and calculation methods"]
      }
    ],
    "example_question_sqls": [
      {
        "id": "example_id",
        "question": ["Sample question text"],
        "sql": ["SELECT ... FROM ..."]
      }
    ],
    "join_specs": [
      {
        "id": "join_id",
        "left": {"identifier": "table1", "alias": "t1"},
        "right": {"identifier": "table2", "alias": "t2"},
        "sql": ["t1.id = t2.id"]
      }
    ],
    "sql_snippets": {
      "filters": [],
      "expressions": [],
      "measures": []
    }
  }
}
```

### Complete Create Space Example (curl)

```bash
curl -X POST "https://<DATABRICKS_INSTANCE>/api/2.0/genie/spaces" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales Analytics Space",
    "description": "Space for analyzing sales performance and trends",
    "parent_path": "/Workspace/Users/analyst@company.com",
    "warehouse_id": "abc123def456",
    "serialized_space": "{\"version\":1,\"config\":{\"sample_questions\":[{\"id\":\"q1\",\"question\":[\"What were total sales last month?\"]},{\"id\":\"q2\",\"question\":[\"Show top 10 customers by revenue\"]},{\"id\":\"q3\",\"question\":[\"Compare sales by region for Q1 vs Q2\"]},{\"id\":\"q4\",\"question\":[\"Which products have the highest return rate?\"]},{\"id\":\"q5\",\"question\":[\"Show monthly revenue trend for the past year\"]}],\"instructions\":\"This space analyzes sales data from our e-commerce platform. All monetary values are in USD. Use the orders and customers tables for transactional data.\"},\"data_sources\":{\"tables\":[{\"identifier\":\"sales.analytics.orders\"},{\"identifier\":\"sales.analytics.customers\"},{\"identifier\":\"sales.analytics.products\"}]}}"
  }'
```

### Response Example

```json
{
  "space_id": "3c409c00b54a44c79f79da06b82460e2",
  "title": "Sales Analytics Space",
  "description": "Space for analyzing sales performance and trends",
  "warehouse_id": "abc123def456",
  "serialized_space": "..."
}
```

---

## 2. Databricks SDK for Python

### Key Findings

The Databricks SDK provides the `GenieAPI` class for Genie operations. As of the current SDK version, the Python SDK primarily supports **conversation operations** and **read operations** for spaces. The create/update space methods may need to be called via raw API requests.

### Available SDK Methods

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# List all Genie Spaces
spaces = w.genie.list_spaces(page_size=100)
for space in spaces.spaces:
    print(f"Space: {space.title} (ID: {space.space_id})")

# Get details of a specific space
space = w.genie.get_space(space_id="<space_id>")

# Move a space to trash
w.genie.trash_space(space_id="<space_id>")

# Start a conversation
message = w.genie.start_conversation_and_wait(
    space_id="<space_id>",
    content="What were total sales last month?"
)

# Create a message in existing conversation
w.genie.create_message(
    space_id="<space_id>",
    conversation_id="<conversation_id>",
    content="Break that down by region"
)
```

### Creating a Space via SDK (using raw API)

Since create_space may not be directly exposed as a high-level method, use the SDK's API client:

```python
from databricks.sdk import WorkspaceClient
import json

w = WorkspaceClient()

# Prepare the serialized space configuration
space_config = {
    "version": 1,
    "config": {
        "sample_questions": [
            {"id": "q1", "question": ["What were total sales last month?"]},
            {"id": "q2", "question": ["Show top 10 customers by revenue"]},
            {"id": "q3", "question": ["Compare sales by region"]},
            {"id": "q4", "question": ["Which products have highest returns?"]},
            {"id": "q5", "question": ["Monthly revenue trend"]}
        ],
        "instructions": "Sales analytics space. All amounts in USD."
    },
    "data_sources": {
        "tables": [
            {"identifier": "sales.gold.orders"},
            {"identifier": "sales.gold.customers"},
            {"identifier": "sales.gold.products"}
        ]
    }
}

# Create the space using the API client
response = w.api_client.do(
    method="POST",
    path="/api/2.0/genie/spaces",
    body={
        "title": "Sales Analytics Space",
        "description": "Analyze sales performance and trends",
        "parent_path": "/Workspace/Users/analyst@company.com",
        "warehouse_id": "<warehouse_id>",
        "serialized_space": json.dumps(space_config)
    }
)

print(f"Created space with ID: {response['space_id']}")
```

### Using databricks-ai-bridge Library

For more advanced Genie interactions in applications:

```python
from databricks_ai_bridge.genie import Genie
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
genie = Genie(space_id="<space_id>", client=w, return_pandas=False)

# Ask a question
response = genie.ask_question("What were total sales last month?")
print(response.result)
```

---

## 3. Databricks Terraform Provider

### Key Findings

**There is NO dedicated `databricks_genie_space` resource** in the Terraform provider as of January 2026. However, related resources exist:

### Available AI/BI Resources

| Resource | Purpose |
|----------|---------|
| `databricks_dashboard` | Manages AI/BI Dashboards (automatically creates companion Genie space) |
| `databricks_aibi_dashboard_embedding_access_policy_setting` | Controls dashboard embedding policy |
| `databricks_aibi_dashboard_embedding_approved_domains_setting` | Specifies approved embedding domains |

### databricks_dashboard Resource

When you create an AI/BI dashboard, Databricks **automatically creates a companion Genie space**. This is currently the only way to create a Genie space via Terraform.

```hcl
data "databricks_sql_warehouse" "starter" {
  name = "Starter Warehouse"
}

resource "databricks_dashboard" "sales_dashboard" {
  display_name         = "Sales Analytics Dashboard"
  warehouse_id         = data.databricks_sql_warehouse.starter.id
  parent_path          = "/Shared/analytics"
  embed_credentials    = false

  # Option 1: Inline JSON
  serialized_dashboard = jsonencode({
    pages = [
      {
        name        = "overview"
        displayName = "Sales Overview"
        datasets    = [
          {
            name  = "orders"
            query = "SELECT * FROM sales.gold.orders"
          }
        ]
        widgets = []
      }
    ]
  })

  # Option 2: External file (mutually exclusive with serialized_dashboard)
  # file_path = "${path.module}/dashboard.lvdash.json"

  # Optional: Set default catalog/schema for datasets
  dataset_catalog = "sales"
  dataset_schema  = "gold"
}

# Control dashboard embedding
resource "databricks_aibi_dashboard_embedding_access_policy_setting" "this" {
  aibi_dashboard_embedding_access_policy {
    access_policy_type = "ALLOW_APPROVED_DOMAINS"
  }
}

resource "databricks_aibi_dashboard_embedding_approved_domains_setting" "this" {
  aibi_dashboard_embedding_approved_domains {
    approved_domains = ["*.company.com", "analytics.internal"]
  }
}
```

### Limitations

- Cannot create standalone Genie spaces (only companion spaces via dashboards)
- Cannot configure Genie-specific settings like sample questions, instructions
- The companion Genie space inherits configuration from the dashboard

---

## 4. Databricks Asset Bundles

### Key Findings

**There is NO dedicated `genie_space` resource type** in Databricks Asset Bundles. However, dashboards can be managed, which creates companion Genie spaces.

### Supported Resource Types (24 total)

The following AI/BI relevant resources are supported:
- `dashboard` - AI/BI dashboards (creates companion Genie space)
- `app` - Databricks Apps (can reference existing Genie spaces)

### Dashboard in databricks.yml

```yaml
bundle:
  name: sales-analytics-bundle

workspace:
  host: https://<workspace>.cloud.databricks.com

resources:
  dashboards:
    sales_dashboard:
      display_name: "Sales Analytics Dashboard"
      file_path: ./dashboards/sales_dashboard.lvdash.json
      warehouse_id: ${var.warehouse_id}
      parent_path: /Shared/analytics
      embed_credentials: false

      # Optional: Parameterize catalog/schema
      dataset_catalog: ${var.catalog}
      dataset_schema: ${var.schema}

      permissions:
        - level: CAN_VIEW
          group_name: analysts
        - level: CAN_EDIT
          user_name: admin@company.com

variables:
  warehouse_id:
    description: SQL Warehouse ID
    default: ""
  catalog:
    description: Default catalog for datasets
    default: "sales"
  schema:
    description: Default schema for datasets
    default: "gold"

targets:
  dev:
    workspace:
      host: https://dev-workspace.cloud.databricks.com
    variables:
      warehouse_id: "dev-warehouse-id"
      catalog: "dev_sales"

  prod:
    workspace:
      host: https://prod-workspace.cloud.databricks.com
    variables:
      warehouse_id: "prod-warehouse-id"
      catalog: "prod_sales"
```

### Referencing Genie Spaces in Apps

```yaml
resources:
  apps:
    genie_app:
      name: genie-query-app
      description: "App that queries Genie spaces"
      source_path: ./apps/genie_app

      resources:
        - name: my-genie-space
          genie_space:
            space_id: ${var.genie_space_id}
            permission: CAN_QUERY
```

---

## 5. Databricks CLI

### Key Findings

The Databricks CLI includes a `genie` command group. **Space management commands (create-space, update-space, list-spaces) are available** but may require the latest CLI version.

### Available Commands

```bash
# Get details of a Genie Space
databricks genie get-space <SPACE_ID>

# Start a conversation
databricks genie start-conversation <SPACE_ID> "What were total sales last month?"

# Create a message in existing conversation
databricks genie create-message <SPACE_ID> <CONVERSATION_ID> "Break down by region"

# Get a specific message
databricks genie get-message <SPACE_ID> <CONVERSATION_ID> <MESSAGE_ID>

# Execute attachment query
databricks genie execute-message-attachment-query <SPACE_ID> <CONVERSATION_ID> <MESSAGE_ID> <ATTACHMENT_ID>

# Get query results
databricks genie get-message-attachment-query-result <SPACE_ID> <CONVERSATION_ID> <MESSAGE_ID> <ATTACHMENT_ID>
```

### Space Management via CLI (using api command)

Since dedicated CLI commands for space creation may not be fully documented, use the generic API command:

```bash
# Create a Genie Space
databricks api post /api/2.0/genie/spaces --json '{
  "title": "Sales Analytics Space",
  "description": "Analyze sales data",
  "parent_path": "/Workspace/Users/analyst@company.com",
  "warehouse_id": "abc123",
  "serialized_space": "{\"version\":1,\"config\":{\"sample_questions\":[{\"id\":\"q1\",\"question\":[\"Total sales?\"]}]},\"data_sources\":{\"tables\":[{\"identifier\":\"sales.gold.orders\"}]}}"
}'

# List all spaces
databricks api get /api/2.0/genie/spaces

# Get a specific space
databricks api get /api/2.0/genie/spaces/<space_id>

# Update a space
databricks api put /api/2.0/genie/spaces/<space_id> --json '{
  "title": "Updated Sales Analytics",
  "serialized_space": "..."
}'

# Delete (trash) a space
databricks api delete /api/2.0/genie/spaces/<space_id>
```

---

## 6. Alternative Approaches

### Unity Catalog Integration

Genie spaces require Unity Catalog. While you cannot create a Genie space directly via SQL, you can prepare the underlying data infrastructure:

```sql
-- Create catalog and schema
CREATE CATALOG IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS sales.gold;

-- Create tables that will be used in Genie space
CREATE TABLE IF NOT EXISTS sales.gold.orders (
    order_id STRING,
    customer_id STRING,
    order_date DATE,
    amount DECIMAL(10,2),
    region STRING
) USING DELTA;

-- Grant access for Genie users
GRANT USE CATALOG ON CATALOG sales TO `analysts`;
GRANT USE SCHEMA ON SCHEMA sales.gold TO `analysts`;
GRANT SELECT ON TABLE sales.gold.orders TO `analysts`;
```

### Metric Views for Genie Enhancement

As of 2025, you can define semantic metadata using metric views:

```sql
CREATE METRIC VIEW IF NOT EXISTS sales.gold.sales_metrics
AS SELECT
  SUM(amount) AS total_revenue,
  COUNT(DISTINCT customer_id) AS unique_customers,
  AVG(amount) AS average_order_value
FROM sales.gold.orders;
```

---

## Recommendations

### For New Projects

1. **REST API (Primary)**: Use the Genie Management APIs for full control over space configuration
2. **Python SDK**: Combine with REST API for automation scripts and CI/CD pipelines
3. **Asset Bundles with Dashboards**: For projects where dashboards + companion Genie spaces are acceptable

### For Terraform Users

1. Use `databricks_dashboard` resource for dashboard-coupled Genie spaces
2. For standalone Genie spaces, consider using `terraform-provider-restapi` or `null_resource` with local-exec provisioners to call the REST API

### Example: Terraform with REST API

```hcl
resource "null_resource" "genie_space" {
  triggers = {
    title        = var.genie_space_title
    warehouse_id = var.warehouse_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      curl -X POST "${var.databricks_host}/api/2.0/genie/spaces" \
        -H "Authorization: Bearer ${var.databricks_token}" \
        -H "Content-Type: application/json" \
        -d '${jsonencode({
          title          = var.genie_space_title
          description    = var.genie_space_description
          parent_path    = var.parent_path
          warehouse_id   = var.warehouse_id
          serialized_space = var.serialized_space
        })}'
    EOT
  }
}
```

---

## Feature Status Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Create Space API | Beta | Full support |
| Update Space API | Beta | Full support |
| Get/List Space API | GA | Full support |
| Python SDK (conversations) | GA | Full support |
| Python SDK (create space) | Beta | Use api_client.do() |
| Terraform databricks_genie_space | Not Available | Use dashboard or REST API |
| Asset Bundles genie_space | Not Available | Use dashboard resource |
| CLI genie commands | GA/Beta | Conversation commands GA, space mgmt via API |

---

## Sources

- [Genie API Reference](https://docs.databricks.com/api/workspace/genie)
- [Genie Conversation API Documentation](https://docs.databricks.com/aws/en/genie/conversation-api)
- [Set up and manage Genie spaces](https://docs.databricks.com/aws/en/genie/set-up)
- [AI/BI Release Notes 2025](https://docs.databricks.com/aws/en/ai-bi/release-notes/2025)
- [Databricks Asset Bundles Resources](https://docs.databricks.com/aws/en/dev-tools/bundles/resources)
- [Terraform Provider databricks_dashboard](https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/dashboard)
- [Databricks CLI genie commands](https://docs.databricks.com/aws/en/dev-tools/cli/reference/genie-commands)
- [databricks/databricks-sdk-py GitHub](https://github.com/databricks/databricks-sdk-py)
- [databricks/terraform-provider-databricks GitHub](https://github.com/databricks/terraform-provider-databricks)
