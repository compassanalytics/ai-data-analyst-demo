# Genie SDK Demo — Workshop Reference Guide

**Notebooks:**
- Workshop (fill-in): `01_genie_sdk_demo.ipynb`
- Answer key: `Genie SDK Demo_v1.ipynb`

**Roles:**
- **Presenter** — Introduces concepts, draws architecture diagrams, poses questions to the audience, frames the "why"
- **Code Lead** — Walks through the notebook cells, explains the code, gives fill-in time, runs demos

---

## Pre-Workshop Setup

Ensure all attendees have:
- Access to the Databricks workspace
- The workshop notebook cloned to their user folder
- Genie Space IDs from `00c_setup_genie` (3 domain spaces + 1 unified)
- A running cluster with `databricks-langchain` installed

Cells 2 (pip install), 4 (imports), 6–8 (widget config) are run-once setup — no fill-ins. Code Lead can run these while Presenter does introductions.

---

## Step 1: Connect to Genie (Cells 0–25)

### 1A. Opening — What is Genie?

**Presenter:**
> "You have structured data in Unity Catalog — sales transactions, customer records, inventory. Your business analysts want to ask questions in plain English without writing SQL. That's what Genie does."

Draw on the board:

```
  "What are the top vehicles by revenue?"
                  |
                  v
          [ Genie Space ]
           (table schemas,
            column descriptions,
            sample questions)
                  |
                  v
         Generated SQL + Answer
```

> "A Genie Space is a curated view over your tables — you tell it which tables to use, describe the columns, and give it sample questions. Genie uses that context to generate SQL from natural language."

> "Let's connect to it programmatically."

---

### 1B. Connect + First Query (Cells 13–14)

**Code Lead:**

> "First we need a `WorkspaceClient` — this handles authentication. On Databricks, it auto-detects your credentials."

**Cell 13** — Create WorkspaceClient:
```python
w = WorkspaceClient()
```
> No arguments needed inside Databricks. The SDK picks up the current user's U2M auth.

**Cell 14** — First Genie query:
```python
msg = w.genie.start_conversation_and_wait(
    space_id=GENIE_SPACE_ID,
    content="What are the top 10 vehicles by total order value?",
    timeout=timedelta(seconds=120),
)
```
> `start_conversation_and_wait` is the core SDK call — send a natural language question, block until Genie generates SQL, executes it, and composes an answer. The `timeout` prevents hanging.

Run the cell. Show the raw `GenieMessage` output — point out it's an object with `attachments`, `conversation_id`, `status`.

---

### 1C. Parse the Response (Cells 16–18)

**Presenter:**

> "Genie gave us back a `GenieMessage`. But the answer is buried inside `attachments` — not every attachment has both SQL and text. How would you safely extract the text answer?"

*(Take a response from the audience)*

**Code Lead:**

**Cell 16** — Extract text from attachments:
```python
answer = next((att.text.content for att in msg.attachments if att.text and att.text.content), None)
```
> Python pattern: "find first matching element or return None." The double check (`att.text and att.text.content`) avoids `AttributeError` if an attachment has no text.

**Cell 18** — Run `GenieUtils.print_output(msg)` to show the formatted version (question, SQL, answer).

---

### 1D. Multi-Turn Conversations (Cells 20–21)

**Presenter:**

> "What if your analyst says 'now break that down by customer segment'? Do they start over?"

*(Brief audience response)*

> "No — Genie supports multi-turn. You pass the `conversation_id` back and it remembers the SQL context."

**Code Lead:**

**Cell 20** — already provided: extracts `conversation_id` from the first message.

**Cell 21** — Follow-up conversation:
```python
followup = w.genie.create_message_and_wait(
    space_id=GENIE_SPACE_ID,
    conversation_id=conversation_id,
    content="Break that down by customer segment",
    timeout=timedelta(seconds=120),
)
```
> `create_message_and_wait` (not `start_conversation`) is for follow-ups. The `conversation_id` came from the previous `msg.conversation_id`. Genie remembers the prior query context.

---

### 1E. GenieUtils — Wrapping the SDK (Cell 11)

**Presenter:**

