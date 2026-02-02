# Genie SDK Demo — Workshop Presenter Script

**Notebooks:**
- Workshop (fill-in): `01_genie_sdk_demo.ipynb`
- Answer key: `Genie SDK Demo_v1.ipynb`

**Roles:**
- **Presenter** — Introduces concepts, draws architecture diagrams, poses questions to the audience, frames the "why"
- **Code Lead** — Walks through the notebook cells, explains the code, gives fill-in time, runs demos

**Ground Rules for Delivery:**
- Blockquotes (`>`) are key sentences — say them verbatim or close to it
- Bullet points are flexible talking points — adapt to your audience
- `[DRAW]` means sketch on whiteboard/iPad
- `[PAUSE]` means wait for audience response
- `[RUN]` means execute the cell and show output
- `[FILL-IN]` means give attendees time to write code

---

## Pre-Workshop Setup (Before Attendees Arrive)

### Environment Checklist
- [ ] All attendees have Databricks workspace access
- [ ] Workshop notebook cloned to each user's folder
- [ ] Genie Space IDs from `00c_setup_genie` are ready (3 domain + 1 unified)
- [ ] A running cluster with `databricks-langchain` installed
- [ ] Presenter mode enabled if using `display_solution()` helpers
- [ ] Test one Genie query yourself to confirm spaces are responsive

### Notebook Pre-Run
Cells 2 (pip install), 4 (imports), 6-8 (widget config) are run-once setup with no fill-ins. Code Lead should run these while Presenter does introductions.

---

## Opening (5 min)

**Presenter:**

> "Welcome everyone. Today we're going to build an AI data analyst — piece by piece. We'll start with a single API call and end with a system that can decompose a complex business question, route it to multiple data domains, and synthesize a unified answer."

- Set expectations: this is hands-on. Every concept is backed by code you'll write.
- Quick show of hands: who has used Genie in the UI? Who has used the Databricks SDK?
- Reassure: no prior Genie experience needed. We start from zero.

> "There are three steps. Step 1: connect to Genie and query it with code. Step 2: put an LLM in front of Genie so it can rewrite questions to match your schema. Step 3: orchestrate multiple Genie Spaces to answer questions that span Sales, CRM, and Operations."

- The notebook has fill-in-the-blank sections. We'll walk through each one together.
- If you get stuck, the answer key notebook has everything filled in.

---

## Step 1: Connect to Genie (Cells 0-25)

### 1A. What is Genie? (3 min)

**Presenter:**

> "Let's start with the problem. You have structured data in Unity Catalog — sales transactions, customer records, inventory. Your business analysts want to ask questions in plain English without writing SQL. That's what Genie does."

- Genie is not a general-purpose chatbot. It's a text-to-SQL engine with a curated context window.
- You tell it which tables to use, describe the columns, give it sample questions. Genie uses that context to generate SQL from natural language.

> "Think of a Genie Space as a curated lens over your data — you decide what it can see, and you describe the columns so it understands the business meaning."

`[DRAW]` Architecture on the board:

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

- The Space metadata (table names, column descriptions, sample questions) is what makes Genie accurate. Bad metadata = bad SQL.
- This is why we spent time in the setup notebooks adding column comments to Unity Catalog.

> "Today we'll connect to Genie programmatically — same engine, but through code instead of the UI."

---

### 1B. Connect + First Query (Cells 13-14) (5 min)

**Code Lead:**

> "First we need a `WorkspaceClient` — this is the Databricks SDK's entry point. It handles all authentication."

**Cell 13** — `[FILL-IN]` Create WorkspaceClient:
```python
w = WorkspaceClient()
```

- No arguments needed inside Databricks notebooks. The SDK auto-detects the current user's U2M (user-to-machine) auth.
- If you were running this locally, you'd pass `host` and `token`. But inside a notebook, it just works.

`[RUN]` the cell. No output expected — that's fine, it means auth succeeded.

**Cell 14** — `[FILL-IN]` First Genie query:
```python
msg = w.genie.start_conversation_and_wait(
    space_id=GENIE_SPACE_ID,
    content="What are the top 10 vehicles by total order value?",
    timeout=timedelta(seconds=120),
)
```

> "This is the core SDK call. `start_conversation_and_wait` sends a natural language question, blocks until Genie generates SQL, executes it, and returns an answer. The `timeout` prevents it from hanging forever."

