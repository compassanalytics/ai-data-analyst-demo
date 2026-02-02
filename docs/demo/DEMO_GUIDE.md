# Demo Guide — Genie SDK Workshop

Follow along with **`notebooks/01_genie_sdk_demo.ipynb`**. This guide explains each section, provides the fill-in answers, and shows the architecture as it builds up.

---

## What We're Building

We start with a single SDK call and progressively add layers:

```
Step 1: Raw SDK            Step 2: + LLM Router         Step 3: Multi-Genie Synthesis

  Question                   Question                     Complex Question
     |                          |                              |
     v                          v                          Decomposer (LLM)
  Genie SDK               Router (LLM)                        |
     |                     |         |                +--------+--------+
     v                  rewrite   space_id            |        |        |
  SQL + Answer             |         |             Sales    CRM     Operations
                           v         v             Genie    Genie    Genie
                        Genie SDK (better query)      |        |        |
                           |                          +--------+--------+
                           v                              |
                     Formatted Output                Synthesizer (LLM)
                                                          |
                                                     Unified Answer
```

| Step | Concept | Key Pattern |
|---|---|---|
| **Step 1** | Connect to Genie, parse responses | SDK calls + attachment iteration |
| **Step 2** | LLM rewrites questions + routes | Metadata-aware prompt engineering |
| **Step 3** | Query multiple Genie Spaces at once | Decompose-fan out-synthesize |

---

## Before You Start

1. Run cells **2** (pip install) and **4** (imports) — these are pre-filled
2. Set the `genie_space_id` widget in cell **6** to your Unified Analytics space ID
3. Run cell **8** to save the widget value

---

## Step 1: Connect to Genie (Cells 13–25)

### Cell 13 — Create a WorkspaceClient

```python
w = WorkspaceClient()
```

No arguments needed inside Databricks — the SDK auto-detects your credentials.

---

### Cell 14 — First Genie query

```python
msg = w.genie.start_conversation_and_wait(
    space_id=GENIE_SPACE_ID,
    content="What are the top 10 vehicles by total order value?",
    timeout=timedelta(seconds=120),
)
print(msg)
```

`start_conversation_and_wait` is the core SDK call — send a natural language question, block until Genie generates SQL, executes it, and returns an answer.

> **Note:** You'll need to add `from datetime import timedelta` or use `timedelta` from the existing imports.

---

### Cell 16 — Extract the text answer

```python
answer = next(
    (att.text.content for att in msg.attachments if att.text and att.text.content),
    None,
)
print(answer)
```

Genie returns a `GenieMessage` with a list of `attachments`. Each attachment can have:
- `.query` — the generated SQL (`.query.query`) and its description (`.query.description`)
- `.text` — the natural language answer (`.text.content`)
- `.suggested_questions` — follow-up suggestions

Not every attachment has all three — always check for `None`.

---

### Cell 11 — GenieUtils fill-ins

The `GenieUtils` class wraps the SDK calls into reusable methods. Here are the fill-ins:

#### `print_output` — Loop body

```python
for att in message.attachments or []:
    if att.query and att.query.query and sql is None:
        sql = att.query.query
    if att.text and att.text.content and answer is None:
        answer = att.text.content
```

#### `ask_genie` — SDK call

```python
msg = client.genie.start_conversation_and_wait(
    space_id=space_id,
    content=query,
    timeout=timedelta(seconds=120),
)
```

#### `ask_genie` — Attachment parsing

```python
for att in msg_dict.get("attachments") or []:
    if att.get("query"):
        sql = sql or att["query"].get("query")
        description = description or att["query"].get("description")
    if att.get("text"):
        content = att["text"].get("content")
        if content:
            text_contents.append(content)
```

Here we use the dict form (`msg.as_dict()`) instead of attribute access — same data, different access pattern. `sql = sql or ...` means "keep the first one found."

#### `to_dataframe` — Fetch query result

```python
qr = client.genie.get_message_attachment_query_result(
    space_id=msg.space_id,
    conversation_id=msg.conversation_id,
    message_id=msg.id,
    attachment_id=att["attachment_id"],
)
```

This is a **separate API call** because result data can be large. Four IDs pinpoint which result to fetch.

#### `to_dataframe` — Build DataFrame

```python
columns = [c.name for c in (stmt.manifest.schema.columns or [])]
rows = stmt.result.data_array or []
```

Column names come from the SQL statement manifest; rows come as a list of lists (all values are strings).

#### `ask_genie_verbose` — Start conversation (non-blocking)

```python
conv = client.genie.start_conversation(
    space_id=space_id,
    content=query,
)
```

Unlike `start_conversation_and_wait`, this returns immediately so we can poll and watch status transitions.

#### `ask_genie_verbose` — Poll for status

```python
msg = client.genie.get_message(
    space_id=space_id,
    conversation_id=conversation_id,
    message_id=message_id,
)
```

---

### Cell 18 — Parse with utility

```python
GenieUtils.print_output(msg)
```

No fill-in needed — just run it to see the formatted output.

