# Databricks AI/BI Workshop Demo Research Summary

**Research Date:** January 26, 2026
**Workshop Focus:** DBX x Compass AI Workshop - Building AI-Powered Data Analysts

---

## Research Documents Created

| File | Topic | Key Takeaway |
|------|-------|--------------|
| `01_genie_spaces_aibi.md` | Genie Spaces & AI/BI | Available on Free Edition; 25 tables max; excellent for non-technical demos |
| `02_databricks_agent_framework.md` | Mosaic AI Agent Framework & MCP | GA with native MCP support; Agent Bricks for no-code agent creation |
| `03_langgraph_databricks.md` | LangGraph + Databricks Integration | Full notebook patterns; GenieAgent + supervisor architecture |
| `04_free_tier_workshop_setup.md` | Free Tier & Workshop Setup | Community Edition retired Jan 2026; use Free Edition or Trial |
| `05_ai_data_analyst_patterns.md` | Enterprise AI Analyst Patterns | TAG architecture; 6% real-world vs 86% benchmark accuracy gap |
| `06_workshop_code_data_sharing.md` | Workshop Code & Data Sharing | GitHub+Repos recommended; DBC archives for non-technical; Delta Sharing for cross-org |

---

## Critical Findings for Your Demo

### 1. Environment Strategy (40-50 Participants)

**IMPORTANT:** Databricks Community Edition was **retired January 1, 2026**.

**Options:**
| Approach | Pros | Cons |
|----------|------|------|
| **Free Edition** (each participant) | No cost, includes Genie | No centralized control, self-registration required |
| **14-Day Trial** | $400 credits, full features | Requires work email for full access |
| **Enterprise Credits** | Managed environment | Requires Databricks coordination |

**Recommendation:** Coordinate with Databricks (Vincent/Felix) to provision workshop-specific environments or use CloudLabs for managed provisioning.

---

### 2. Two-Stage Demo Architecture

#### Stage 1: Non-Technical (Genie Spaces) - Business Persona

**What Genie Provides:**
- Conversational natural language to SQL
- "Thinking steps" transparency (great for trust-building)
- System prompts + custom SQL expressions
- Dashboard integration

**Demo Flow:**
1. Connect to sample dataset (TPC-H or custom Molson-style)
2. Define system prompt with business context
3. Create SQL expressions for key KPIs
4. Live Q&A with natural language queries
5. Show thinking steps to demystify AI

**Constraints:**
- 25 tables/views max per space
- 20 questions/minute via UI
- Pre-test benchmark questions before demo

#### Stage 2: Technical (LangGraph + Genie API) - Technical Persona

**Architecture:**
```
┌─────────────────┐
│   LangGraph     │
│   Supervisor    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌─────────────┐
│ Genie │ │VectorSearch │
│ Agent │ │   Agent     │
└───────┘ └─────────────┘
```

**Key Code Pattern:**
```python
from databricks_langchain.genie import GenieAgent
from langgraph_supervisor import create_supervisor

# Genie for structured data
genie_agent = GenieAgent(
    space_id="your-genie-space-id",
    name="SQLAnalyst",
    description="Queries structured business data"
)

# Supervisor orchestrates multiple agents
supervisor = create_supervisor(
    agents=[genie_agent, vector_search_agent],
    model="databricks-meta-llama-3-3-70b-instruct"
)
```

**Notebook Deployment:**
```python
import mlflow
mlflow.langchain.autolog()  # Required on serverless

# Deploy to Model Serving
from databricks.agents import deploy
deploy(model_fqn="catalog.schema.my_agent", uc_function_tools=["catalog.schema.*"])
```

---

### 3. Demo Dataset Recommendations

**Built-in Options:**
- `samples.nyctaxi.trips` - NYC taxi data (good for analytics demos)
- `samples.tpch.*` - TPC-H benchmark (classic BI queries)
- `samples.tpcds_sf1.*` - TPC-DS retail scenario

**For Molson-style Use Case:**
Consider creating a simplified CPG/beverage analytics dataset with:
- Sales transactions
- Inventory levels
- Regional performance
- Seasonal trends

---

### 4. Key Talking Points (Lessons Learned)

Based on research from production deployments:

1. **The Accuracy Gap:** Benchmarks show 86% accuracy, real-world is ~6%. The gap = missing business context, not LLM capability.

2. **Data Engineering Layer is Critical:** Speed and SQL complexity require pre-aggregated views, semantic layer, and well-documented schemas.

3. **Trust Through Transparency:** Genie's "thinking steps" are essential for business adoption - always show the reasoning.

4. **Start Small:** 5 or fewer well-documented tables outperforms 25 poorly-documented ones.

5. **ROI Timeline:** Set expectations for 12-24 month horizon; PoC is easy, production is 6+ months (you cut to 10 weeks).

---

### 5. Technical Requirements Checklist

**For Genie Spaces:**
- [ ] Unity Catalog enabled workspace
- [ ] Pro SQL Warehouse or Serverless
- [ ] Tables registered in UC with comments/descriptions
- [ ] System prompt drafted
- [ ] Custom SQL expressions for key metrics

**For LangGraph Notebooks:**
- [ ] Python packages: `langgraph`, `databricks-langchain`, `mlflow>=3.1`
- [ ] Genie Space ID for API access
- [ ] Vector Search index (if using RAG)
- [ ] MLflow experiment for tracing

**Workshop Materials:**
- [ ] Git repo with notebooks
- [ ] Sample data uploaded to UC
- [ ] Step-by-step instructions document
- [ ] Fallback screenshots/recordings

---

### 6. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| WiFi issues | Have hotspot backup; pre-download notebooks |
| Genie rate limits | Space out demos; have pre-recorded backup |
| Compute quota | Test with 50 concurrent users beforehand |
| LLM hallucinations | Use well-tested questions; show "uncertain" handling |
| Time overrun | Have modular sections; cut technical deep-dive if needed |

---

## Next Steps

1. **Confirm with DBX (Vincent/Felix):** Environment provisioning approach
2. **Create Demo Dataset:** Anonymized Molson-style or use built-in samples
3. **Build Genie Space:** Configure with system prompts and SQL expressions
4. **Develop Notebooks:** LangGraph + Genie API integration
5. **Test End-to-End:** Simulate 50 concurrent users
6. **Prepare Fallbacks:** Screenshots, recordings, offline notebooks

---

## Quick Links to Research

- [Genie Spaces Deep Dive](./01_genie_spaces_aibi.md)
- [Agent Framework & MCP](./02_databricks_agent_framework.md)
- [LangGraph Integration](./03_langgraph_databricks.md)
- [Free Tier & Workshop Setup](./04_free_tier_workshop_setup.md)
- [AI Analyst Patterns](./05_ai_data_analyst_patterns.md)