- `space_id` — which Genie Space to query (we configured this in the widgets above)
- `content` — the natural language question
- `timeout` — safety net; Genie usually responds in 5-15 seconds

`[RUN]` the cell. Wait for it to complete.

> "Look at what came back — it's a `GenieMessage` object. Notice `attachments`, `conversation_id`, `status`. The actual answer is buried inside the attachments. Let's extract it."

- Point out the raw object structure on screen. It's not immediately human-readable — that's intentional, it's a data structure.
- The `conversation_id` is important — we'll use it later for follow-up questions.

---

### 1C. Parse the Response (Cells 16-18) (5 min)

**Presenter:**

> "Genie gave us back a `GenieMessage`. But the answer is buried inside `attachments`. Not every attachment has both SQL and text. How would you safely extract the text answer?"

`[PAUSE]` — take a response from the audience. Someone will likely suggest a loop or list comprehension.

**Code Lead:**

**Cell 16** — `[FILL-IN]` Extract text from attachments:
```python
answer = next(
    (att.text.content for att in msg.attachments if att.text and att.text.content),
    None,
)
```

> "This is a Python pattern: find the first matching element or return `None`. The double check — `att.text` AND `att.text.content` — avoids an `AttributeError` if an attachment has no text block at all."

- Why `next()` with a default? Because some attachments only have SQL, no text. We want the first text we find.
- Production code would also extract the SQL from `att.query.query` — we'll do that in the utility class.

`[RUN]` Cell 16, then print `answer`.

**Cell 18** — `[RUN]` `GenieUtils.print_output(msg)` to show the formatted version.

> "This helper formats it nicely — question at the top, SQL in the middle, answer at the bottom. We'll build this helper ourselves in a few minutes."

---

### 1D. Multi-Turn Conversations (Cells 20-21) (3 min)

**Presenter:**

> "What if your analyst asks a follow-up? 'Now break that down by customer segment.' Do they start over from scratch?"

`[PAUSE]` — brief audience response.

> "No. Genie supports multi-turn conversations. You pass the `conversation_id` back and Genie remembers the SQL context from before."

- This is the same pattern as ChatGPT conversations — context carries forward.
- Under the hood, Genie uses the previous SQL as context for the next question.

**Code Lead:**

**Cell 20** — already provided. Just `[RUN]` it to extract `conversation_id`:
```python
conversation_id = msg.conversation_id
```

**Cell 21** — `[FILL-IN]` Follow-up conversation:
```python
followup = w.genie.create_message_and_wait(
    space_id=GENIE_SPACE_ID,
    conversation_id=conversation_id,
    content="Break that down by customer segment",
    timeout=timedelta(seconds=120),
)
```

> "Notice the method name changed: `create_message_and_wait`, not `start_conversation`. And we pass in the `conversation_id` from the first response. That's what links them together."

- `start_conversation_and_wait` = new conversation
- `create_message_and_wait` = continue existing conversation
- Everything else is the same — question in, `GenieMessage` out.

`[RUN]` and show the result. Point out how it references "customer segment" correctly because it has the prior SQL context.

---

### 1E. GenieUtils — Wrapping the SDK (Cell 11) (10 min)

**Presenter:**

> "We've been writing raw SDK calls and extracting attachments manually every time. That's fine for exploration, but what happens when you need to do this 50 times across a codebase?"

`[PAUSE]` — someone says "wrap it in a function" or "make a class."

> "Exactly. The `GenieUtils` class is provided for you — but some key lines inside the methods are missing. Let's walk through each method and fill in the SDK calls."

**Code Lead:**

Walk through Cell 11 method by method. For each: explain what it does, show the signature, then give fill-in time.

#### `print_output(message)` — `[FILL-IN]` Attachment loop body:
```python
for att in message.attachments or []:
    if att.query and att.query.query and sql is None:
        sql = att.query.query
    if att.text and att.text.content and answer is None:
        answer = att.text.content
```

> "Same pattern as cell 16, but structured. We iterate all attachments, grab the first SQL and first text answer. The `or []` guards against `None` if there are no attachments."

- Why `sql is None` check? First match wins. Some messages have multiple attachments.
- This is defensive programming — handle the weird edge cases so callers don't have to.

#### `ask_genie(query, space_id, client)` — `[FILL-IN]` SDK call:
```python
msg = client.genie.start_conversation_and_wait(
    space_id=space_id,
    content=query,
    timeout=timedelta(seconds=120),
)
```