---

### Cells 20–21 — Multi-turn conversations

Every Genie response includes a `conversation_id`. Pass it back with `create_message_and_wait` to ask follow-ups — Genie remembers the SQL context.

**Cell 21:**

```python
followup = w.genie.create_message_and_wait(
    space_id=GENIE_SPACE_ID,
    conversation_id=conversation_id,
    content="Break that down by customer segment",
    timeout=timedelta(seconds=120),
)
GenieUtils.print_output(followup)
```

---

### Cell 23 — Verbose mode

No fill-in — just run it. Watch the status transitions print in real time:

```
[verbose] Status: ASKING_AI
[verbose] Status: EXECUTING_QUERY
[verbose] Status: COMPLETED
```

This is what `start_conversation_and_wait` does under the hood — a polling loop checking `get_message()` until the status reaches `COMPLETED`.

---

### Cell 25 — Get results as a DataFrame

```python
result = GenieUtils.ask_genie("What are the total orders by region?", GENIE_SPACE_ID, client=w)
df = GenieUtils.to_dataframe(result, client=w)
df
```

Chains two utilities: `ask_genie` sends the question, `to_dataframe` fetches the raw data rows via `get_message_attachment_query_result` and wraps them in a pandas DataFrame.

---

### Step 1 Recap

| What you did | Code |
|---|---|
| Connect to Databricks | `WorkspaceClient()` |
| Ask Genie a question | `genie.start_conversation_and_wait()` |
| Parse the response | Loop over `message.attachments` |
| Follow up in context | `genie.create_message_and_wait()` with `conversation_id` |
| Get data as DataFrame | `genie.get_message_attachment_query_result()` |
| Watch status transitions | `genie.start_conversation()` + `genie.get_message()` polling |

---

## Step 2: Single Genie Orchestrator (Cells 26–40)

The problem: users ask "what's the revenue by region?" but the column is called `total_order_value`. Genie might figure it out, or it might not. We add an LLM layer that reads the table schemas and **rewrites** the question to match the column names.

### Cell 28 — Create LLM

```python
llm = ChatDatabricks(
    endpoint="databricks-gpt-5-nano",
    temperature=1,
)
```

`ChatDatabricks` connects to a Databricks Model Serving endpoint. Check **AI/ML > Serving** in the sidebar for available endpoints.

---

### Cell 29 — Test the LLM

```python
llm.invoke("How is the weather today?")
```

Sanity check that the endpoint is reachable.

---

### Cell 31 — Practice with ask_genie

```python
GenieUtils.ask_genie("How many orders were placed last month by payment method?", GENIE_SPACE_ID, client=w)
```

---

### Cell 33 — Fetch space metadata

```python
GenieUtils.get_space_metadata(GENIE_SPACE_ID, client=w, enrich_columns=True)
```

This shows what the LLM router will receive: table names, column names with types and descriptions, and sample questions. The router uses this context to rewrite queries accurately.

---

### Cell 35 — `ask_router` fill-ins

#### Build the metadata prompt

```python
for space_id in genie_spaces:
    space_metadata = GenieUtils.get_space_metadata(space_id, client=client, enrich_columns=True)
    prompt += f"Space ID: {space_id}\nMetadata: {space_metadata}\n"
```

#### Call the LLM and parse

```python
response = llm.invoke(prompt)
obj = json.loads(response.content)
```

The LLM returns `{"query": "improved question", "space_id": "target space"}`.

---

### Cell 36 — Test the router

```python
router_response = ask_router(
    llm, "Which vehicle models have the most service orders?", [GENIE_SPACE_ID], client=w,
)
print(router_response)
```

Inspect the output — see how the LLM rewrote the query.

---

### Cell 38 — `GenieOrchestrator.execute()` fill-ins

#### Call the router

```python
router_response = ask_router(
    llm=self.llm,
    question=user_question,
    genie_spaces=self.space_ids,
    client=self.client,
)
```

#### Call Genie with the rewritten query

```python
genie_response = GenieUtils.ask_genie(
    query=router_response["query"],
    space_id=routed_id,
    client=self.client,
)
```

We use `router_response["query"]` (the rewritten version), not the original user question.

---

### Cell 39 — Create orchestrator

```python
orch = GenieOrchestrator(
    llm=llm,
    client=w,
)
```

No `space_ids` — defaults to `[GENIE_SPACE_ID]`.

---

### Cell 40 — Run it

```python
orch.execute("What are the top 5 selling vehicle models by total revenue?", output_format="llm")
```

Full pipeline: router rewrites + routes, Genie generates SQL + executes, LLM formats a polished summary.

Output formats:
- `"full"` — question + SQL + answer (no LLM cost)
- `"text"` — answer only
- `"llm"` — LLM-formatted Markdown summary
- `"raw"` — return dict, no printing

---

### Step 2 Recap

| What you did | Code |
|---|---|
| Connect to an LLM | `ChatDatabricks(endpoint=..., temperature=...)` |
| Fetch space metadata | `GenieUtils.get_space_metadata()` |
| LLM rewrites + routes | `ask_router()` |
| Full pipeline | `GenieOrchestrator.execute()` |

