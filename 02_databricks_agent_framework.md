# Databricks Agent Framework Research

**Research Date**: January 26, 2026
**Purpose**: Workshop demo preparation - Databricks agentic capabilities and MCP integration

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Mosaic AI Agent Framework](#mosaic-ai-agent-framework)
3. [Agent Bricks Platform](#agent-bricks-platform)
4. [MCP (Model Context Protocol) on Databricks](#mcp-model-context-protocol-on-databricks)
5. [Unity Catalog Integration](#unity-catalog-integration)
6. [Function Calling and Tool Use](#function-calling-and-tool-use)
7. [Agent Evaluation](#agent-evaluation)
8. [Agent Deployment and Serving](#agent-deployment-and-serving)
9. [AI Gateway and Guardrails](#ai-gateway-and-guardrails)
10. [Multi-Agent Architecture](#multi-agent-architecture)
11. [Code Examples](#code-examples)
12. [Sources](#sources)

---

## Executive Summary

Databricks has evolved into a comprehensive AI agent platform with the following key capabilities as of January 2026:

- **Mosaic AI Agent Framework** (GA): Production-grade framework for building, evaluating, and deploying AI agents
- **Agent Bricks** (Beta, launched June 2025): Automated agent creation platform with pre-built templates
- **MCP Integration**: Native support for Model Context Protocol with managed servers and custom hosting
- **MLflow 3**: Redesigned for GenAI with agent observability, prompt versioning, and cross-platform monitoring
- **Mosaic AI Gateway** (GA): Unified entry point with guardrails, governance, and multi-provider support
- **Multi-Agent Supervisor**: Orchestration system for coordinating multiple specialized agents

---

## Mosaic AI Agent Framework

### Overview

The Mosaic AI Agent Framework is now generally available and provides an end-to-end solution for building production-quality AI agents. It integrates tightly with Unity Catalog for governance and MLflow for tracking and evaluation.

### Core Capabilities

| Capability            | Description                                                           |
| --------------------- | --------------------------------------------------------------------- |
| **Agent Development** | Build agents using Python, LangChain, LangGraph, or custom frameworks |
| **Tool Integration**  | Connect to Unity Catalog functions, MCP servers, Vector Search        |
| **Governance**        | End-to-end governance through Unity Catalog                           |
| **Evaluation**        | Built-in LLM judges and human feedback integration                    |
| **Deployment**        | One-click deployment to Model Serving endpoints                       |
| **Observability**     | Real-time tracing with MLflow 3                                       |

### Supported Agent Authoring Libraries

- **LangGraph/LangChain**: Native integration via `databricks-langchain` package
- **LlamaIndex**: Supported for RAG-based agents
- **AutoGen**: Tool-calling agent support with Databricks tools
- **DSPy**: Single-turn tool-calling agents
- **Custom Python**: Full flexibility with MLflow ResponsesAgent interface

### Key Components

```
Mosaic AI Agent Framework
├── Agent Development
│   ├── AI Playground (prototyping)
│   ├── Code-based authoring
│   └── Agent Bricks (no-code/low-code)
├── Tools & Integration
│   ├── Unity Catalog Functions
│   ├── MCP Servers (managed & custom)
│   ├── Vector Search
│   └── Genie Spaces
├── Evaluation
│   ├── LLM Judges
│   ├── Human Feedback (Review App)
│   └── Custom Metrics
├── Deployment
│   ├── Model Serving
│   ├── Auto-scaling
│   └── Authentication
└── Governance
    ├── Unity Catalog
    ├── AI Gateway
    └── Guardrails
```

---

## Agent Bricks Platform

### Introduction

Agent Bricks was announced at Data + AI Summit 2025 (June 11, 2025) as an automated approach to creating high-performing AI agents. It uses Mosaic AI Research techniques including TAO (Task-Aware Optimization) and ALHF (Automated Learning from Human Feedback).

### Agent Types

#### 1. Information Extraction

Extract structured data from unstructured documents:

- PDFs, emails, scanned forms
- No labeled training data required
- Outputs to structured tables

**Customer Example**: AstraZeneca parsed 400,000+ clinical trial documents and extracted structured data in under 60 minutes without writing code.

#### 2. Knowledge Assistant

Reliable Q&A over enterprise documents:

- Automatic content indexing
- Quality evaluation built-in
- Fast, accurate answers grounded in enterprise data
- Ideal for manuals, policies, technical guides

#### 3. Multi-Agent Supervisor

Orchestration system for complex tasks:

- Coordinates Genie Spaces, agent endpoints, UC functions, MCP servers
- Advanced AI orchestration patterns
- Task delegation and result synthesis

### Key Features

- **Declarative Configuration**: Build agents using natural language descriptions
- **Auto-Optimization**: Automatically generates synthetic data and benchmarks
- **Built-in Evaluation**: MLflow integration for quality assessment
- **MCP Integration**: Native support for MCP servers in agent workflows

---

## MCP (Model Context Protocol) on Databricks

### Overview

MCP is an open-source standard that connects AI agents to tools, resources, prompts, and contextual information. Databricks provides comprehensive MCP support with both managed servers and custom hosting options.

### MCP Server Types on Databricks

#### 1. Managed MCP Servers

Databricks provides ready-to-use managed servers:

| Server Type                 | Purpose                         | URL Pattern              |
| --------------------------- | ------------------------------- | ------------------------ |
| **Unity Catalog Functions** | Execute UC functions as tools   | `uc-functions` endpoint  |
| **Vector Search**           | Search unstructured data        | `vector-search` endpoint |
| **Genie Spaces**            | Query structured data via Genie | `genie` endpoint         |

**Key Benefits**:

- Unity Catalog permissions enforced automatically
- No infrastructure management
- Secure by default with authentication

#### 2. Custom MCP Servers (Databricks Apps)

Host your own MCP servers as Databricks Apps:

**Requirements**:

- HTTP-compatible transport (streamable HTTP)
- App name prefixed with `mcp-`
- OAuth authentication for M2M communication

**Deployment Steps**:

1. Authenticate using `databricks auth login`
2. Create `requirements.txt` with dependencies
3. Configure `app.yaml` with server command
4. Deploy using Databricks CLI
5. Access at `https://<app-url>/mcp`

#### 3. External MCP Servers

Connect to third-party MCP servers through the MCP Marketplace (Public Preview).

### MCP Catalog (Beta)

New in 2025: The MCP Servers tab in Databricks provides:

- Discovery and governance of all MCP servers
- Built on Unity Catalog for security
- Access control consistent with enterprise standards

### databricks-mcp Python Library

The `databricks-mcp` library simplifies MCP authentication:

```python
# Installation
pip install databricks-mcp

# Key classes
from databricks_mcp import DatabricksMCPClient, DatabricksOAuthClientProvider
```

**Authentication Methods**:

- Databricks CLI profile (development)
- Service principal (production M2M)
- On-behalf-of-user (runtime user context)

---

## Unity Catalog Integration

### Governance Model

Unity Catalog provides end-to-end governance for AI agents:

| Feature                   | Description                            |
| ------------------------- | -------------------------------------- |
| **Function Registration** | Register Python/SQL functions as tools |
| **Access Control**        | Per-column ACLs, row-level filters     |
| **Audit Logging**         | Complete audit trail of data access    |
| **Credential Management** | Scoped, time-bound credentials         |
| **Tool Discovery**        | Centralized tool catalog               |

### Creating UC Functions as Tools

Requirements for Python functions:

- **Type hints**: All arguments and return values must have type hints
- **Docstrings**: Google-style docstrings for LLM understanding
- **No variable arguments**: `*args` and `**kwargs` not supported

### Execution Modes

| Mode                     | Description                                  | Use Case              |
| ------------------------ | -------------------------------------------- | --------------------- |
| **Serverless** (default) | Remote execution on Spark Connect serverless | Production            |
| **Local**                | Local subprocess execution                   | Development/debugging |

### Built-in AI Tools

Databricks provides built-in tools in Unity Catalog:

- `system.ai.python_exec`: Sandboxed Python code execution
- External connections for API integrations
- AI functions for common operations

---

## Function Calling and Tool Use

### Tool Types

1. **Unity Catalog Functions**
   - SQL UDFs
   - Python UDFs (with type hints)
   - Pre-built system functions

2. **Vector Search Retrievers**
   - Unstructured data search
   - Automatic source citation

3. **MCP Tools**
   - Managed Databricks MCP servers
   - Custom MCP servers
   - External MCP servers (marketplace)

4. **Function Definitions**
   - Custom function schemas
   - Direct LLM tool definitions

### AI Playground Tool Options

Maximum 20 tools per agent:

- UC Function selection
- Function Definition (custom)
- Vector Search indexes
- MCP servers (managed and external)

### UCFunctionToolkit

```python
from databricks.agent_framework.tools import UCFunctionToolkit

# Initialize toolkit with UC function names
UC_TOOL_NAMES = ["system.ai.python_exec", "my_catalog.schema.my_function"]
uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)

# Get tool specifications
tools = uc_toolkit.tools
```

### LangChain Integration

```python
from databricks_langchain import UCFunctionToolkit

# Create toolkit for LangChain agents
toolkit = UCFunctionToolkit(function_names=["my_catalog.schema.keyword_extractor"])
tools = toolkit.get_tools()
```

---

## Agent Evaluation

### Mosaic AI Agent Evaluation

Comprehensive evaluation framework integrated with MLflow:

#### Built-in LLM Judges

| Judge                 | Purpose                                           |
| --------------------- | ------------------------------------------------- |
| `relevance_to_query`  | Check if response answers the query               |
| `groundedness`        | Verify response is grounded in provided context   |
| `chunk_relevance`     | Assess retrieved document relevance               |
| `safety`              | Detect toxic or harmful content                   |
| `guideline_adherence` | Verify custom guideline compliance                |
| `context_sufficiency` | Check if context was sufficient (requires labels) |
| `correctness`         | Verify factual accuracy (requires labels)         |

#### Custom Evaluation

```python
import mlflow
from mlflow.genai.scorers import RelevanceToQuery, Safety

eval_dataset = [
    {
        "inputs": {"messages": [{"role": "user", "content": "What is an LLM?"}]},
        "expected_response": None,
    }
]

eval_results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=lambda messages: agent.predict({"messages": messages}),
    scorers=[RelevanceToQuery(), Safety()]
)
```

#### Advanced Evaluation Configuration

```python
guidelines = {
    'pricing': ["The agent should never provide pricing information."]
}

eval_results = mlflow.evaluate(
    model=lambda inputs: agent.predict(inputs),
    data=spark.table("evaluation_table"),
    model_type="databricks-agent",
    evaluator_config={
        "databricks-agent": {
            "global_guidelines": guidelines,
            "metrics": [
                "chunk_relevance",
                "guideline_adherence",
                "safety",
            ],
        },
    },
)
```

### Review App

The Agent Evaluation Review App enables:

- Domain expert assessment and labeling
- Custom criteria definition
- Structured feedback collection
- No spreadsheets or custom tools needed

### MLflow 3 Evaluation Features

- Evaluation datasets with versioning and lineage
- Integration with Unity Catalog
- Conversion of production traces to evaluation records
- Continuous improvement cycle with human feedback

---

## Agent Deployment and Serving

### Deployment Methods

#### 1. Agent Framework deploy() API

```python
from databricks.agents import deploy

# Deploy agent to Model Serving
deployment = deploy(
    model_uri="models:/my_agent/1",
    endpoint_name="my-agent-endpoint"
)
```

**What deploy() does**:

- Creates Model Serving endpoint with auto-scaling
- Provisions secure authentication
- Enables MLflow tracing and monitoring
- Integrates with Review App

#### 2. Model Serving Endpoints

**Supported Model Types**:

- Custom models (MLflow format)
- Foundation models (Databricks-hosted)
- External models (via AI Gateway)

**Serving Features**:

- Serverless, auto-scaling architecture
- Scale-to-zero capability
- Pay-per-token pricing for foundation models

### Deployment Strategies

| Strategy       | Description                                 |
| -------------- | ------------------------------------------- |
| **Canary**     | Gradual rollout to subset of traffic        |
| **Blue/Green** | Parallel deployments with instant switch    |
| **Shadow**     | Test new version against production traffic |

### Production Tracing

Agents deployed on Databricks automatically:

- Log traces to MLflow experiment
- Support real-time viewing
- Optional long-term storage in Delta tables
- Automated quality assessment via Production Monitoring

### Prerequisites

- MLflow 3.1.3+ for `deploy()` API
- `databricks-agents` SDK 1.1.0+ for external notebook deployment
- Serverless compute enabled in workspace

---

## AI Gateway and Guardrails

### Mosaic AI Gateway (GA)

Unified entry point for all AI services:

| Feature                    | Description                                  |
| -------------------------- | -------------------------------------------- |
| **Multi-Provider Support** | OpenAI, Anthropic, Databricks-hosted, custom |
| **Automatic Fallback**     | Switch between providers on failure          |
| **Rate Limiting**          | Control usage across teams                   |
| **Usage Logging**          | Detailed telemetry in Unity Catalog          |
| **Guardrails**             | Safety, PII, keyword, topic filtering        |

### Guardrail Types

#### 1. Safety Filtering

Filters harmful content:

- Hate speech
- Insults
- Sexual content
- Violence
- Misconduct

#### 2. PII Detection

```python
gateway_request_data = {
    "guardrails": {
        "input": {"pii": {"behavior": "BLOCK"}},
        "output": {"pii": {"behavior": "BLOCK"}},
    }
}
```

#### 3. Keyword Filters

Block specific topics or terms in requests/responses.

#### 4. Topic Filters

Keep applications focused on intended scope.

#### 5. Custom Guardrails

Bring your own guardrail logic for inputs and outputs.

### Security Framework

Databricks AI Security Framework (DASF) v2.0:

- Maps 62 technical security risks
- Covers 12 AI system components
- Addresses prompt injection and jailbreaks
- Prevents accidental data exposure

### Investment in Noma Security (June 2025)

Additional AI governance capabilities:

- Comprehensive AI asset visibility
- AI Bill of Materials (AIBOM)
- Early risk detection
- Compliance with ISO 42001

---

## Multi-Agent Architecture

### Design Patterns

#### 1. Supervisor Pattern

```
                    ┌─────────────────┐
                    │   Supervisor    │
                    │     Agent       │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Genie Space  │    │   Knowledge   │    │   Custom      │
│    Agent      │    │   Assistant   │    │   Agent       │
└───────────────┘    └───────────────┘    └───────────────┘
```

#### 2. Hierarchical Multi-Agent

```
              ┌─────────────────────────────┐
              │   Organization Orchestrator │
              │   (Supervisor of Supervisors)│
              └──────────────┬──────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Division A   │    │  Division B   │    │  Division C   │
│  Supervisor   │    │  Supervisor   │    │  Supervisor   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │ Workers │          │ Workers │          │ Workers │
   └─────────┘          └─────────┘          └─────────┘
```

### Agent Roles

| Role                         | Description                                                          |
| ---------------------------- | -------------------------------------------------------------------- |
| **Supervisor Agents**        | Strategic planning, dependency management, multi-stage orchestration |
| **Manager Agents**           | Team coordination, goal-oriented task management                     |
| **Worker/Specialist Agents** | Domain expertise, specific task execution                            |

### Multi-Agent Supervisor Configuration

The Multi-Agent Supervisor coordinates:

- Genie Spaces (structured data queries)
- Knowledge Assistant endpoints
- Unity Catalog functions
- MCP servers

**Capabilities**:

- Task delegation
- Context management
- Result synthesis
- Natural language feedback integration

---

## Code Examples

### Example 1: Basic Agent with UC Tools

```python
from databricks.agent_framework.tools import UCFunctionToolkit
from databricks_model_serving_client import DatabricksModelServingClient
import mlflow

# Enable tracing
mlflow.autogen.autolog(log_traces=True)

# Initialize tools
UC_TOOL_NAMES = ["system.ai.python_exec"]
uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)

# Custom tool definition
def weather_in_california_city(city: str) -> str:
    """Get the weather description of a city in California."""
    return f"The weather in {city} is sunny."

tools = [weather_in_california_city]
tools.extend(uc_toolkit.tools)

# LLM endpoint
LLM_ENDPOINT_NAME = "databricks-meta-llama-3-3-70b-instruct"
```

### Example 2: MCP Server Connection

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

# Managed MCP server
client = DatabricksMCPClient()

# Custom MCP server (Databricks App)
import os
workspace_client = WorkspaceClient(
    host="<DATABRICKS_WORKSPACE_URL>",
    client_id=os.getenv("DATABRICKS_CLIENT_ID"),
    client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
    auth_type="oauth-m2m",
)

CUSTOM_MCP_SERVER_URLS = [
    "https://<custom-mcp-app-url>/mcp"
]
```

### Example 3: LangChain Integration

```python
from databricks_langchain import UCFunctionToolkit, ChatDatabricks
from langchain_core.messages import HumanMessage

# Initialize LLM
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

# Initialize toolkit
toolkit = UCFunctionToolkit(
    function_names=["my_catalog.schema.keyword_extractor"]
)
tools = toolkit.get_tools()

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Invoke
response = llm_with_tools.invoke([
    HumanMessage(content="Extract keywords from: AI is transforming industries")
])
```

### Example 4: Agent Deployment

```python
from databricks.agents import deploy
import mlflow

# Log the agent
with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model=my_agent,
        registered_model_name="my_agent_model"
    )

# Deploy to serving endpoint
deployment = deploy(
    model_uri="models:/my_agent_model/1",
    endpoint_name="my-agent-endpoint"
)

print(f"Endpoint URL: {deployment.endpoint_url}")
```

### Example 5: PII Guardrails Configuration

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Update endpoint with guardrails
w.serving_endpoints.update_config(
    name="my-agent-endpoint",
    served_entities=[...],
    ai_gateway={
        "guardrails": {
            "input": {
                "pii": {"behavior": "BLOCK"},
                "safety": {"behavior": "BLOCK"}
            },
            "output": {
                "pii": {"behavior": "BLOCK"},
                "safety": {"behavior": "BLOCK"}
            }
        }
    }
)
```

---

## Sources

### Official Databricks Documentation

- [Model Context Protocol (MCP) on Databricks](https://docs.databricks.com/aws/en/generative-ai/mcp/)
- [Host custom MCP servers using Databricks apps](https://docs.databricks.com/aws/en/generative-ai/mcp/custom-mcp)
- [Use Databricks managed MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp)
- [Create AI agent tools using Unity Catalog functions](https://docs.databricks.com/aws/en/generative-ai/agent-framework/create-custom-tool)
- [Deploy an agent for generative AI applications](https://docs.databricks.com/aws/en/generative-ai/agent-framework/deploy-agent)
- [Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/)
- [Multi-Agent Supervisor](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [AI Gateway introduction](https://docs.databricks.com/aws/en/ai-gateway/)
- [Integrate LangChain with Databricks Unity Catalog tools](https://docs.databricks.com/aws/en/generative-ai/agent-framework/langchain-uc-integration)
- [Agent system design patterns](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns)

### Databricks Blog Posts

- [Mosaic AI Announcements at Data + AI Summit 2025](https://www.databricks.com/blog/mosaic-ai-announcements-data-ai-summit-2025)
- [Multi-Agent Supervisor Architecture: Orchestrating Enterprise AI at Scale](https://www.databricks.com/blog/multi-agent-supervisor-architecture-orchestrating-enterprise-ai-scale)
- [MLflow 3.0: Build, Evaluate, and Deploy Generative AI with Confidence](https://www.databricks.com/blog/mlflow-30-unified-ai-experimentation-observability-and-governance)
- [Accelerate AI Development with Databricks: Discover, Govern, and Build with MCP and Agent Bricks](https://www.databricks.com/blog/accelerate-ai-development-databricks-discover-govern-and-build-mcp-and-agent-bricks)
- [Announcing Advanced Security and Governance in Mosaic AI Gateway](https://www.databricks.com/blog/new-updates-mosaic-ai-gateway-bring-security-and-governance-genai-models)

### Summit Sessions

- [Building Tool-Calling Agents With Databricks Agent Framework and MCP - Data + AI Summit 2025](https://www.databricks.com/dataaisummit/session/building-tool-calling-agents-databricks-agent-framework-and-mcp)

### Product Pages

- [Mosaic AI Agent Framework](https://www.databricks.com/product/machine-learning/retrieval-augmented-generation)
- [Mosaic AI](https://www.databricks.com/product/artificial-intelligence)
- [Agent Bricks](https://www.databricks.com/product/artificial-intelligence/agent-bricks)
- [Mosaic AI Gateway](https://www.databricks.com/product/artificial-intelligence/ai-gateway)

### API Documentation

- [Databricks MCP Python API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_mcp.html)

### Community Resources

- [Building Custom MCP Servers on Databricks Apps: A Practical Guide](https://medium.com/@AI-on-Databricks/building-custom-mcp-servers-on-databricks-apps-a-practical-guide-48048480ce62)
- [Step-by-Step Guide to Building Custom MCP Server on Databricks](https://community.databricks.com/t5/technical-blog/step-by-step-guide-to-building-custom-mcp-server-on-databricks/ba-p/132995)
- [Building a Supply-Chain Copilot with OpenAI Agent SDK and Databricks MCP Servers](https://cookbook.openai.com/examples/mcp/databricks_mcp_cookbook)

---

## Confidence Assessment

**Overall Confidence**: High

The information in this document is sourced from:

- Official Databricks documentation (primary source)
- Databricks blog posts and announcements
- Product pages and API documentation
- Data + AI Summit 2025 content

**Caveats**:

- Agent Bricks is in Beta as of January 2026
- MCP Catalog is in Beta
- Some features may have cloud-specific availability (AWS, Azure, GCP)
- Pricing and quotas may vary by workspace configuration

---

## Recommendations for Workshop Demo

### Demo Flow Suggestion

1. **Intro**: Show AI Playground for rapid prototyping
2. **Tools**: Demonstrate UC function creation and tool binding
3. **MCP**: Connect to managed MCP servers (Vector Search, Genie)
4. **Evaluation**: Run agent evaluation with MLflow
5. **Deployment**: Deploy to serving endpoint
6. **Governance**: Configure AI Gateway guardrails

### Key Talking Points

- Unified governance through Unity Catalog
- MCP standardization for tool integration
- No-code agent creation with Agent Bricks
- Production observability with MLflow 3
- Enterprise-grade security with AI Gateway

### Workshop Prerequisites

```bash
pip install databricks-langchain mlflow>=3.1.0 databricks-agents>=1.0.0 databricks-mcp
```

### Feature Availability Summary

| Feature                   | Status | Notes                              |
| ------------------------- | ------ | ---------------------------------- |
| Mosaic AI Agent Framework | GA     | Production ready                   |
| Agent Bricks              | Beta   | Launched June 2025                 |
| MCP Managed Servers       | GA     | UC Functions, Vector Search, Genie |
| MCP Custom Servers        | GA     | Via Databricks Apps                |
| MCP Catalog               | Beta   | Discovery and governance           |
| MLflow 3                  | GA     | GenAI observability                |
| AI Gateway                | GA     | Guardrails and governance          |
| Multi-Agent Supervisor    | Beta   | Part of Agent Bricks               |