> "Same SDK call as cell 14, now inside a reusable method. One place to change the timeout, add error handling, or add logging."

#### `ask_genie` — `[FILL-IN]` Attachment parsing (dict version):
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

> "We convert the message to a dict with `as_dict()` for key-based access. `sql = sql or ...` means first query attachment wins. We collect all text fragments and later pick the longest one with `max(text_contents, key=len)`."

- Why dict access here instead of object attributes? Consistency with serialization — dicts are JSON-friendly.
- The `max(..., key=len)` trick: Genie sometimes returns a short confirmation AND a long answer in separate text blocks. We want the long one.

#### `to_dataframe(result, client)` — `[FILL-IN]` Fetch query result:
```python
qr = client.genie.get_message_attachment_query_result(
    space_id=msg.space_id,
    conversation_id=msg.conversation_id,
    message_id=msg.id,
    attachment_id=att["attachment_id"],
)
```

> "This is a separate API call because query results can be large. Four IDs uniquely identify which result to fetch — space, conversation, message, and attachment."

#### `to_dataframe` — `[FILL-IN]` Build DataFrame:
```python
columns = [c.name for c in (stmt.manifest.schema.columns or [])]
rows = stmt.result.data_array or []
```

> "Column names from `.manifest.schema.columns`, data rows from `.result.data_array`. Both are lists. Wrap them in a pandas DataFrame and you're done."

#### `ask_genie_verbose` — `[FILL-IN]` Start conversation (non-blocking):
```python
conv = client.genie.start_conversation(
    space_id=space_id,
    content=query,
)
```

> "`start_conversation` without `_and_wait` returns immediately. We get back `conversation_id` and `message_id` to poll with."

#### `ask_genie_verbose` — `[FILL-IN]` Poll for status:
```python
msg = client.genie.get_message(
    space_id=space_id,
    conversation_id=conversation_id,
    message_id=message_id,
)
```

> "Called in a `while True` loop with `time.sleep(2)`. We check `msg.status.value` each iteration until it says `COMPLETED` or `FAILED`."

- This is what `start_conversation_and_wait` does under the hood — we've exposed the polling loop so you can see the lifecycle.

---

### 1F. Utilities in Action (Cells 23-25) (5 min)

**Code Lead:**

**Cell 23** — `[RUN]` `ask_genie_verbose`:

> "Watch the status transitions print out: `SUBMITTED` then `ASKING_AI` then `EXECUTING_QUERY` then `COMPLETED`. This is the Genie lifecycle — your question goes through an LLM step (SQL generation), then a query execution step."

- If anyone sees `FAILED`, check the Genie Space permissions and table access.

**Cell 25** — `[FILL-IN]` Convert to DataFrame:
```python
result = GenieUtils.ask_genie("What are the total orders by region?", GENIE_SPACE_ID, client=w)
df = GenieUtils.to_dataframe(result, client=w)
```

> "This chains two utilities: `ask_genie` sends the question and parses the response, `to_dataframe` makes a second API call to get the raw data rows and wraps them in a pandas DataFrame."

`[RUN]` and show the DataFrame output. This is where it clicks — they can see actual tabular data.

- Point out: this DataFrame is now a normal pandas object. You can plot it, join it, export it — whatever you'd do with any DataFrame.

---

### Step 1 Checkpoint (2 min)

**Presenter:**

> "Let's take stock. We can now query Genie programmatically, parse responses, follow up in conversations, get DataFrames, and we have a utility class wrapping it all."

Recap what we built:
- `WorkspaceClient()` — authentication
- `start_conversation_and_wait()` — blocking query
- `create_message_and_wait()` — follow-up query
- `GenieUtils` — reusable wrapper with `ask_genie`, `to_dataframe`, `print_output`

> "But we're still hand-writing every question. What happens when the user says 'revenue by region' but the column is called `total_order_value`? Genie might figure it out. Or it might not."

`[PAUSE]` — let that sink in.

> "We need something smarter in front of Genie."

---

## Step 2: Single Genie Orchestrator (Cells 26-40)

### 2A. The Schema Mismatch Problem (3 min)

**Presenter:**

> "Your user asks 'what's the revenue by region?' but the column is called `total_order_value`, not `revenue`. The table has `dealer_region`, not just `region`. Genie's context window helps, but it doesn't always bridge that gap."

> "How do we fix this?"

`[PAUSE]` — someone will say "use an LLM."