> "We've been writing raw SDK calls, extracting attachments manually every time. What happens when you need to do this 50 times across a codebase? You wrap it in a utility class."

> "The `GenieUtils` class is provided for you — but some key lines inside the methods are missing. Let's walk through each method and fill in the SDK calls."

**Code Lead:**

Walk through cell 11 method by method. For each, explain what the method does, then have attendees fill in the TODO.

**`print_output`** — Attachment loop body:
```python
for att in message.attachments or []:
    if att.query and att.query.query and sql is None:
        sql = att.query.query
    if att.text and att.text.content and answer is None:
        answer = att.text.content
```
> Same pattern as cell 16 but structured — iterate all attachments, grab the first SQL and first text answer. `or []` guards against `None` attachments.

**`ask_genie`** — SDK call:
```python
msg = client.genie.start_conversation_and_wait(
    space_id=space_id,
    content=query,
    timeout=timedelta(seconds=120),
)
```
> Same SDK call as cell 14, now inside a reusable method.

**`ask_genie`** — Attachment parsing:
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
> We convert the message to a dict (`as_dict()`) for key-based access. `sql = sql or ...` means first query attachment wins. We collect all text fragments and later pick the longest with `max(text_contents, key=len)`.

---

**Now run cells 23 and 25 to show the utility in action.**

**Cell 23** — `ask_genie_verbose`: already provided, just run it. Watch status transitions print: `ASKING_AI -> EXECUTING_QUERY -> COMPLETED`.

> "This is what `start_conversation_and_wait` does under the hood — we've exposed the polling loop so you can see it."

**Cell 25** — Convert to DataFrame:
```python
result = GenieUtils.ask_genie("What are the total orders by region?", GENIE_SPACE_ID, client=w)
df = GenieUtils.to_dataframe(result, client=w)
```
> Chains two utilities: `ask_genie` sends the question and parses the response, `to_dataframe` makes a second API call (`get_message_attachment_query_result`) to get raw data rows and wraps them in a pandas DataFrame.

**Fill-ins inside `to_dataframe`** (if walking through cell 11 in detail):

Fetch query result:
```python
qr = client.genie.get_message_attachment_query_result(
    space_id=msg.space_id,
    conversation_id=msg.conversation_id,
    message_id=msg.id,
    attachment_id=att["attachment_id"],
)
```
> Separate API call because results can be large. Four IDs uniquely identify which result to fetch.

Build DataFrame:
```python
columns = [c.name for c in (stmt.manifest.schema.columns or [])]
rows = stmt.result.data_array or []
```
> Column names from `.manifest.schema.columns`, data rows from `.result.data_array`. Both are lists.

**Fill-ins inside `ask_genie_verbose`** (if walking through in detail):

Start conversation (non-blocking):
```python
conv = client.genie.start_conversation(
    space_id=space_id,
    content=query,
)
```
> `start_conversation` (no `_and_wait`) returns immediately. We get back `conversation_id` and `message_id` to poll with.

Poll for status:
```python
msg = client.genie.get_message(
    space_id=space_id,
    conversation_id=conversation_id,
    message_id=message_id,
)
```
> Called in a `while True` loop with `time.sleep(2)`. We check `msg.status.value` each iteration until `COMPLETED` or `FAILED`.

---

### Step 1 Checkpoint

**Presenter:**

> "We can now query Genie programmatically, parse responses, follow up in conversations, get DataFrames, and we have a utility class wrapping it all. But we're still hand-writing every question. What if the user's question doesn't match the column names?"

*(Transition to Step 2)*

---

## Step 2: Single Genie Orchestrator (Cells 26–40)

### 2A. Introduce the Problem

**Presenter:**

> "Your user asks 'what's the revenue by region?' but the column is called `total_order_value`, not `revenue`. Genie might figure it out, or it might not. How do we bridge that gap?"

*(Take audience response — someone will say "use an LLM")*

> "Exactly. We put an LLM in front of Genie as a router. It reads the table schemas, rewrites the question to match the column names, and picks which Genie Space to send it to."

Draw on the board:

