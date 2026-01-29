# API Reference

Complete reference for agents, configurations, and utilities in the AI Data Analyst Workshop.

## Table of Contents

1. [Configuration](#configuration)
2. [GenieDataAgent](#geniedataagent)
3. [RAGAgent](#ragagent)
4. [MultiGenieOrchestrator](#multigenieorchestrator)
5. [PlannerAgent](#planneragent)
6. [SynthesizerAgent](#synthesizeragent)
7. [ReportWriter](#reportwriter)
8. [Supervisor](#supervisor)
9. [Result Classes](#result-classes)

---

## Configuration

### Config Class

Location: `src/config.py`

```python
from src.config import Config, get_config, clear_config_cache
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `databricks_host` | str | "" | Workspace URL |
| `databricks_token` | str | None | PAT token (local dev only) |
| `genie_space_id` | str | "" | Primary Genie Space ID |
| `warehouse_id` | str | "" | SQL Warehouse ID |
| `model_endpoint` | str | "databricks-meta-llama-3-3-70b-instruct" | LLM endpoint |
| `mock_mode` | bool | False | Enable mock responses |
| `vector_search_endpoint` | str | None | Vector Search endpoint |
| `vector_search_index` | str | None | Vector Search index |
| `embedding_endpoint` | str | "databricks-bge-large-en" | Embedding model |
| `genie_spaces_json` | str | None | JSON config for multiple spaces |
| `cache_enabled` | bool | True | Enable query caching |
| `cache_ttl_seconds` | int | 300 | Cache TTL (5 minutes) |
| `cache_max_size` | int | 1000 | Maximum cache entries |
| `demo_mode` | str | "normal" | Demo mode (normal/fast/live) |

#### Factory Methods

```python
# From environment variables
config = Config.from_env()

# From Databricks secrets
config = Config.from_databricks_secrets(scope="ai-data-analyst")

# From notebook widgets
config = Config.from_notebook_params({"genie_space_id": "abc123"})

# Singleton instance (auto-detects environment)
config = get_config()
```

#### Validation

```python
errors = config.validate()  # Returns list of error messages
is_valid = config.is_valid()  # Boolean
rag_errors = config.validate_rag()  # RAG-specific validation
has_rag = config.is_rag_configured()  # Check RAG setup
```

---

## GenieDataAgent

Location: `src/agents/genie_agent.py`

Wraps Databricks Genie Conversation API for structured data queries.

```python
from src.agents.genie_agent import GenieDataAgent, GenieResult, QueryStatus
```

### Constructor

```python
agent = GenieDataAgent(config: Config)
```

### Methods

#### query()

```python
def query(
    self,
    question: str,
    timeout_seconds: Optional[int] = None,
    retry_count: int = 2,
    retry_delay: float = 1.0,
) -> GenieResult
```

**Parameters:**
- `question`: Natural language query
- `timeout_seconds`: Query timeout (default: 120)
- `retry_count`: Number of retries on failure
- `retry_delay`: Delay between retries (seconds)

**Returns:** `GenieResult`

**Example:**
```python
result = agent.query("What were total sales last month?")
if result.success:
    print(result.to_markdown_table())
else:
    print(f"Error: {result.error}")
```

---

## RAGAgent

Location: `src/agents/rag_agent.py`

Retrieval-Augmented Generation using Databricks Vector Search.

```python
from src.agents.rag_agent import RAGAgent, RAGResult, Document
```

### Constructor

```python
agent = RAGAgent(config: Config)
```

### Methods

#### search()

```python
def search(
    self,
    query: str,
    num_results: int = 5,
) -> RAGResult
```

**Parameters:**
- `query`: Search query
- `num_results`: Maximum documents to return

**Returns:** `RAGResult`

**Example:**
```python
result = agent.search("What is our refund policy?")
if result.success:
    print(result.answer)
    print(result.format_sources())
```

---

## MultiGenieOrchestrator

Location: `src/agents/multi_genie_orchestrator.py`

Orchestrates queries across multiple Genie Spaces.

```python
from src.agents.multi_genie_orchestrator import (
    MultiGenieOrchestrator,
    GenieSpaceConfig,
    MultiGenieResult,
)
```

### GenieSpaceConfig

```python
@dataclass
class GenieSpaceConfig:
    space_id: str           # Genie Space ID
    name: str               # Human-readable name
    domain: str = ""        # Keywords for routing
    timeout_seconds: int = 120
    retry_count: int = 2
    retry_delay: float = 1.0
```

### Constructor

```python
orchestrator = MultiGenieOrchestrator(
    space_configs: list[GenieSpaceConfig],
    base_config: Config,
)
```

### Methods

#### query_spaces()

```python
def query_spaces(
    self,
    question: str,
    space_names: Optional[list[str]] = None,
    parallel: bool = True,
) -> MultiGenieResult
```

**Parameters:**
- `question`: Query to send to spaces
- `space_names`: Specific spaces to query (None = all)
- `parallel`: Run queries in parallel

**Returns:** `MultiGenieResult`

**Example:**
```python
spaces = [
    GenieSpaceConfig("id1", "Sales", "revenue, orders"),
    GenieSpaceConfig("id2", "CRM", "customers, segments"),
]
orchestrator = MultiGenieOrchestrator(spaces, config)

result = orchestrator.query_spaces(
    "Compare Q4 performance",
    space_names=["Sales", "CRM"]
)
print(result.to_combined_markdown())
```

---

## PlannerAgent

Location: `src/agents/planner_agent.py`

Decomposes complex questions into sub-queries.

```python
from src.agents.planner_agent import PlannerAgent, Plan, SubQuery
```

### Methods

#### decompose()

```python
def decompose(
    self,
    question: str,
    available_spaces: list[GenieSpaceConfig],
) -> Plan
```

**Returns:** `Plan` with sub-queries and target spaces

#### execute_plan()

```python
def execute_plan(
    self,
    plan: Plan,
    orchestrator: MultiGenieOrchestrator,
) -> MultiGenieResult
```

---

## SynthesizerAgent

Location: `src/agents/synthesizer_agent.py`

Synthesizes insights from multi-source query results.

```python
from src.agents.synthesizer_agent import (
    SynthesizerAgent,
    SynthesisResult,
    Insight,
    Correlation,
    Anomaly,
)
```

### Methods

#### synthesize()

```python
def synthesize(
    self,
    multi_result: MultiGenieResult,
    query: str,
    context: Optional[dict] = None,
) -> SynthesisResult
```

**Returns:** `SynthesisResult` with insights, correlations, anomalies, recommendations

---

## ReportWriter

Location: `src/agents/report_writer.py`

Generates formatted reports from agent results.

```python
from src.agents.report_writer import ReportWriter
```

### Methods

#### generate()

```python
def generate(
    self,
    synthesis: SynthesisResult,
    format: str = "markdown",
) -> str
```

**Parameters:**
- `synthesis`: Results to format
- `format`: Output format (markdown, html)

---

## Supervisor

Location: `src/agents/supervisor.py`

LangGraph-based supervisor agent that routes between Genie and RAG.

```python
from src.agents.supervisor import create_supervisor_agent, AgentState
```

### Factory Function

```python
def create_supervisor_agent(config: Config) -> CompiledStateGraph
```

### AgentState

```python
class AgentState(TypedDict):
    messages: Annotated[list, add]
    context: str
    iteration_count: int
```

### Usage

```python
supervisor = create_supervisor_agent(config)
result = supervisor.invoke({
    "messages": [{"role": "user", "content": "What was Q4 revenue?"}]
})
```

---

## Result Classes

### GenieResult

```python
@dataclass
class GenieResult:
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    sql: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    columns: list[str] = field(default_factory=list)

    def to_markdown_table(self, max_rows: int = 10) -> str: ...
```

### RAGResult

```python
@dataclass
class RAGResult:
    success: bool
    answer: str = ""
    documents: list[Document] = field(default_factory=list)
    error: Optional[str] = None

    def format_sources(self) -> str: ...
```

### MultiGenieResult

```python
@dataclass
class MultiGenieResult:
    results: dict[str, GenieResult]
    metadata: ResultMetadata

    @property
    def any_success(self) -> bool: ...
    @property
    def all_success(self) -> bool: ...
    def to_combined_markdown(self, max_rows_per_space: int = 10) -> str: ...
```

### SynthesisResult

```python
@dataclass
class SynthesisResult:
    success: bool
    key_insights: list[Insight] = field(default_factory=list)
    cross_domain_correlations: list[Correlation] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    domains_analyzed: list[str] = field(default_factory=list)

    def to_markdown(self) -> str: ...
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABRICKS_HOST` | Yes* | Workspace URL |
| `DATABRICKS_TOKEN` | Yes* | Personal Access Token |
| `GENIE_SPACE_ID` | Yes* | Primary Genie Space ID |
| `GENIE_SPACES` | No | JSON for multiple spaces |
| `WAREHOUSE_ID` | No | SQL Warehouse ID |
| `MODEL_ENDPOINT` | No | LLM endpoint name |
| `MOCK_MODE` | No | Enable mock mode |
| `VECTOR_SEARCH_ENDPOINT` | No | VS endpoint for RAG |
| `VECTOR_SEARCH_INDEX` | No | VS index for RAG |
| `CACHE_ENABLED` | No | Enable caching |
| `CACHE_TTL_SECONDS` | No | Cache TTL |

*Not required when `MOCK_MODE=true`