> "Right. We put an LLM in front of Genie as a router. It reads the table schemas — column names, types, descriptions — and rewrites the user's question to match the actual data model. Then it sends the improved question to Genie."

`[DRAW]` on the board:

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

- The router does two things: **rewrite** and **route**.
- Rewrite: "revenue" becomes "total_order_value". "Region" becomes "dealer_region".
- Route: with multiple spaces, it picks the right one. With a single space, it still rewrites.

> "The LLM doesn't touch the data. It just makes the question Genie-friendly."

---

### 2B. LLM Setup (Cells 27-29) (3 min)

**Code Lead:**

Cell 27 — MLflow setup. Just `[RUN]` it, no fill-in.

**Cell 28** — `[FILL-IN]` Create the LLM:
```python
llm = ChatDatabricks(
    endpoint="databricks-gpt-5-nano",
    temperature=1,
)
```

> "`ChatDatabricks` connects to a Model Serving endpoint. The `endpoint` parameter is the name of the serving endpoint — you can find it under AI/ML > Serving in the sidebar."

- `temperature=1` gives the LLM some creativity in rewriting. For routing, you could argue for lower temperature, but rewrites benefit from flexibility.
- This is `databricks-langchain`'s integration — it wraps the Databricks model serving API in a LangChain-compatible interface.

**Cell 29** — `[FILL-IN]` Test the LLM:
```python
llm.invoke("How is the weather today?")
```

> "Quick sanity check that the endpoint is reachable. If this fails, check your cluster's network access to the model serving endpoint."

`[RUN]` it. Confirm you get a response. Content doesn't matter — we just need to know the pipe works.

---

### 2C. Space Metadata + Router (Cells 31-36) (10 min)

**Code Lead:**

**Cell 31** — `[FILL-IN]` Practice calling `ask_genie`:
```python
GenieUtils.ask_genie("How many orders were placed last month by payment method?", GENIE_SPACE_ID, client=w)
```

> "Quick practice using the utility we just built. This should feel natural now."

`[RUN]` it.

**Cell 33** — `[RUN]` See what the router will receive:
```python
GenieUtils.get_space_metadata(GENIE_SPACE_ID, client=w, enrich_columns=True)
```

**Presenter:**

> "Look at this output. Table names, column names with their types and descriptions, sample questions. This is everything the LLM needs to understand the data model."

- Walk through the output on screen. Point out a few columns: "See `total_order_value` with type `DOUBLE` and description 'Total value of the order'? That's how the LLM knows 'revenue' maps to this column."
- `enrich_columns=True` fetches full Unity Catalog schemas — richer metadata but extra API calls.
- The sample questions are especially useful — they show the LLM what kinds of questions work for this space.

> "The quality of this metadata determines the quality of the routing. Good column descriptions = good rewrites."

**Code Lead:**

Now walk through **Cell 35** — the `ask_router` function. Two fill-ins:

The router prompt is structured as:
```
You are an intelligent router for Databricks Genie AI.
Improve and augment the question to be maximally useful to Genie.

Return only a dictionary:
{
    "query": "The improved version of the question",
    "space_id": "The genie space to route to"
}

Question: {question}

Genie Spaces Available and their metadata:
{space_metadata}
```

**Fill-in 1** — `[FILL-IN]` Build space metadata prompt:
```python
for space_id in genie_spaces:
    space_metadata = GenieUtils.get_space_metadata(space_id, client=client, enrich_columns=True)
    prompt += f"Space ID: {space_id}\nMetadata: {space_metadata}\n"
```

> "Loop over all spaces, fetch metadata, append to the prompt. The LLM needs column-level detail to rewrite queries accurately. With a single space, this loop runs once. With three spaces, it runs three times — same code either way."

**Fill-in 2** — `[FILL-IN]` LLM invoke + JSON parse:
```python
response = llm.invoke(prompt)
obj = json.loads(response.content)
```

> "Send the full prompt to the LLM, parse the JSON response. The prompt asked the LLM to return `{\"query\": ..., \"space_id\": ...}`. `response.content` is a string — `json.loads` converts it to a dict we can use."

- Production note: if the LLM returns markdown fences or extra text, `json.loads` will crash. In production code (see `src/agents/supervisor.py`), add retry logic and strip fences. For the workshop, this is fine.

**Cell 36** — `[FILL-IN]` Call the router:
```python
router_response = ask_router(llm, "Which vehicle models have the most service orders?", [GENIE_SPACE_ID], client=w)
```