```
  User Question
       |
       v
  ask_router (LLM)
    - reads space metadata (tables, columns)
    - rewrites question to match schema
    - picks target space_id
       |
       v
  ask_genie (SDK)
       |
       v
  Format + Display
```

---

### 2B. LLM Setup (Cells 27–29)

**Code Lead:**

Cell 27 is MLflow setup (provided, just run it).

**Cell 28** — Create LLM:
```python
llm = ChatDatabricks(
    endpoint="databricks-gpt-5-nano",
    temperature=1,
)
```
> `ChatDatabricks` connects to a Model Serving endpoint. `endpoint` is the serving endpoint name (check AI/ML > Serving in the sidebar).

**Cell 29** — Test LLM:
```python
llm.invoke("How is the weather today?")
```
> Sanity check that the endpoint is reachable.

---

### 2C. Space Metadata + Router (Cells 31–36)

**Code Lead:**

**Cell 31** — Practice calling ask_genie:
```python
GenieUtils.ask_genie("How many orders were placed last month by payment method?", GENIE_SPACE_ID, client=w)
```
> Quick practice using the utility we just built.

**Cell 33** — See what the router will receive:
```python
GenieUtils.get_space_metadata(GENIE_SPACE_ID, client=w, enrich_columns=True)
```
> Show the output — table names, column names + types + comments, sample questions. This is the context the LLM router gets. `enrich_columns=True` fetches full Unity Catalog schemas (richer but extra API calls).

**Presenter:**

> "Look at the metadata output — that's everything the LLM needs to understand the data. Column names, types, descriptions, sample questions. The router prompt feeds all of this in."

**Code Lead:**

Now walk through cell 35 — the `ask_router` function. Two fill-ins:

**Fill-in 1** — Build space metadata prompt:
```python
for space_id in genie_spaces:
    space_metadata = GenieUtils.get_space_metadata(space_id, client=client, enrich_columns=True)
    prompt += f"Space ID: {space_id}\nMetadata: {space_metadata}\n"
```
> Loop over all spaces, fetch metadata, append to the prompt. The LLM needs column-level detail to rewrite queries accurately.

**Fill-in 2** — LLM invoke + JSON parse:
```python
response = llm.invoke(prompt)
obj = json.loads(response.content)
```
> Send the full prompt to the LLM, parse the JSON response. The LLM was instructed to return `{"query": "...", "space_id": "..."}`. `response.content` is a string — `json.loads` converts it to a dict.

> Note for production: if the LLM returns markdown fences or extra text, `json.loads` crashes. Add retry logic (see `src/agents/supervisor.py` for an example).

**Cell 36** — Call the router:
```python
router_response = ask_router(llm, "Which vehicle models have the most service orders?", [GENIE_SPACE_ID], client=w)
```
> Test standalone. Inspect the output — see how the LLM rewrote the query and which space it chose.

---

### 2D. GenieOrchestrator — Wire It Together (Cells 38–40)

**Presenter:**

> "We have the router and Genie as separate pieces. The orchestrator wires them into a single `execute()` call."

**Code Lead:**

Walk through cell 38 — the `GenieOrchestrator` class. Two fill-ins inside `execute()`:

**Fill-in 1** — Call the router:
```python
router_response = ask_router(
    llm=self.llm,
    question=user_question,
    genie_spaces=self.space_ids,
    client=self.client,
)
```
> `self.space_ids` can be one space or many. With one, the router still rewrites the query. With multiple, it also picks the best space.

**Fill-in 2** — Call Genie with the rewritten query:
```python
genie_response = GenieUtils.ask_genie(
    query=router_response["query"],
    space_id=routed_id,
    client=self.client,
)
```
> We use `router_response["query"]` (the rewritten version), not the original `user_question`. `routed_id` comes from `router_response["space_id"]`.

**Cell 39** — Create orchestrator:
```python
orch = GenieOrchestrator(
    llm=llm,
    client=w,
)
```
> No `space_ids` passed — defaults to `[GENIE_SPACE_ID]` (the unified space).

