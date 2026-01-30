# AI Data Analyst Workshop

Workshop for building AI data analysts with Databricks Genie Spaces and LangGraph multi-agent orchestration. Demonstrates dirty vs clean data impact on AI, Genie + RAG routing, and multi-Genie report generation.

## Tech Stack
Python 3.10+, LangGraph, Databricks SDK, databricks-langchain, Vector Search, Pydantic, Pandas, Faker

## Commands
Install: `uv sync` | Test: `uv run pytest` | Run: `uv run python scripts/test_genie.py`
Generate data: `uv run python dataset_generators/generate_velocity_motors.py`
Deploy: `databricks bundle deploy -t dev`

## Environment
Copy `.env.example` to `.env`, set DATABRICKS_HOST, DATABRICKS_TOKEN, GENIE_SPACE_ID
Mock mode: `MOCK_MODE=true` for testing without Databricks

## Key Patterns
- All agents accept Config, use mock_mode for testing
- Result classes: success bool first, error Optional[str] last, formatting methods
- Lazy-load SDK clients with @property pattern
- Use `uv run` for all Python commands

## Project Structure
src/agents/ - GenieDataAgent, RAGAgent, MultiGenieOrchestrator, Supervisor, Synthesizer, Planner
src/config.py - Configuration (from_env, from_databricks_secrets, from_notebook_params)
dataset_generators/ - velocity_motors, healthcare, finance_banking, star_schema, super_table
notebooks/ - 00a_setup_data, 00b_setup_rag, 00c_setup_genie, 01_agent_basics, 02_multi_genie_orchestration, 03_build_your_agent
scripts/ - test_genie.py, evaluate_genie.py, benchmark.py, setup_vector_search.py

## Critical Files
src/config.py - Config dataclass, get_config singleton
src/agents/genie_agent.py - GenieDataAgent, GenieResult
src/agents/supervisor.py - create_supervisor_agent, AgentState
pyproject.toml - Dependencies

## Workshop Parts
Part 1: Genie UI dirty vs clean data demo
Part 2: Genie + RAG multi-agent with LangGraph
Part 3: Multi-Genie orchestration + report generation

## Documentation
Index: `docs/KNOWLEDGE_BASE.md`