`[RUN]` and inspect the output.

> "Look at the output. The original question was 'Which vehicle models have the most service orders?' — see how the LLM rewrote it? It probably used the exact column names from the metadata. And it picked the right `space_id`."

- Show the before (user question) and after (rewritten query). The difference is the value of the router.

---

### 2D. GenieOrchestrator — Wire It Together (Cells 38-40) (5 min)

**Presenter:**

> "We have the router and Genie as separate pieces. Now we wire them into a single `execute()` call. Question goes in, formatted answer comes out."

**Code Lead:**

Walk through **Cell 38** — the `GenieOrchestrator` class. Two fill-ins inside `execute()`:

**Fill-in 1** — `[FILL-IN]` Call the router:
```python
router_response = ask_router(
    llm=self.llm,
    question=user_question,
    genie_spaces=self.space_ids,
    client=self.client,
)
```

> "`self.space_ids` can be one space or many. With one, the router still rewrites the question. With many, it also picks the best space."

**Fill-in 2** — `[FILL-IN]` Call Genie with the rewritten query:
```python
genie_response = GenieUtils.ask_genie(
    query=router_response["query"],
    space_id=routed_id,
    client=self.client,
)
```

> "Key detail: we use `router_response[\"query\"]` — the rewritten version — not the original `user_question`. That's the whole point of the router. `routed_id` comes from `router_response[\"space_id\"]`."

**Cell 39** — `[FILL-IN]` Create orchestrator:
```python
orch = GenieOrchestrator(
    llm=llm,
    client=w,
)
```

- No `space_ids` passed — defaults to `[GENIE_SPACE_ID]` (the unified space).

**Cell 40** — `[FILL-IN]` Run it:
```python
orch.execute("What are the top 5 selling vehicle models by total revenue?", "llm")
```

`[RUN]` it.

> "Full pipeline: router rewrites the question, Genie generates SQL and executes it, then an LLM formats a polished Markdown summary."

Walk through the output formats:
- `"full"` — question + SQL + answer (good for debugging)
- `"text"` — answer only (good for end users)
- `"llm"` — LLM-formatted Markdown (good for reports and presentations)
- `"raw"` — returns the dict (good for programmatic use)

---

### Step 2 Checkpoint (2 min)

**Presenter:**

> "We now have a single-space orchestrator: the LLM rewrites the question to match the schema, Genie answers it, and we get a formatted result."

Recap what we added:
- `ChatDatabricks` — LLM connection via Model Serving
- `get_space_metadata()` — feeds the LLM the column-level context
- `ask_router()` — rewrites + routes
- `GenieOrchestrator.execute()` — full pipeline in one call

> "But real organizations don't have one Genie Space. They have Sales, CRM, Operations — each with different tables, different schemas, different owners. What changes?"

`[PAUSE]` — let them think.

> "The code barely changes. The architecture does."

---

## Step 3: Multi-Genie Orchestration (Cells 41-55)

### 3A. Multi-Space Routing (Cells 41-49) (8 min)

**Presenter:**

`[DRAW]` on the board:

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

> "Same router, same orchestrator — but now initialized with 3 space IDs instead of 1. The router reads metadata from all three spaces and picks the best match for each question."

- Each space covers a different business domain.
- The router sees all three sets of column names and descriptions.
- The question determines which space gets chosen.

> "This is where the metadata quality really matters. If Sales and Operations both have a `total_value` column, the descriptions need to be clear enough for the LLM to pick the right one."

**Code Lead:**

**Cell 42** — `[RUN]` List available spaces. Shows all Velocity Motors Genie Spaces in the workspace.

**Cell 43** — `[FILL-IN]` Configure domain spaces and create multi-space orchestrator:
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

> "Same `GenieOrchestrator` class, just more space IDs. It caches each space's title at init time so the output shows human-readable names."

Now run the demo cells. For each, highlight which space the router chose.

**Cell 45** — `[RUN]` "top 5 selling vehicle models by revenue":
> "Watch the `Routed to space:` output. Revenue + vehicle models = Sales."

**Cell 46** — `[RUN]` "which customer segments generate most service revenue":
> "Customer segments = Customer Intelligence space."

**Cell 47** — `[RUN]` "which parts are below reorder point":
> "Parts + reorder = Operations."

**Cell 49** — `[RUN]` "customer lifetime value including service history":
> "This one's ambiguous — it touches both Customer and Operations. Watch which space the router picks and whether the answer is complete."

