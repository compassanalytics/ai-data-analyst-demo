# Agent Implementation Patterns

This document describes the established patterns used across agent implementations in this codebase. Follow these patterns when implementing new agents like `ReportWriter`.

## Table of Contents

1. [Agent Class Structure](#agent-class-structure)
2. [Config Integration](#config-integration)
3. [Result Dataclasses](#result-dataclasses)
4. [Mock Mode Pattern](#mock-mode-pattern)
5. [Lazy-Loading Pattern for External Clients](#lazy-loading-pattern-for-external-clients)
6. [Agent Integration Patterns](#agent-integration-patterns)
7. [File Structure and Exports](#file-structure-and-exports)

---

## Agent Class Structure

All agents follow a consistent class structure:

### Basic Template

```python
"""Module docstring - describe the agent's purpose.

This module provides a [Agent Name] that [core functionality description].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.config import Config


@dataclass
class AgentResult:
    """Result from the agent operation.

    Attributes:
        success: Whether the operation completed successfully
        # ... domain-specific fields
        error: Error message if operation failed
    """
    success: bool
    # domain-specific fields with defaults
    error: Optional[str] = None

    def format_method(self) -> str:
        """Format the result for display."""
        # formatting logic
        pass


class Agent:
    """Main agent class.

    Docstring with example usage.

    Example:
        >>> config = Config(mock_mode=True)
        >>> agent = Agent(config)
        >>> result = agent.operation("input")
        >>> print(result.format_method())
    """

    def __init__(self, config: Config):
        """Initialize the agent.

        Args:
            config: Configuration instance with settings
        """
        self.config = config
        self._client = None  # Lazy-loaded clients
        # Additional private state

    @property
    def client(self):
        """Lazy-load external client."""
        if self._client is None and not self.config.mock_mode:
            from some_sdk import Client
            self._client = Client(...)
        return self._client

    def operation(self, input: str) -> AgentResult:
        """Main public method.

        Args:
            input: Description

        Returns:
            AgentResult with results or error
        """
        if self.config.mock_mode:
            return self._mock_operation(input)
        return self._real_operation(input)

    def _real_operation(self, input: str) -> AgentResult:
        """Execute real operation with external services."""
        try:
            # Real implementation
            return AgentResult(success=True, ...)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    def _mock_operation(self, input: str) -> AgentResult:
        """Return mock data for demonstration."""
        # Pattern matching on input to return contextual mock data
        return AgentResult(success=True, ...)
```

---

## Config Integration

### The Config Dataclass

Located in `/Users/julien.hovan/Playground/ai-data-analyst-workshop/src/config.py`, the `Config` class provides centralized configuration:

```python
@dataclass
class Config:
    """Configuration settings.

    Attributes:
        databricks_host: Databricks workspace URL
        databricks_token: Personal access token (for local dev only)
        genie_space_id: The Genie Space ID for data analysis
        warehouse_id: SQL Warehouse ID for queries
        model_endpoint: Model serving endpoint for ChatDatabricks
        mock_mode: Enable mock mode for demos without real access
        vector_search_endpoint: Optional Vector Search endpoint
        vector_search_index: Optional Vector Search index name
        embedding_endpoint: Embedding model endpoint
        genie_spaces_json: JSON config for multiple Genie Spaces
    """
    databricks_host: str = field(default="")
    databricks_token: Optional[str] = field(default=None, repr=False)
    # ... other fields
    mock_mode: bool = field(default=False)
```

### Config Loading Methods

- `Config.from_env()` - Load from environment variables
- `Config.from_databricks_secrets(scope)` - Load from Databricks secrets
- `Config.from_notebook_params(params)` - Load from notebook widgets
- `get_config()` - Singleton pattern with caching

### Usage Pattern

Agents always receive Config in their constructor:

```python
def __init__(self, config: Config):
    self.config = config
```

---

## Result Dataclasses

### Common Pattern

All result classes follow these conventions:

1. **Use `@dataclass` decorator**
2. **First field is always `success: bool`**
3. **Use `field(default_factory=...)` for mutable defaults**
4. **Last field (if applicable) is `error: Optional[str] = None`**
5. **Provide formatting methods for display**

### GenieResult Example

```python
@dataclass
class GenieResult:
    """Result from a Genie query."""
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    sql: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    columns: list[str] = field(default_factory=list)

    def to_markdown_table(self, max_rows: int = 10) -> str:
        """Convert results to a markdown table."""
        if not self.data:
            return "_No results_"

        columns = self.columns or list(self.data[0].keys())

        # Header
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"

        # Rows
        rows = []
        for row in self.data[:max_rows]:
            row_values = [str(row.get(col, "")) for col in columns]
            rows.append("| " + " | ".join(row_values) + " |")

        result = "\n".join([header, separator] + rows)

        if len(self.data) > max_rows:
            result += f"\n\n_Showing {max_rows} of {len(self.data)} rows_"

        return result
```

### RAGResult Example

```python
@dataclass
class RAGResult:
    """Result from a RAG query."""
    success: bool
    answer: str = ""
    documents: list[Document] = field(default_factory=list)
    error: Optional[str] = None

    def format_sources(self) -> str:
        """Format the source documents as a citation list."""
        if not self.documents:
            return "_No sources_"

        lines = ["**Sources:**"]
        for i, doc in enumerate(self.documents, 1):
            score_str = f" (relevance: {doc.score:.2f})" if doc.score else ""
            lines.append(f"{i}. {doc.source}{score_str}")

        return "\n".join(lines)
```

### SynthesisResult Example (Complex)

```python
@dataclass
class SynthesisResult:
    """Complete synthesis output."""
    success: bool
    key_insights: list[Insight] = field(default_factory=list)
    cross_domain_correlations: list[Correlation] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    domains_analyzed: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Format synthesis as markdown report."""
        # Multi-section markdown generation
        sections = []

        # Header with success/failure indicator
        if self.success:
            sections.append("# Cross-Domain Synthesis Report")
        else:
            sections.append("# Synthesis Report (Incomplete)")
            if self.error:
                sections.append(f"\n**Error:** {self.error}")

        # ... additional sections

        return "\n".join(sections)
```

---

## Mock Mode Pattern

### Design Principles

1. **Check `config.mock_mode` first in public methods**
2. **Separate `_real_*` and `_mock_*` method implementations**
3. **Mock methods return realistic, context-aware fake data**
4. **Pattern match on input to provide relevant mock responses**

### Implementation Pattern

```python
def query(self, question: str) -> Result:
    """Main method routing to real or mock implementation."""
    if self.config.mock_mode:
        return self._mock_query(question)
    return self._real_query(question)

def _real_query(self, question: str) -> Result:
    """Execute real query against external services."""
    try:
        # Real implementation with SDK calls
        pass
    except Exception as e:
        return Result(success=False, error=str(e))

def _mock_query(self, question: str) -> Result:
    """Return mock data for demonstration purposes."""
    question_lower = question.lower()

    # Pattern matching for contextual responses
    if "revenue" in question_lower or "sales" in question_lower:
        return Result(
            success=True,
            data=[{"product": "Enterprise Suite", "revenue": 2450000}, ...],
            description="Top products by revenue",
        )

    elif "customer" in question_lower:
        return Result(
            success=True,
            data=[{"segment": "Enterprise", "count": 125}, ...],
            description="Customer segmentation",
        )

    # Default/fallback mock response
    else:
        return Result(
            success=True,
            data=[{"metric": "Total Revenue", "value": 10000000}, ...],
            description=f"Summary metrics for: {question}",
        )
```

### Best Practices

- Provide 3-5 specific scenario mocks based on common keywords
- Always have a generic fallback response
- Include realistic data values and structures
- Mock responses should mirror the shape of real responses

---

## Lazy-Loading Pattern for External Clients

### Why Lazy-Loading?

1. **Avoids import errors** when SDK is not installed
2. **Delays connection** until actually needed
3. **Respects mock mode** - no client initialization in mock
4. **Reduces startup time** for the application

### Implementation Pattern

```python
class Agent:
    def __init__(self, config: Config):
        self.config = config
        self._client = None      # SDK client
        self._vs_client = None   # Vector Search client
        self._llm = None         # LLM client

    @property
    def client(self):
        """Lazy-load the Databricks SDK client."""
        if self._client is None and not self.config.mock_mode:
            from databricks.sdk import WorkspaceClient

            self._client = WorkspaceClient(
                host=self.config.databricks_host or None,
                token=self.config.databricks_token,
            )
        return self._client

    @property
    def vs_client(self):
        """Lazy-load the VectorSearchClient."""
        if self._vs_client is None and not self.config.mock_mode:
            from databricks.vector_search.client import VectorSearchClient

            self._vs_client = VectorSearchClient(
                workspace_url=self.config.databricks_host,
                personal_access_token=self.config.databricks_token,
            )
        return self._vs_client

    @property
    def llm(self):
        """Lazy-load ChatDatabricks for LLM operations."""
        if self._llm is None and not self.config.mock_mode:
            from databricks_langchain import ChatDatabricks

            self._llm = ChatDatabricks(
                endpoint=self.config.model_endpoint,
                temperature=0.1,
            )
        return self._llm
```

### Key Points

1. **Private attribute with underscore prefix** (`self._client`)
2. **Property decorator** for lazy access
3. **Guard with `not self.config.mock_mode`** to skip in mock mode
4. **Import inside the property** to avoid import-time errors
5. **Use config values** for initialization parameters

---

## Agent Integration Patterns

### 1. Direct Composition (Agent uses Agent)

The `MultiGenieOrchestrator` creates and manages multiple `GenieDataAgent` instances:

```python
class MultiGenieOrchestrator:
    def __init__(self, space_configs: list[GenieSpaceConfig], base_config: Config):
        self._base_config = base_config
        self._agents: dict[str, GenieDataAgent] = {}  # Lazy agent cache

    def _get_agent(self, space_config: GenieSpaceConfig) -> GenieDataAgent:
        """Get or create a GenieDataAgent for a space."""
        if space_config.name not in self._agents:
            # Create config with this space's ID
            config = Config(
                databricks_host=self._base_config.databricks_host,
                databricks_token=self._base_config.databricks_token,
                genie_space_id=space_config.space_id,  # Override for this space
                mock_mode=self._base_config.mock_mode,
                # ... other inherited settings
            )
            self._agents[space_config.name] = GenieDataAgent(config)

        return self._agents[space_config.name]
```

### 2. Result Consumption (Agent consumes another Agent's Result)

The `SynthesizerAgent` consumes `MultiGenieResult`:

```python
class SynthesizerAgent:
    def synthesize(
        self,
        multi_result: "MultiGenieResult",  # TYPE_CHECKING import
        query: str,
        context: Optional[dict] = None,
    ) -> SynthesisResult:
        # Check for successful results
        if not multi_result.any_success:
            return SynthesisResult(
                success=False,
                error="No successful query results to synthesize",
            )

        # Use the result's formatting method
        combined_data = multi_result.to_combined_markdown(max_rows_per_space=10)

        # Build warnings from failed queries
        warnings = []
        for name, result in multi_result.results.items():
            if not result.success:
                warnings.append(f"Data from '{name}' unavailable: {result.error}")
```

### 3. TYPE_CHECKING for Circular Import Prevention

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.multi_genie_orchestrator import (
        GenieSpaceConfig,
        MultiGenieOrchestrator,
        MultiGenieResult,
    )
```

### 4. Plan Execution Pattern

The `PlannerAgent` creates plans that can be executed by the orchestrator:

```python
class PlannerAgent:
    def decompose(self, question: str) -> Plan:
        """Create execution plan."""
        pass

    def execute_plan(
        self,
        plan: Plan,
        orchestrator: MultiGenieOrchestrator,
    ) -> MultiGenieResult:
        """Execute a plan using the orchestrator."""
        return orchestrator.query_spaces(
            plan.original_question,
            space_names=plan.target_spaces,
        )
```

---

## File Structure and Exports

### Agent File Location

All agents are located in `/Users/julien.hovan/Playground/ai-data-analyst-workshop/src/agents/`:

```
src/agents/
    __init__.py           # Exports all public symbols
    genie_agent.py        # GenieDataAgent, GenieResult, QueryStatus
    rag_agent.py          # RAGAgent, RAGResult, Document
    multi_genie_orchestrator.py  # MultiGenieOrchestrator, GenieSpaceConfig, etc.
    planner_agent.py      # PlannerAgent, Plan, SubQuery
    synthesizer_agent.py  # SynthesizerAgent, SynthesisResult, etc.
    supervisor.py         # create_supervisor_agent, AgentState
```

### Export Pattern in `__init__.py`

```python
"""Agent modules for the AI Data Analyst demo."""

from src.agents.genie_agent import GenieDataAgent
from src.agents.rag_agent import RAGAgent
from src.agents.multi_genie_orchestrator import (
    MultiGenieOrchestrator,
    GenieSpaceConfig,
    MultiGenieResult,
    ResultMetadata,
)
# ... other imports

__all__ = [
    "GenieDataAgent",
    "RAGAgent",
    "MultiGenieOrchestrator",
    "GenieSpaceConfig",
    "MultiGenieResult",
    "ResultMetadata",
    # ... all public symbols
]
```

### Naming Conventions

- **Agent class**: `{Domain}Agent` (e.g., `GenieDataAgent`, `RAGAgent`, `PlannerAgent`)
- **Result class**: `{Domain}Result` (e.g., `GenieResult`, `RAGResult`, `SynthesisResult`)
- **Config class**: `{Domain}Config` (e.g., `GenieSpaceConfig`)
- **File name**: `{domain}_agent.py` or `{purpose}.py`

---

## Summary Checklist for New Agent Implementation

When implementing a new agent (e.g., `ReportWriter`), ensure:

- [ ] Create result dataclass with `success: bool` as first field
- [ ] Include `error: Optional[str] = None` for error handling
- [ ] Add formatting method(s) to result class (e.g., `to_markdown()`, `to_pdf()`)
- [ ] Agent constructor accepts `Config` as parameter
- [ ] Use `self._client = None` pattern for lazy-loadable clients
- [ ] Implement `@property` for lazy client loading
- [ ] Guard client initialization with `not self.config.mock_mode`
- [ ] Public methods check `config.mock_mode` and route accordingly
- [ ] Implement `_real_*` method with try/except returning Result
- [ ] Implement `_mock_*` method with pattern-matched responses
- [ ] Add agent and result classes to `__init__.py` exports
- [ ] Include module docstring with purpose description
- [ ] Include class docstring with example usage