---

## Step 3: Multi-Genie Orchestration (Cells 41–55)

Same orchestrator, but now initialized with **3 domain-specific spaces** instead of 1. The router reads metadata from all spaces and picks the best match per question.

### Cell 42 — List available spaces

No fill-in — run it to see all Velocity Motors spaces in the workspace.

---

### Cell 43 — Configure multi-space orchestrator

Replace the space IDs with your actual IDs from `00c_setup_genie`:

```python
DOMAIN_SPACES = [
    "your-sales-space-id",
    "your-crm-space-id",
    "your-operations-space-id",
]

multi_orch = GenieOrchestrator(
    llm=llm,
    space_ids=DOMAIN_SPACES,
    client=w,
)
```

---

### Cells 45–49 — Watch routing in action

Run each cell and watch the `Routed to space:` output:

| Cell | Question | Expected target |
|---|---|---|
| 45 | "Top 5 selling vehicle models by revenue" | Sales Analytics |
| 46 | "Which customer segments generate the most service revenue?" | Customer Intelligence |
| 47 | "Which parts are below their reorder point?" | Operations & Inventory |
| 49 | "Customer lifetime value including service history?" | Router decides |

---

### Cell 51 — `ask_decomposer` fill-ins

Same pattern as the router, but returns a **list** of sub-queries instead of one:

#### Build metadata prompt

```python
for space_id in genie_spaces:
    space_metadata = GenieUtils.get_space_metadata(space_id, client=client, enrich_columns=True)
    prompt += f"Space ID: {space_id}\nMetadata: {space_metadata}\n\n"
```

#### Call LLM and parse

```python
response = llm.invoke(prompt)
sub_queries = json.loads(response.content)
```

Returns a list like `[{"query": "...", "space_id": "..."}, ...]`.

---

### Cell 52 — `execute_multi` fill-ins

Three fill-ins covering decompose, fan-out, and synthesize:

#### Decompose

```python
sub_queries = ask_decomposer(
    llm=self.llm,
    question=user_question,
    genie_spaces=self.space_ids,
    client=self.client,
)
```

#### Fan-out (inside the loop)

```python
response = GenieUtils.ask_genie(
    query=sq["query"],
    space_id=sq["space_id"],
    client=self.client,
)
```

#### Synthesize

```python
synthesis = self.llm.invoke(synthesis_prompt)
```

The synthesis prompt includes the original question plus all sub-query results, and the LLM combines them into a unified answer.

---

### Cells 54–55 — Cross-domain queries

Run these to see decomposition in action:

- **Cell 54**: "Compare revenue by region with customer satisfaction ratings and parts inventory levels" — decomposes into 3 sub-queries across all spaces
- **Cell 55**: "Which vehicle models have the highest service costs relative to their sale price?" — decomposes into 2 sub-queries (Sales + Operations)

---

### Step 3 Recap

| What you did | Code |
|---|---|
| Multi-space routing | `GenieOrchestrator(space_ids=[...])` — same class, more spaces |
| Decompose complex questions | `ask_decomposer()` — breaks into sub-queries |
| Fan-out execution | `GenieUtils.ask_genie()` per sub-query |
| Synthesize results | LLM combines all results into one answer |
| Full pipeline | `multi_orch.execute_multi()` |

---

## Bonus: Notebook 02 — Multi-Genie Report Generation

`02_multi_genie_orchestration.ipynb` builds on what you learned here to create a **report generation** pipeline. If you want to explore further:

- It adds a **Planner** agent that breaks business questions into an analytical plan
- A **Synthesizer** produces structured reports from multiple Genie queries
- The **ReportWriter** formats output as Markdown with charts and tables

This notebook is self-contained — open it and follow the instructions.

---

## Complete SDK Reference

| SDK Method | Blocks? | Returns | Use when |
|---|---|---|---|
| `genie.start_conversation_and_wait()` | Yes | `GenieMessage` | New question (simple path) |
| `genie.start_conversation()` | No | `Wait[GenieMessage]` | Need status polling |
| `genie.get_message()` | No | `GenieMessage` | Polling in a loop |
| `genie.create_message_and_wait()` | Yes | `GenieMessage` | Follow-up in same conversation |
| `genie.get_message_attachment_query_result()` | Yes | Query result | Need raw data rows |
| `genie.get_space()` | Yes | `GenieSpace` | Space title or config |
| `genie.list_spaces()` | Yes | List of spaces | Discovery |

For full method signatures, parameter types, and response structures, see the [Appendix](APPENDIX.md).

---

## Summary

```
3 SDK calls power the entire demo:

1. start_conversation_and_wait  -->  new question
2. create_message_and_wait      -->  follow-up
3. get_message_attachment_query_result  -->  get the data

Everything else is orchestration: LLMs rewriting questions,
routing to the right space, decomposing complex queries,
and synthesizing results.
```
