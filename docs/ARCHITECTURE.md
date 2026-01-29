# Architecture Guide

This document explains the technical architecture of the AI Data Analyst system.

## Overview

The workshop demonstrates a multi-agent architecture using LangGraph to orchestrate specialized AI agents:

```
User Question
      │
      ▼
┌─────────────────────┐
│  Supervisor Agent   │  (LangGraph StateGraph)
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

## Components

### 1. Supervisor Agent (`src/agents/supervisor.py`)

The supervisor orchestrates the workflow using LangGraph's StateGraph:

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    messages: Annotated[list, add]  # Accumulates conversation
    context: str                     # Current context
    iteration_count: int             # Prevents infinite loops

# Supervisor has two tools:
# - query_data: Routes to Genie for SQL/analytics
# - search_documents: Routes to RAG for policies/docs
```

**Routing Logic:**
- Data keywords (revenue, sales, product, trend) → Genie Agent
- Document keywords (policy, procedure, guide) → RAG Agent

### 2. Genie Agent (`src/agents/genie_agent.py`)

Wraps the Databricks Genie Conversation API:

```python
from databricks.sdk.service.dashboards import GenieAPI

class GenieDataAgent:
    def query(self, question: str) -> GenieResult:
        # Start conversation with Genie Space
        conversation = self.genie.start_conversation_and_wait(
            space_id=self.space_id,
            content=question
        )
        # Returns structured result with SQL and data
        return GenieResult(
            answer=conversation.response,
            sql_query=conversation.sql_query,
            data=conversation.data
        )
```

**Key Features:**
- Conversation continuity (multi-turn queries)
- Mock mode for testing without Databricks
- Markdown table formatting for results

### 3. RAG Agent (`src/agents/rag_agent.py`)

Uses Databricks Vector Search for document retrieval:

```python
from databricks.vector_search.client import VectorSearchClient

class RAGAgent:
    def search(self, query: str) -> str:
        # Search for similar documents
        results = self.vs_client.similarity_search(
            index_name=self.index_name,
            query_text=query,
            num_results=5
        )
        # Generate answer using retrieved context
        return self.generate_answer(query, results)
```

**Key Features:**
- Delta Sync index for real-time updates
- LLM-powered answer generation with citations
- Configurable similarity threshold

## Data Flow

### Query Routing

```
1. User: "What was Q4 revenue?"
   │
   ▼
2. Supervisor analyzes intent
   │
   ▼
3. Detects "revenue" → Data query
   │
   ▼
4. Calls Genie Agent tool
   │
   ▼
5. Genie generates SQL, executes, returns results
   │
   ▼
6. Supervisor formats response for user
```

### Multi-Step Reasoning

```
1. User: "Compare our refund policy with Q4 returns"
   │
   ▼
2. Supervisor needs both data AND documents
   │
   ▼
3. First: RAG Agent → Gets refund policy
   │
   ▼
4. Then: Genie Agent → Gets Q4 returns data
   │
   ▼
5. Supervisor synthesizes both into response
```

## LangGraph State Management

### State Schema

```python
class AgentState(TypedDict):
    messages: Annotated[list, add]  # Message history
    context: str                     # Retrieved context
    iteration_count: int             # Loop protection
```

### Graph Structure

```python
from langgraph.graph import StateGraph

builder = StateGraph(AgentState)

# Add nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("genie", genie_node)
builder.add_node("rag", rag_node)

# Add edges
builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_query,
    {"genie": "genie", "rag": "rag", "end": END}
)
builder.add_edge("genie", "supervisor")
builder.add_edge("rag", "supervisor")

graph = builder.compile()
```

## Configuration

### Environment-Based Config (`src/config.py`)

```python
class Config:
    genie_space_id: str
    model_endpoint: str
    mock_mode: bool
    vector_search_endpoint: str
    vector_search_index: str

    @classmethod
    def from_env(cls):
        """Load from environment variables."""
        ...

    @classmethod
    def from_notebook_params(cls, dbutils):
        """Load from Databricks notebook widgets."""
        ...

    @classmethod
    def from_databricks_secrets(cls, scope: str):
        """Load from Databricks secret scope."""
        ...
```

## Advanced: Multi-Genie Architecture (Part 3)

For complex domains, use multiple Genie Spaces:

```
User Question
      │
      ▼
┌─────────────────────┐
│  Domain Supervisor  │
└─────────┬───────────┘
          │
    ┌─────┼─────┐
    │     │     │
    ▼     ▼     ▼
┌──────┐ ┌──────┐ ┌──────┐
│Sales │ │ CRM  │ │ Ops  │
│Genie │ │Genie │ │Genie │
└──────┘ └──────┘ └──────┘
          │
          ▼
┌─────────────────────┐
│  Report Generator   │
└─────────────────────┘
```

Each Genie Space is optimized for its domain:
- **Sales:** Revenue, orders, products
- **CRM:** Customers, segments, interactions
- **Operations:** Inventory, suppliers, logistics

## MLflow Integration

> **Note:** This section describes planned capabilities not yet implemented in the current workshop code.

All agent executions are traced with MLflow:

```python
import mlflow

# Enable automatic tracing
mlflow.langchain.autolog()

# Set experiment
mlflow.set_experiment("/Shared/ai-data-analyst-workshop")

# Traces are visible in MLflow UI
```

**What's Traced:**
- Input/output at each node
- Tool calls and responses
- Latency per step
- Token usage

## Key Patterns

### 1. Tool Calling

```python
@tool
def query_data(question: str) -> str:
    """Query structured business data via Genie."""
    return genie_agent.query(question)

@tool
def search_documents(query: str) -> str:
    """Search company policies and procedures."""
    return rag_agent.search(query)
```

### 2. Error Handling

```python
def safe_genie_call(state):
    try:
        result = genie.query(state["messages"][-1])
        return {"messages": [{"role": "assistant", "content": result}]}
    except Exception as e:
        return {"messages": [{"role": "assistant", "content": f"Error querying data: {e}"}]}
```

### 3. Iteration Limits

```python
def should_continue(state) -> str:
    if state["iteration_count"] >= 5:
        return "end"
    if is_complete(state):
        return "end"
    return "continue"
```

## Deployment

### Option 1: Notebook-Based (Workshop)

Run directly in Databricks notebooks with:
```python
%pip install langgraph databricks-langchain
```

### Option 2: Model Serving (Production)

> **Note:** This section describes planned capabilities not yet implemented in the current workshop code.

Deploy as a Databricks Model Serving endpoint:
```python
from databricks.agents import deploy

deploy(
    model_name="catalog.schema.ai_data_analyst",
    model_version=1,
    scale_to_zero=True
)
```

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Databricks Agent Framework](https://docs.databricks.com/aws/en/generative-ai/agent-framework/)
- [Genie Conversation API](https://docs.databricks.com/aws/en/genie/conversation-api)
- [Vector Search](https://docs.databricks.com/aws/en/generative-ai/vector-search/)
