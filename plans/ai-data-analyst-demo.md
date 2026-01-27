# AI Data Analyst Demo: Compass x Databricks

## Overview

Build a demo showcasing Databricks Genie Space capabilities with multi-agent orchestration using LangGraph. The supervisor agent routes queries to specialized subagents including Genie for structured data analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface                            │
│              (Databricks Notebook / Streamlit)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Supervisor Agent                           │
│         (LangGraph StateGraph + ChatDatabricks)              │
│                                                              │
│   Routes queries based on intent:                            │
│   • Structured data questions → Genie Agent                  │
│   • Document/policy questions → RAG Agent                    │
│   • Complex analysis → Multi-step orchestration              │
└────────┬────────────────────────────┬───────────────────────┘
         │                            │
         ▼                            ▼
┌─────────────────────┐    ┌─────────────────────┐
│    Genie Agent      │    │     RAG Agent       │
│                     │    │                     │
│ • NL to SQL         │    │ • Vector Search     │
│ • Data insights     │    │ • Document QA       │
│ • Aggregations      │    │ • Policy lookup     │
└─────────────────────┘    └─────────────────────┘
```

## Project Structure

```
research_dbx_demo/
├── databricks.yml              # Databricks Asset Bundle config
├── pyproject.toml              # Python dependencies (uv)
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── genie_agent.py      # Genie Space wrapper
│   │   ├── rag_agent.py        # RAG/Vector Search agent
│   │   └── supervisor.py       # LangGraph supervisor orchestration
│   ├── tools/
│   │   ├── __init__.py
│   │   └── data_tools.py       # Custom tools for analysis
│   └── config.py               # Configuration management
├── notebooks/
│   └── demo.ipynb              # Main demo notebook for Databricks
├── plans/
│   └── ai-data-analyst-demo.md # This plan
└── docs/
    └── setup.md                # Setup instructions
```

## Implementation Tasks

### Phase 1: Core Infrastructure

1. **Project Setup**
   - Create `pyproject.toml` with dependencies
   - Create `databricks.yml` for Asset Bundle deployment
   - Set up configuration management

2. **Genie Agent Module** (`src/agents/genie_agent.py`)
   - Wrapper class for Databricks Genie API
   - Methods: `start_conversation`, `send_message`, `get_results`
   - Handle async polling for query completion
   - Parse and format query results

3. **RAG Agent Module** (`src/agents/rag_agent.py`)
   - Integration with Databricks Vector Search
   - Document retrieval and response generation
   - (Placeholder for demo - can be expanded)

### Phase 2: LangGraph Orchestration

4. **Supervisor Agent** (`src/agents/supervisor.py`)
   - Define `AgentState` TypedDict
   - Create supervisor with routing logic
   - Build StateGraph with conditional edges
   - Implement tool-calling pattern for subagents

5. **State Management**
   - Message history tracking
   - Conversation context preservation
   - Error handling and recovery

### Phase 3: Demo Interface

6. **Demo Notebook** (`notebooks/demo.ipynb`)
   - Setup cells (install deps, configure)
   - Interactive demo cells
   - Example queries showcasing:
     - Simple data queries via Genie
     - Complex multi-step analysis
     - Agent routing demonstrations

## Key Dependencies

```
databricks-sdk>=0.40.0
databricks-langchain>=0.1.0
databricks-agents>=0.1.0
langgraph>=0.2.0
langchain-core>=0.3.0
mlflow>=2.17.0
pydantic>=2.0.0
```

## Configuration Requirements

Environment variables (or Databricks secrets):
- `DATABRICKS_HOST` - Workspace URL
- `DATABRICKS_TOKEN` - PAT token (for local dev)
- `GENIE_SPACE_ID` - Target Genie Space ID
- `VECTOR_SEARCH_ENDPOINT` - VS endpoint (optional)
- `VECTOR_SEARCH_INDEX` - VS index name (optional)

## Demo Flow

1. **Introduction**: Show Genie Space in Databricks UI
2. **Basic Query**: "What are our top 10 products by revenue?"
3. **Follow-up**: "Break that down by region"
4. **Complex Analysis**: Multi-step query requiring agent orchestration
5. **Technical Deep-dive**: Show the LangGraph code and supervisor routing

## Pre-Mortem Checklist

### Potential Issues

- [ ] **Genie Space not configured**: Need valid Space ID with data
- [ ] **Authentication**: Token scopes must include Genie API access
- [ ] **Rate limiting**: Genie API may have request limits
- [ ] **Async polling**: Queries take time; need proper wait logic
- [ ] **Error handling**: Genie can fail on ambiguous queries

### Mitigations

- [ ] Include mock/fallback responses for demo stability
- [ ] Add retry logic with exponential backoff
- [ ] Validate Genie Space access before demo
- [ ] Prepare canned queries known to work

## Success Criteria

1. Successfully route queries to appropriate subagent
2. Genie returns valid SQL results for data questions
3. Supervisor provides coherent final response
4. Demo runs smoothly in Databricks notebook
5. Code is portable via `databricks bundle deploy`

## Next Steps After Implementation

1. Test with real Genie Space and data
2. Add MLflow tracking for agent responses
3. Deploy as Databricks Agent for production use
4. Add streaming response support
