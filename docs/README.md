# Workshop Documentation

This folder contains documentation for the AI Data Analyst Workshop.

## Documents

| Document | Description |
|----------|-------------|
| [SETUP.md](SETUP.md) | Participant setup guide for Databricks Free Edition |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture of the multi-agent system |
| [GENIE_BEST_PRACTICES.md](GENIE_BEST_PRACTICES.md) | Data quality and Knowledge Store configuration |

## Workshop Parts

### Part 1: Genie Spaces UI (Non-Technical)
Demonstrates why data quality matters more than AI capabilities:
- Dirty data with 139 columns → AI gets confused
- Clean star schema → Same questions work perfectly
- Knowledge Store configuration for business context

### Part 2: Genie + RAG Multi-Agent (Technical)
Build a LangGraph supervisor that routes between:
- Genie Agent for structured data queries
- RAG Agent for document search
- Extensible architecture for adding more tools

### Part 3: Multi-Genie Report Generator (Advanced)
Advanced orchestration with:
- Multiple Genie Spaces (Sales, CRM, Operations)
- Automated report generation workflow
- Customizable agent building

## Additional Resources

- [Databricks Genie Documentation](https://docs.databricks.com/aws/en/genie/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Databricks Agent Framework](https://docs.databricks.com/aws/en/generative-ai/agent-framework/)
