# AI Data Analyst Workshop

**By Compass x Databricks**

Build AI-powered data analysts using Databricks Genie Spaces and LangGraph.

## Workshop Overview

This hands-on workshop teaches you to build AI data analysts that can:

- Answer business questions in natural language
- Query structured data via Genie Spaces
- Search documents via RAG (Retrieval-Augmented Generation)
- Orchestrate multiple AI agents for complex workflows

**Duration:** 30 min presentation + 2.5 hour hands-on demo

**Audience:** Non-technical, semi-technical, and technical participants

## Workshop Structure

| Part       | Focus                                                               | Audience  |
| ---------- | ------------------------------------------------------------------- | --------- |
| **Part 1** | Genie Spaces UI - What works, what breaks, why data quality matters | Everyone  |
| **Part 2** | Genie as a LangGraph node - Building multi-agent systems            | Technical |
| **Part 3** | Multi-Genie + Report Generator - Advanced orchestration             | Technical |

## Quick Start

### Prerequisites

- Databricks account ([Free Edition](https://www.databricks.com/learn/free-edition) works)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for Python environment management

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/ai-data-analyst-workshop.git
cd ai-data-analyst-workshop

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your Databricks credentials
```

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

### Run Demo Notebook

1. Upload `notebooks/` to your Databricks workspace
2. Or import the DBC archive: `workshop-materials.dbc`
3. Follow along with Part 1, 2, or 3

## Repository Structure

```
ai-data-analyst-workshop/
├── notebooks/              # Demo notebooks for each workshop part
├── src/                    # Agent code (Genie, RAG, Supervisor)
├── dataset_generators/     # Generate sample data (dirty vs clean)
├── infra/                  # Genie Space Infrastructure-as-Code
├── scripts/                # Setup and deployment scripts
├── data/documents/         # Sample documents for RAG demo
├── docs/                   # Workshop documentation
└── databricks.yml          # Databricks Asset Bundle config
```

## Documentation

- [Setup Guide](docs/SETUP.md) - Environment setup for participants
- [Architecture](docs/ARCHITECTURE.md) - How the agents work
- [Genie Best Practices](docs/GENIE_BEST_PRACTICES.md) - Data quality and Knowledge Store

## Key Concepts

### Why Data Quality Matters

In Part 1, we demonstrate:

- **Dirty data** (139 columns, inconsistent naming) → Genie gets confused
- **Clean data** (star schema, 6 tables) → Same questions work perfectly

The AI didn't change. The data did.

### Multi-Agent Architecture

```
User Question
      │
      ▼
┌─────────────────────┐
│  Supervisor Agent   │  Routes based on intent
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌────────┐
│ Genie  │  │  RAG   │
│ (Data) │  │ (Docs) │
└────────┘  └────────┘
```

## Resources

- [Databricks Genie Spaces Documentation](https://docs.databricks.com/aws/en/genie/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Databricks Free Edition](https://www.databricks.com/learn/free-edition)