**Cell 40** — Run it:
```python
orch.execute("What are the top 5 selling vehicle models by total revenue?", "llm")
```
> Full pipeline: router rewrites + routes, Genie generates SQL + executes, LLM formats a polished Markdown summary. Output formats: `"full"` (question + SQL + answer), `"text"` (answer only), `"llm"` (Markdown), `"raw"` (return dict).

---

### Step 2 Checkpoint

**Presenter:**

> "We now have a single-space orchestrator: LLM rewrites the question, Genie answers it, and we get a formatted result. But real organizations don't have one Genie Space — they have Sales, CRM, Operations, each with different tables. What changes?"

*(Transition to Step 3)*

---

## Step 3: Multi-Genie Orchestration (Cells 41–55)

### 3A. Multi-Space Routing (Cells 41–49)

**Presenter:**

Draw on the board:

```
  Question
     |
     v
  ask_router (LLM)
     |--- reads metadata from ALL spaces
     |
     +---> Sales Genie        (revenue, orders, vehicles)
     +---> Customer Genie     (segments, interactions, leads)
     +---> Operations Genie   (parts, service, inventory)
```

> "Same router, same orchestrator — but now initialized with 3 space IDs instead of 1. The router reads metadata from all spaces and picks the best match."

**Code Lead:**

**Cell 42** — List available spaces (provided, just run). Shows all Velocity Motors spaces in the workspace.

**Cell 43** — Configure domain spaces:
```python
DOMAIN_SPACES = [
    "01f0fe356cbe15a7a4259f6822d1ebe8",  # Sales Analytics
    "01f0fe356c771e348b333b15f82c2e15",  # Customer Intelligence
    "01f0fe356c511a278a49fdc1e83797e3",  # Operations & Inventory
]

multi_orch = GenieOrchestrator(
    llm=llm,
    space_ids=DOMAIN_SPACES,
    client=w,
)
```
> Same `GenieOrchestrator` class, just more space IDs. It caches each space's title at init time.

**Run cells 45–49** — demonstrate routing to different spaces:
- Cell 45: "top 5 selling vehicle models by revenue" -> routes to Sales
- Cell 46: "which customer segments generate most service revenue" -> routes to Customer
- Cell 47: "which parts are below reorder point" -> routes to Operations
- Cell 49: "customer lifetime value including service history" -> router must decide

> "Watch the `Routed to space:` output — each question lands on a different space."

---

### 3B. The Cross-Domain Problem

**Presenter:**

> "The router picks ONE space per question. But what about: 'Compare revenue by region with customer satisfaction ratings and parts inventory levels'? No single space has all that data."

*(Ask the audience: "How would you handle this?")*

*(Possible answers: join all tables in one space, run multiple queries and merge, use an LLM to combine. All valid — acknowledge them.)*

> "We'll use a decompose-then-synthesize pattern."

Draw on the board:

```
  "Compare revenue by region with satisfaction ratings
   and inventory levels"
              |
              v
      ask_decomposer (LLM)
              |
              +---> "Revenue by region" --> Sales Genie --> result 1
              +---> "Customer satisfaction ratings" --> CRM Genie --> result 2
              +---> "Parts inventory levels" --> Ops Genie --> result 3
              |
              v
        Synthesizer (LLM)
              |
              v
        Unified Answer
```

> "The LLM breaks the complex question into focused sub-queries, each targeting one space. After all results come back, another LLM call synthesizes them into a single answer."

---

### 3C. Decomposer Function (Cell 51)

**Code Lead:**

Walk through cell 51 — `ask_decomposer`. Same structure as `ask_router` but returns a list instead of a single dict. Two fill-ins:

**Fill-in 1** — Build space metadata prompt (same pattern as router):
```python
for space_id in genie_spaces:
    space_metadata = GenieUtils.get_space_metadata(space_id, client=client, enrich_columns=True)
    prompt += f"Space ID: {space_id}\nMetadata: {space_metadata}\n\n"
```
> Identical to the router. Reinforces the pattern — every LLM that needs to make routing decisions gets the same metadata context.

**Fill-in 2** — LLM invoke + JSON parse:
```python
response = llm.invoke(prompt)
sub_queries = json.loads(response.content)
```
> Same as the router, but the expected output is a JSON list: `[{"query": "...", "space_id": "..."}, ...]`. The `isinstance(sub_queries, list)` check below validates the shape.

