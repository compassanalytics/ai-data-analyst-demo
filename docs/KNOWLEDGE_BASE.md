# AI Data Analyst Workshop - Knowledge Base

Quick index to detailed documentation.

## Architecture
Multi-agent system: Supervisor routes to Genie (SQL) and RAG (docs) agents via LangGraph.
`docs/ARCHITECTURE.md`

## Development
Setup, testing, dataset generation, and deployment workflows with uv.
`docs/development.md`

## API Reference
Agent classes (GenieDataAgent, RAGAgent, MultiGenieOrchestrator), Config, Result dataclasses.
`docs/api-reference.md`

## Genie Best Practices
Data quality patterns, Knowledge Store configuration, dirty vs clean data examples.
`docs/GENIE_BEST_PRACTICES.md`

## Agent Patterns
Implementation patterns: mock mode, lazy-loading, result classes, agent composition.
`docs/AGENT_PATTERNS.md`

## Setup Guide
Participant setup: Databricks account, credentials, data upload, Genie Space creation.
`docs/SETUP.md`

## Troubleshooting
Common errors: auth, rate limits, Vector Search, imports. Debug tips and solutions.
`docs/troubleshooting.md`

## Dataset Generators
Three domains: velocity_motors (automotive), healthcare, finance_banking. Plus star_schema/super_table demos.
`dataset_generators/README.md`

## Workshop Parts

| Part | Focus | Notebook |
|------|-------|----------|
| 1 | Genie UI - dirty vs clean data | `notebooks/demo.ipynb` |
| 2 | Multi-agent with RAG | `notebooks/advanced_demo.ipynb` |
| 3 | Build your own agent | `notebooks/03_build_your_agent.ipynb` |

## Research Documents
`docs/research/00_RESEARCH_SUMMARY.md` - Index to Genie Spaces, Agent Framework, LangGraph research.

## Key Source Files

| File | Purpose |
|------|---------|
| `src/config.py` | Configuration management |
| `src/agents/genie_agent.py` | Genie data queries |
| `src/agents/rag_agent.py` | Document retrieval |
| `src/agents/multi_genie_orchestrator.py` | Multi-space orchestration |
| `src/agents/supervisor.py` | LangGraph supervisor |
| `src/agents/synthesizer_agent.py` | Cross-domain synthesis |
| `src/agents/planner_agent.py` | Query decomposition |

## External Resources

- [Databricks Genie Docs](https://docs.databricks.com/aws/en/genie/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [Databricks Agent Framework](https://docs.databricks.com/aws/en/generative-ai/agent-framework/)