**Presenter:**

> "That last question is the interesting one. The router picked ONE space. But the answer needs data from TWO. The router was forced to choose, and the answer is incomplete."

`[PAUSE]` — let them feel the limitation.

> "This is the fundamental limitation of single-route architectures. Some questions don't fit in one box."

---

### 3B. The Cross-Domain Problem (3 min)

**Presenter:**

> "How would you handle: 'Compare revenue by region with customer satisfaction ratings and parts inventory levels'? No single Genie Space has all that data."

`[PAUSE]` — take audience responses. Acknowledge all approaches:
- "Join all tables in one space" — works but doesn't scale, and you lose domain ownership
- "Run multiple queries and merge manually" — works but tedious
- "Use an LLM to combine" — that's where we're going

> "We'll use a decompose-then-synthesize pattern. An LLM breaks the complex question into focused sub-queries, each targeting one space. After all results come back, another LLM call synthesizes them into a single answer."

`[DRAW]` on the board:

```
  "Compare revenue by region with satisfaction ratings
   and inventory levels"
              |
              v
      ask_decomposer (LLM)
              |
              +---> "Revenue by region" --> Sales Genie --> result 1
              +---> "Satisfaction ratings" --> CRM Genie --> result 2
              +---> "Parts inventory levels" --> Ops Genie --> result 3
              |
              v
        Synthesizer (LLM)
              |
              v
        Unified Answer
```

> "Three LLM calls total: one to decompose, one per sub-query result isn't an LLM call — it's a Genie call, and one to synthesize. The Genie calls are just SDK calls, not LLM calls."

- The decomposer uses the same metadata as the router — it knows what columns exist in each space.
- The synthesizer sees all the answers and finds cross-domain patterns.
- If one space fails, the others still return results. The synthesizer notes the gap.

---

### 3C. Decomposer Function (Cell 51) (5 min)

**Code Lead:**

Walk through **Cell 51** — `ask_decomposer`. Same structure as `ask_router` but returns a list.

The decomposer prompt is structured as:
```
You are a query decomposer for Databricks Genie AI.
Break the question into focused sub-queries targeting exactly one Genie Space each.

Return ONLY a JSON list:
[
    {"query": "Sub-question for this space", "space_id": "Target space ID"}
]

Rules:
- Each sub-query targets exactly one space_id
- Keep sub-queries simple and specific
- Use 1-4 sub-queries (only as many as needed)
```

**Fill-in 1** — `[FILL-IN]` Build space metadata prompt (same pattern as router):
```python
for space_id in genie_spaces:
    space_metadata = GenieUtils.get_space_metadata(space_id, client=client, enrich_columns=True)
    prompt += f"Space ID: {space_id}\nMetadata: {space_metadata}\n\n"
```

> "Identical to the router. This pattern is deliberate — every LLM that needs to make routing decisions gets the same metadata context. One loop, same API call, same structure."

**Fill-in 2** — `[FILL-IN]` LLM invoke + JSON parse:
```python
response = llm.invoke(prompt)
sub_queries = json.loads(response.content)
```

> "Same as the router, but the expected output is a JSON list instead of a single dict: `[{\"query\": ..., \"space_id\": ...}, ...]`. The `isinstance(sub_queries, list)` check below validates the shape."

- The decomposer decides both *what* to ask and *where* to ask it.
- Simple questions produce 1 sub-query (equivalent to routing).
- Complex cross-domain questions produce 2-4 sub-queries.

---

### 3D. Execute Multi — The Full Pipeline (Cell 52) (8 min)

**Code Lead:**

Walk through **Cell 52** — `execute_multi()` on the `GenieOrchestrator` class. Three fill-ins covering the full decompose-fan-out-synthesize flow.

**Fill-in 1** — `[FILL-IN]` Call the decomposer:
```python
sub_queries = ask_decomposer(
    llm=self.llm,
    question=user_question,
    genie_spaces=self.space_ids,
    client=self.client,
)
```

> "The decomposer decides both what to ask and where. A complex question might produce 2-3 sub-queries, each targeting a different space."

**Fill-in 2** — `[FILL-IN]` Fan-out: call Genie for each sub-query:
```python
response = GenieUtils.ask_genie(
    query=sq["query"],
    space_id=sq["space_id"],
    client=self.client,
)
```

