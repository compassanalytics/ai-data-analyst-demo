# Appendix — SDK & Library Reference

Complete reference for every method, class, and type used in the workshop notebooks. Pulled from the official Databricks SDK and databricks-langchain documentation.

---

## Table of Contents

1. [WorkspaceClient (Authentication)](#1-workspaceclient)
2. [Genie API Methods](#2-genie-api-methods)
3. [Response Types](#3-response-types)
4. [ChatDatabricks](#4-chatdatabricks)
5. [MLflow Autologging](#5-mlflow-autologging)
6. [Official Documentation Links](#6-official-documentation-links)

---

## 1. WorkspaceClient

```python
from databricks.sdk import WorkspaceClient
```

### Constructor

```python
w = WorkspaceClient(
    host: str = None,      # e.g. "https://your-workspace.cloud.databricks.com"
    token: str = None,     # Personal Access Token (dapi...)
)
```

Inside a Databricks notebook, call `WorkspaceClient()` with no arguments — it auto-detects the notebook's authentication context.

### Authentication Resolution Order

When no explicit credentials are provided, the SDK tries these methods in order:

| Priority | Method | Config Required |
|---|---|---|
| 1 | Personal Access Token | `DATABRICKS_HOST` + `DATABRICKS_TOKEN` env vars |
| 2 | OAuth U2M | `host` + cached OAuth from `databricks auth login` |
| 3 | OAuth M2M (Service Principal) | `host` + `client_id` + `client_secret` |
| 4 | Azure CLI | Azure CLI logged in |
| 5 | Notebook context | Running inside Databricks Runtime (automatic) |

### Usage

```python
# Inside Databricks notebook (automatic auth)
w = WorkspaceClient()

# Outside Databricks (explicit PAT)
w = WorkspaceClient(
    host="https://your-workspace.cloud.databricks.com",
    token="dapi..."
)

# Outside Databricks (env vars)
# Set DATABRICKS_HOST and DATABRICKS_TOKEN, then:
w = WorkspaceClient()
```

---

## 2. Genie API Methods

All methods are on `WorkspaceClient().genie`.

### `start_conversation_and_wait`

Start a new conversation with a question and block until Genie returns a result.

```python
w.genie.start_conversation_and_wait(
    space_id: str,                                     # Genie Space ID (32-char hex)
    content: str,                                      # Natural language question
    timeout: datetime.timedelta = timedelta(minutes=20) # Max wait time
) -> GenieMessage
```

**Example:**
```python
from datetime import timedelta

msg = w.genie.start_conversation_and_wait(
    space_id="3c409c00b54a44c79f79da06b82460e2",
    content="What are the top 10 vehicles by total order value?",
    timeout=timedelta(seconds=120),
)
```

---

### `create_message_and_wait`

Send a follow-up question in an existing conversation. Genie uses the full conversation history for context.

```python
w.genie.create_message_and_wait(
    space_id: str,                                     # Genie Space ID
    conversation_id: str,                              # From previous message
    content: str,                                      # Follow-up question
    timeout: datetime.timedelta = timedelta(minutes=20)
) -> GenieMessage
```

**Example:**
```python
followup = w.genie.create_message_and_wait(
    space_id=GENIE_SPACE_ID,
    conversation_id=msg.conversation_id,
    content="Break that down by customer segment",
    timeout=timedelta(seconds=120),
)
```

---

### `start_conversation`

Start a new conversation without blocking. Use this when you want to poll for status manually.

```python
w.genie.start_conversation(
    space_id: str,                                     # Genie Space ID
    content: str,                                      # Natural language question
) -> Wait[GenieMessage]
```

Returns a `Wait` object. The `conversation_id` and `message_id` are available immediately for polling.

**Example:**
```python
conv = w.genie.start_conversation(
    space_id=GENIE_SPACE_ID,
    content="Show monthly revenue trend",
)
conversation_id = conv.conversation_id
message_id = conv.message_id
```

---

### `get_message`

Retrieve the current state of a message. Used in polling loops to check status.

```python
w.genie.get_message(
    space_id: str,                                     # Genie Space ID
    conversation_id: str,                              # Conversation ID
    message_id: str,                                   # Message ID
) -> GenieMessage
```

**Example (polling loop):**
```python
import time

while True:
    msg = w.genie.get_message(
        space_id=GENIE_SPACE_ID,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    if msg.status.value in ("COMPLETED", "FAILED"):
        break
    time.sleep(2)
```

---

### `get_message_attachment_query_result`

Fetch the raw data rows from a query attachment. This is a separate API call because result data can be large.

```python
w.genie.get_message_attachment_query_result(
    space_id: str,                                     # Genie Space ID
    conversation_id: str,                              # Conversation ID
    message_id: str,                                   # Message ID
    attachment_id: str,                                # From GenieAttachment.attachment_id
) -> GenieGetMessageQueryResultResponse
```

**Returns** a response containing `statement_response` (from the SQL Statement Execution API).

**Example:**
```python
for att in msg.attachments or []:
    if att.attachment_id and att.query:
        qr = w.genie.get_message_attachment_query_result(
            space_id=GENIE_SPACE_ID,
            conversation_id=msg.conversation_id,
            message_id=msg.message_id,
            attachment_id=att.attachment_id,
        )
        stmt = qr.statement_response
        columns = [c.name for c in stmt.manifest.schema.columns]
        rows = stmt.result.data_array  # List[List[str]]
        df = pd.DataFrame(rows, columns=columns)
```

> **Limit:** Maximum 5,000 rows returned per query result.

---

### `get_space`

Fetch metadata for a Genie Space. With `include_serialized_space=True`, returns the full configuration JSON (requires **CAN EDIT** permission).

```python
w.genie.get_space(
    space_id: str,                                     # Genie Space ID
    include_serialized_space: bool = None,             # Include full config JSON
) -> GenieSpace
```

**Example:**
```python
space = w.genie.get_space(
    space_id=GENIE_SPACE_ID,
    include_serialized_space=True,
)
print(space.title)
print(space.description)

# Parse full config
import json
config = json.loads(space.serialized_space)
tables = config["data_sources"]["tables"]
```

---

### `list_spaces`

List all Genie Spaces you have access to.

```python
w.genie.list_spaces(
    page_size: int = None,                             # Max spaces per page
    page_token: str = None,                            # Pagination token
) -> GenieListSpacesResponse
```

**Example:**
```python
resp = w.genie.list_spaces()
for space in resp.spaces:
    print(f"{space.title}: {space.space_id}")
```

---

## 3. Response Types

All types are imported from `databricks.sdk.service.dashboards`.

### `GenieMessage`

The primary response from Genie API calls.

```python
from databricks.sdk.service.dashboards import GenieMessage
```

| Field | Type | Description |
|---|---|---|
| `content` | `str` | The original question you sent |
| `conversation_id` | `str` | Reuse for follow-up messages |
| `message_id` | `str` | Unique message identifier |
| `space_id` | `str` | The Genie Space that handled this |
| `attachments` | `List[GenieAttachment]` or `None` | AI-generated response(s) |
| `status` | `MessageStatus` or `None` | Processing status |
| `error` | `MessageError` or `None` | Error details if `status == FAILED` |
| `id` | `str` | Legacy message ID (prefer `message_id`) |

---

### `GenieAttachment`

Each attachment contains one type of response content.

| Field | Type | Description |
|---|---|---|
| `attachment_id` | `str` or `None` | Used to fetch query results |
| `query` | `GenieQueryAttachment` or `None` | Generated SQL |
| `text` | `TextAttachment` or `None` | Natural language answer |
| `suggested_questions` | `GenieSuggestedQuestionsAttachment` or `None` | Follow-up suggestions |

---

### `GenieQueryAttachment`

The SQL query generated by Genie.

| Field | Type | Description |
|---|---|---|
| `query` | `str` or `None` | The generated SQL string |
| `description` | `str` or `None` | Explanation of what the query does |
| `statement_id` | `str` or `None` | Statement Execution API ID |
| `title` | `str` or `None` | Query title |

---

### `TextAttachment`

The natural language response.

| Field | Type | Description |
|---|---|---|
| `content` | `str` or `None` | AI-generated text answer |

---

### `MessageStatus` (Enum)

```python
from databricks.sdk.service.dashboards import MessageStatus
```

| Value | Description |
|---|---|
| `SUBMITTED` | Request received |
| `FETCHING_METADATA` | Loading table schemas |
| `FILTERING_CONTEXT` | Selecting relevant context |
| `ASKING_AI` | LLM generating SQL |
| `PENDING_WAREHOUSE` | Waiting for warehouse allocation |
| `EXECUTING_QUERY` | Running the generated SQL |
| `COMPLETED` | Done — results are in `attachments` |
| `FAILED` | Generation or execution failed |
| `CANCELLED` | User cancelled |
| `QUERY_RESULT_EXPIRED` | Results expired — re-run with `execute_message_attachment_query()` |

**Typical lifecycle:**
```
SUBMITTED -> FETCHING_METADATA -> ASKING_AI -> EXECUTING_QUERY -> COMPLETED
```

---

### `GenieSpace`

```python
from databricks.sdk.service.dashboards import GenieSpace
```

| Field | Type | Description |
|---|---|---|
| `space_id` | `str` | Unique identifier (32-char hex) |
| `title` | `str` | Display name |
| `description` | `str` or `None` | Space description |
| `serialized_space` | `str` or `None` | Full config JSON (when requested) |
| `warehouse_id` | `str` or `None` | Attached SQL warehouse |

---

### `GenieGetMessageQueryResultResponse`

Returned by `get_message_attachment_query_result`.

| Field | Type | Description |
|---|---|---|
| `statement_response` | `sql.StatementResponse` | SQL execution result |

Access pattern:
```python
stmt = qr.statement_response
columns = [c.name for c in stmt.manifest.schema.columns]  # Column names
rows = stmt.result.data_array                               # List[List[str]]
```

---

### `MessageError`

| Field | Type | Description |
|---|---|---|
| `error` | `str` or `None` | Error message |
| `type` | `MessageErrorType` or `None` | Error category |

---

## 4. ChatDatabricks

```python
from databricks_langchain import ChatDatabricks
```

Wrapper around a Databricks Model Serving endpoint, compatible with the LangChain ecosystem.

### Constructor

```python
llm = ChatDatabricks(
    endpoint: str,                    # Model Serving endpoint name (required)
    temperature: float = None,        # Sampling temperature (0 = deterministic, 1 = creative)
    max_tokens: int = None,           # Max tokens to generate
    stop: List[str] = None,           # Stop sequences
    extra_params: dict = None,        # Additional params forwarded to endpoint
    workspace_client: WorkspaceClient = None,  # Custom auth (auto-created if omitted)
)
```

> **Note:** The parameter is named `endpoint` (alias for `model` internally). Both `endpoint=` and `model=` work.

**Example:**
```python
llm = ChatDatabricks(
    endpoint="databricks-gpt-5-nano",
    temperature=1,
)
```

### Authentication

Inside Databricks: automatic — `ChatDatabricks` creates a `WorkspaceClient()` internally.

Outside Databricks: set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` environment variables, or pass a `workspace_client`.

### `.invoke()`

Send a prompt and get a response.

```python
llm.invoke(
    input: str | List[tuple] | List[BaseMessage],  # The prompt
    config: RunnableConfig = None,                   # Optional LangChain config
    **kwargs,
) -> AIMessage
```

**Input formats:**

| Format | Example |
|---|---|
| Plain string | `llm.invoke("What is MLflow?")` |
| Tuple messages | `llm.invoke([("system", "You are helpful"), ("human", "Hi")])` |
| Message objects | `llm.invoke([HumanMessage(content="Hi")])` |

**Return type:** `AIMessage`

```python
response = llm.invoke("Explain Genie Spaces in one sentence.")
print(response.content)  # "Genie Spaces are..."
print(response.response_metadata)  # {"prompt_tokens": 15, "completion_tokens": 22, ...}
```

### `.stream()`

Stream the response token by token.

```python
for chunk in llm.stream("Explain Genie Spaces"):
    print(chunk.content, end="")
```

### `.bind_tools()`

Attach tool schemas for function calling (requires a compatible endpoint).

```python
from pydantic import BaseModel

class GetWeather(BaseModel):
    """Get weather for a location"""
    location: str

llm_with_tools = llm.bind_tools([GetWeather])
response = llm_with_tools.invoke("What's the weather in Paris?")
print(response.tool_calls)
```

### `.with_structured_output()`

Force the LLM to return a Pydantic model.

```python
class Answer(BaseModel):
    answer: str
    confidence: float

structured = llm.with_structured_output(Answer)
result = structured.invoke("What is 2+2?")
# result.answer == "4", result.confidence == 1.0
```

---

## 5. MLflow Autologging

### Setup

```python
import mlflow

mlflow.set_tracking_uri("databricks")       # Log to Databricks workspace
mlflow.set_registry_uri("databricks-uc")    # Model registry -> Unity Catalog
mlflow.langchain.autolog()                   # Enable LangChain tracing
```

Inside Databricks notebooks, the tracking and registry URIs are typically pre-configured.

### `mlflow.langchain.autolog()`

```python
mlflow.langchain.autolog(
    disable: bool = False,                # Turn off autologging
    log_traces: bool = True,              # Log traces for each LLM call
    silent: bool = False,                 # Suppress MLflow warnings
)
```

### What gets captured

When `log_traces=True` (default), every `llm.invoke()` or chain execution creates a **trace** with spans:

| Span Type | Captured For | Data Recorded |
|---|---|---|
| `CHAT_MODEL` | `ChatDatabricks.invoke()` | Input messages, output, token usage, latency |
| `CHAIN` | LangChain chain execution | Input, output, sub-spans |
| `RETRIEVER` | RAG retrievers | Query, retrieved documents |
| `TOOL` | Tool/function calls | Tool name, input, output |

**Token usage** is recorded per-span and aggregated per-trace:
```python
trace = mlflow.get_trace(trace_id=mlflow.get_last_active_trace_id())
print(trace.info.token_usage)
# {"input_tokens": 150, "output_tokens": 42, "total_tokens": 192}
```

### Viewing traces

In Databricks, traces appear in the **MLflow Experiments** UI:
1. Click **Experiments** in the sidebar
2. Select your notebook's experiment
3. Click the **Traces** tab

---

## 6. Official Documentation Links

### Databricks SDK

| Resource | URL |
|---|---|
| Genie API methods | [databricks-sdk-py.readthedocs.io/en/latest/workspace/dashboards/genie.html](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dashboards/genie.html) |
| Dashboard dataclasses | [databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dashboards.html](https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dashboards.html) |
| SDK authentication | [databricks-sdk-py.readthedocs.io/en/latest/authentication.html](https://databricks-sdk-py.readthedocs.io/en/latest/authentication.html) |
| Genie Conversation API guide | [docs.databricks.com/aws/en/genie/conversation-api](https://docs.databricks.com/aws/en/genie/conversation-api) |
| REST API reference | [docs.databricks.com/api/workspace/genie](https://docs.databricks.com/api/workspace/genie) |
| SDK GitHub repo | [github.com/databricks/databricks-sdk-py](https://github.com/databricks/databricks-sdk-py) |

### databricks-langchain

| Resource | URL |
|---|---|
| PyPI package | [pypi.org/project/databricks-langchain](https://pypi.org/project/databricks-langchain/) |
| ChatDatabricks integration docs | [docs.langchain.com/oss/python/integrations/chat/databricks](https://docs.langchain.com/oss/python/integrations/chat/databricks) |
| Source repo | [github.com/databricks/databricks-ai-bridge](https://github.com/databricks/databricks-ai-bridge) |

### MLflow

| Resource | URL |
|---|---|
| LangChain autologging | [mlflow.org/docs/latest/genai/flavors/langchain/autologging](https://mlflow.org/docs/latest/genai/flavors/langchain/autologging/) |
| Tracing for LangChain | [mlflow.org/docs/latest/genai/tracing/integrations/listing/langchain](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/langchain) |
| Python API reference | [mlflow.org/docs/latest/python_api/mlflow.langchain.html](https://mlflow.org/docs/latest/python_api/mlflow.langchain.html) |

---

## REST API Endpoints (Reference)

For debugging or direct API calls without the SDK:

| Operation | Method | Endpoint |
|---|---|---|
| Start conversation | POST | `/api/2.0/genie/spaces/{space_id}/start-conversation` |
| Create message | POST | `/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages` |
| Get message | GET | `/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}` |
| Get query result | GET | `...messages/{message_id}/query-result/{attachment_id}` |
| List spaces | GET | `/api/2.0/genie/spaces` |
| Get space | GET | `/api/2.0/genie/spaces/{space_id}` |

---

## Known Limits & Gotchas

| Constraint | Detail |
|---|---|
| Query result rows | 5,000 max per `get_message_attachment_query_result` call |
| API throughput | ~5 queries/minute per workspace (Public Preview) |
| GET polling | Does **not** count toward rate limits — only POST requests do |
| Space ID format | 32-character lowercase hex (UUID without hyphens) |
| Default timeout | 20 minutes for `_and_wait` methods |
| `query_result` field | **Deprecated** on `GenieMessage` — use `attachments` instead |
| Expired results | Call `execute_message_attachment_query()` to re-run expired queries |
| Conversation state | AI uses all prior messages in a conversation for context — create a new conversation to start fresh |