---

### 3D. Execute Multi — The Full Pipeline (Cell 52)

**Code Lead:**

Walk through cell 52 — `execute_multi`. Three fill-ins covering decompose, fan-out, and synthesize:

**Fill-in 1** — Call the decomposer:
```python
sub_queries = ask_decomposer(
    llm=self.llm,
    question=user_question,
    genie_spaces=self.space_ids,
    client=self.client,
)
```
> The decomposer decides both *what* to ask and *where*. A complex question might produce 2–3 sub-queries targeting different spaces.

**Fill-in 2** — Fan-out: call Genie for each sub-query:
```python
response = GenieUtils.ask_genie(
    query=sq["query"],
    space_id=sq["space_id"],
    client=self.client,
)
```
> Each sub-query hits a different space. The `try/except` around this ensures one failure doesn't crash the whole pipeline — failed results are recorded with `"success": False`.

**Fill-in 3** — Synthesize all results:
```python
synthesis = self.llm.invoke(synthesis_prompt)
```
> The synthesis prompt includes the original question and all sub-query results formatted as `--- Space Title ---\nQuery: ...\nAnswer: ...`. The LLM combines insights across domains and highlights cross-domain patterns.

---

### 3E. Demo — Cross-Domain Queries (Cells 54–55)

**Code Lead:**

**Cell 54** — Spans all 3 domains:
```python
multi_orch.execute_multi(
    "Compare revenue by region with customer satisfaction ratings and parts inventory levels",
    output_format="llm",
)
```
> Watch the decomposer create 3 sub-queries, each routing to a different space. Then the synthesizer combines them.

**Cell 55** — Spans 2 domains:
```python
multi_orch.execute_multi(
    "Which vehicle models have the highest service costs relative to their sale price?",
    output_format="llm",
)
```
> The decomposer only creates 2 sub-queries here (Sales + Operations) — it uses as many as needed, not always all 3.

---

### Step 3 Checkpoint / Wrap-Up

**Presenter:**

> "We started with a single SDK call, wrapped it in utilities, added an LLM router, scaled to multiple spaces, and built a decompose-synthesize pipeline for cross-domain questions. Each layer added one capability."

Refer to the summary table in cell 56 — it maps every concept to its code.

---

## Quick Reference

### Architecture Progression

```
Step 1: Raw SDK                Step 2: Single Orchestrator

  Question                       Question
     |                              |
     v                              v
  Genie SDK                    Router (LLM)
     |                           |        |
     v                       rewrite   space_id
  GenieMessage                   |        |
     |                           v        v
     v                        Genie SDK (rewritten query)
  sql + text                     |
                                 v
                           format output


Step 3: Multi-Genie Synthesis

  Complex Question
       |
       v
   Decomposer (LLM) --> [sub-query 1, sub-query 2, sub-query 3]
       |
       +---> Genie (Space A) --> result 1
       +---> Genie (Space B) --> result 2
       +---> Genie (Space C) --> result 3
       |
       v
   Synthesizer (LLM)
       |
       v
   Unified Answer
```

### SDK Method Reference

| Method | Blocks? | Returns | Use when |
|---|---|---|---|
| `genie.start_conversation_and_wait()` | Yes | `GenieMessage` | New question (simple path) |
| `genie.start_conversation()` | No | `conv_id` + `msg_id` | Need status polling |
| `genie.get_message()` | No | `GenieMessage` | Polling in a loop |
| `genie.create_message_and_wait()` | Yes | `GenieMessage` | Follow-up in same conversation |
| `genie.get_message_attachment_query_result()` | Yes | Query result | Need raw data rows |
| `genie.get_space()` | Yes | Space metadata | Space title or config |

### Fill-In Counts by Section

| Section | Inside functions | Usage cells | Total |
|---|---|---|---|
| Step 1: Connect to Genie | 7 | 6 | 13 |
| Step 2: Single Orchestrator | 4 | 7 | 11 |
| Step 3: Multi-Genie + Synthesis | 5 | 0 | 5 |
| **Total** | **16** | **13** | **29** |