> "Each sub-query hits a different space. Notice the `try/except` around this — if one space is slow or fails, the others still return results. Failed sub-queries are recorded with `success: False`."

- This runs sequentially in the workshop for simplicity. In production (see `src/agents/multi_genie_orchestrator.py`), you'd use `ThreadPoolExecutor` for parallel queries.

**Fill-in 3** — `[FILL-IN]` Synthesize all results:
```python
synthesis = self.llm.invoke(synthesis_prompt)
```

> "The synthesis prompt includes the original question AND all sub-query results formatted as sections: space title, query, answer. The LLM combines insights across domains and highlights cross-domain patterns."

- The synthesis prompt is already built for you above this fill-in. Walk through its structure if time allows.
- The LLM is being asked to find relationships *between* the results, not just summarize each one.

---

### 3E. Demo — Cross-Domain Queries (Cells 54-55) (5 min)

**Code Lead:**

**Cell 54** — `[RUN]` Spans all 3 domains:
```python
multi_orch.execute_multi(
    "Compare revenue by region with customer satisfaction ratings and parts inventory levels",
    output_format="llm",
)
```

> "Watch the output carefully. First you'll see the decomposer split this into 3 sub-queries. Then each one routes to a different space. Then the synthesizer combines all three into a single answer."

- Point out: the decomposer created 3 sub-queries, one per domain. Not 2, not 4 — exactly as many as the question needed.
- Show the final synthesized answer. It should reference data from all three domains.

**Cell 55** — `[RUN]` Spans 2 domains:
```python
multi_orch.execute_multi(
    "Which vehicle models have the highest service costs relative to their sale price?",
    output_format="llm",
)
```

> "This question only needs Sales and Operations — not Customer. Watch: the decomposer only creates 2 sub-queries. It's smart enough to use only what it needs."

- The decomposer isn't hardcoded to always query all spaces. It reads the question and decides.

---

### Step 3 Checkpoint / Wrap-Up (5 min)

**Presenter:**

> "Let's look at what we built, layer by layer."

`[DRAW]` the final architecture progression or reference the summary in cell 56:

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

> "We started with a single SDK call. We wrapped it in utilities. We added an LLM router to rewrite questions. We scaled to multiple spaces. And we built a decompose-synthesize pipeline for cross-domain questions. Each layer added exactly one capability."

Key takeaways to leave the audience with:
- **Genie is a text-to-SQL engine**, not a chatbot. Its quality depends on metadata quality.
- **The LLM router is the bridge** between user language and schema language. It doesn't touch the data.
- **Decompose-synthesize is the pattern** for multi-domain questions. It's the same pattern used in production multi-agent systems.
- **Everything composes**: `WorkspaceClient` > `GenieUtils` > `ask_router` > `GenieOrchestrator` > `execute_multi`. Each layer uses the one below.

> "If you want to see the production version of this with retries, circuit breakers, parallel execution, and LangGraph orchestration — check out the `src/agents/` directory. The concepts are identical, the resilience is higher."

---

## Quick Reference

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

### Architecture Progression (ASCII)

```
Step 1: Raw SDK                Step 2: Single Orchestrator       Step 3: Multi-Genie Synthesis

  Question                       Question                        Complex Question
     |                              |                                  |
     v                              v                                  v
  Genie SDK                    Router (LLM)                    Decomposer (LLM)
     |                           |        |                          |
     v                       rewrite   space_id               sub-queries[]
  GenieMessage                   |        |                    /     |     \
     |                           v        v                   v      v      v
     v                        Genie SDK               Genie A  Genie B  Genie C
  sql + text                     |                          \    |    /
                                 v                           v   v   v
                           format output               Synthesizer (LLM)
                                                              |
                                                              v
                                                        Unified Answer
```

### Troubleshooting Quick Hits

| Symptom | Likely Cause | Fix |
|---|---|---|
| `WorkspaceClient()` fails | Not on a Databricks cluster | Check cluster is running, or pass `host`/`token` |
| Genie query hangs past timeout | Space is cold or misconfigured | Restart cluster, check Space exists in UI |
| `json.loads` crashes | LLM returned markdown fences | Strip content before parsing, or add retry |
| Router picks wrong space | Metadata too similar | Improve column descriptions in Unity Catalog |
| Decomposer returns 1 sub-query for cross-domain Q | Question too vague | Rephrase with explicit domain references |
| `get_message_attachment_query_result` 404 | Stale conversation/message ID | Re-run the query fresh |
