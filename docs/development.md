# Development Guide

Complete guide for developing and testing the AI Data Analyst Workshop codebase.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Project Structure](#project-structure)
3. [Running the Code](#running-the-code)
4. [Testing](#testing)
5. [Dataset Generation](#dataset-generation)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Databricks account (Free Edition or higher)

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_ORG/ai-data-analyst-workshop.git
cd ai-data-analyst-workshop

# Install dependencies with uv
uv sync

# Install dev dependencies
uv sync --group dev
```

### Environment Configuration

```bash
# Copy template
cp .env.example .env
```

**Required variables:**
```env
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-pat-token
GENIE_SPACE_ID=your-space-id
```

**Optional variables:**
```env
WAREHOUSE_ID=your-warehouse-id
MODEL_ENDPOINT=databricks-meta-llama-3-3-70b-instruct
MOCK_MODE=false
VECTOR_SEARCH_ENDPOINT=rag-demo-endpoint
VECTOR_SEARCH_INDEX=workspace.rag_demo.document_index
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
```

### Getting Databricks Credentials

1. **Personal Access Token:**
   - Databricks UI > Settings > Developer > Access tokens > Generate new token

2. **Genie Space ID:**
   - Navigate to Genie > Open a Space
   - Copy ID from URL: `/genie/spaces/[SPACE_ID]/conversations`

3. **Warehouse ID:**
   - SQL Warehouses > Select warehouse > Copy ID from URL

---

## Project Structure

```
ai-data-analyst-workshop/
├── src/                          # Main source code
│   ├── agents/                   # Agent implementations
│   │   ├── genie_agent.py        # GenieDataAgent for SQL queries
│   │   ├── rag_agent.py          # RAGAgent for document search
│   │   ├── multi_genie_orchestrator.py  # Multi-space orchestration
│   │   ├── planner_agent.py      # Query decomposition
│   │   ├── synthesizer_agent.py  # Cross-domain synthesis
│   │   ├── report_writer.py      # Report generation
│   │   └── supervisor.py         # LangGraph supervisor
│   ├── config.py                 # Configuration management
│   ├── tools/                    # LangChain tools
│   ├── utils/                    # Utility functions
│   ├── benchmark/                # Benchmarking framework
│   ├── evaluation/               # Genie evaluation tools
│   ├── demo/                     # Demo utilities
│   └── workshop/                 # Workshop helpers
├── dataset_generators/           # Data generation
│   ├── velocity_motors/          # Automotive domain
│   ├── healthcare/               # Healthcare domain
│   ├── finance_banking/          # Finance domain
│   ├── star_schema_generator.py  # Clean data generator
│   └── super_table_generator.py  # Dirty data generator
├── notebooks/                    # Databricks notebooks
│   ├── 00a_setup_data.ipynb  # Data setup
│   ├── 01_agent_basics.ipynb                # Basic demo
│   ├── advanced_01_agent_basics.ipynb       # Multi-Genie demo
│   └── 03_build_your_agent.ipynb # Agent Builder workshop
├── scripts/                      # Utility scripts
│   ├── setup_vector_search.py    # Vector Search setup
│   ├── evaluate_genie.py         # Evaluation runner
│   ├── benchmark.py              # Benchmark runner
│   └── upload_to_azure.py        # Azure blob upload
├── tests/                        # Test suite
├── infra/                        # Genie Space IaC
├── config/                       # Dataset schemas
└── docs/                         # Documentation
```

---

## Running the Code

### Mock Mode (No Databricks)

```bash
# Test without Databricks connection
MOCK_MODE=true uv run python -c "
from src.config import Config
from src.agents.genie_agent import GenieDataAgent

config = Config.from_env()
agent = GenieDataAgent(config)
result = agent.query('What are top products?')
print(result.to_markdown_table())
"
```

### Real Mode

```bash
# With Databricks connection
uv run python scripts/test_genie.py
```

### Running Notebooks Locally

```bash
# Start Jupyter
uv run jupyter notebook

# Or in Databricks
# Upload notebooks/ directory to workspace
```

### Using the Supervisor Agent

```python
from src.config import Config
from src.agents.supervisor import create_supervisor_agent

config = Config.from_env()
supervisor = create_supervisor_agent(config)

# Query data
response = supervisor.invoke({
    "messages": [{"role": "user", "content": "What was Q4 revenue?"}]
})
print(response["messages"][-1].content)
```

### Using Multi-Genie Orchestrator

```python
from src.config import Config
from src.agents.multi_genie_orchestrator import MultiGenieOrchestrator, GenieSpaceConfig

config = Config.from_env()
spaces = [
    GenieSpaceConfig(space_id="abc123", name="Sales", domain="revenue, orders"),
    GenieSpaceConfig(space_id="def456", name="CRM", domain="customers, segments"),
]

orchestrator = MultiGenieOrchestrator(spaces, config)
result = orchestrator.query_spaces("Compare sales and customer trends")
print(result.to_combined_markdown())
```

---

## Testing

### Run All Tests

```bash
uv run pytest
```

### Run Specific Tests

```bash
# By file
uv run pytest tests/test_evaluation.py

# By pattern
uv run pytest -k "test_cache"

# With verbose output
uv run pytest -v
```

### Test Coverage

```bash
uv run pytest --cov=src --cov-report=html
```

### Test Scripts (Integration Tests)

```bash
# Test Genie agent
uv run python scripts/test_genie.py

# Test multi-Genie orchestration
uv run python scripts/test_multi_genie.py

# Test planner
uv run python scripts/test_planner.py

# Test synthesizer
uv run python scripts/test_synthesizer.py
```

---

## Dataset Generation

### Generate All Datasets

```bash
uv run python dataset_generators/generate_all.py
```

### Generate Specific Datasets

```bash
# Velocity Motors (automotive dealership)
uv run python dataset_generators/generate_velocity_motors.py

# Star Schema (clean dimensional model)
uv run python dataset_generators/star_schema_generator.py

# Super Table (dirty anti-pattern demo)
uv run python dataset_generators/super_table_generator.py

# Healthcare
uv run python dataset_generators/generate_healthcare.py

# Finance/Banking
uv run python dataset_generators/generate_finance.py
```

### Dataset Options

```bash
# With parameters
uv run python dataset_generators/generate_velocity_motors.py \
    --scale 1.0 \
    --output-dir dataset_generators/data/velocity_motors
```

### Upload to Databricks

Use the setup notebook:
1. Open `notebooks/00a_setup_data.ipynb`
2. Configure widgets (dataset, catalog)
3. Run all cells

Or manually:
```bash
databricks fs cp dataset_generators/data/ dbfs:/workshop/data/ --recursive
```

---

## Deployment

### Databricks Asset Bundles

```bash
# Deploy to dev
databricks bundle deploy -t dev

# Deploy to prod
databricks bundle deploy -t prod

# With variables
databricks bundle deploy -t dev \
    --var genie_space_id=YOUR_ID \
    --var warehouse_id=YOUR_WAREHOUSE
```

### Deploy Genie Spaces (IaC)

```bash
uv run python scripts/deploy_velocity_motors_spaces.py
```

### Vector Search Setup

```bash
uv run python scripts/setup_vector_search.py
```

---

## Troubleshooting

### Import Errors

```bash
# Verify installation
uv pip list | grep databricks

# Reinstall
uv sync --refresh
```

### Authentication Errors

- Verify `DATABRICKS_HOST` includes `https://`
- Check token expiration
- Ensure token has correct scopes

### Genie Rate Limits

- UI: 20 questions/minute
- API: 5 questions/minute
- Solution: Add delays or use caching

### Mock Mode Not Working

```bash
# Verify environment
echo $MOCK_MODE

# Force mock mode
MOCK_MODE=true uv run python your_script.py
```

### Cache Issues

```python
# Clear config cache
from src.config import clear_config_cache
clear_config_cache()
```

### Notebook Import Errors

In Databricks notebooks:
```python
# Install dependencies
%pip install databricks-langchain langgraph

# Restart Python
dbutils.library.restartPython()
```

---

## Code Quality

### Linting (if configured)

```bash
uv run ruff check src/
uv run ruff format src/
```

### Type Checking (if configured)

```bash
uv run mypy src/
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/config.py` | Central configuration management |
| `src/agents/__init__.py` | Agent exports |
| `pyproject.toml` | Project dependencies |
| `.env.example` | Environment variable template |
| `databricks.yml` | Asset Bundle configuration |
