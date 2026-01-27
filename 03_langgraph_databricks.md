# LangGraph Integration with Databricks Notebooks

**Research Date:** January 26, 2026
**Purpose:** Workshop Demo - LangGraph + Databricks Integration Patterns

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Running LangGraph Agents in Databricks Notebooks](#1-running-langgraph-agents-in-databricks-notebooks)
3. [LangGraph + Genie Space API Integration](#2-langgraph--genie-space-api-integration)
4. [Best Practices for LangGraph in Databricks](#3-best-practices-for-langgraph-in-databricks)
5. [MLflow Integration with LangGraph](#4-mlflow-integration-with-langgraph)
6. [Databricks as Vector Store with LangGraph](#5-databricks-as-vector-store-with-langgraph)
7. [Example Architectures](#6-example-architectures)
8. [Deploying LangGraph Agents on Databricks](#7-deploying-langgraph-agents-on-databricks)
9. [Sample Notebook Code Patterns](#8-sample-notebook-code-patterns)
10. [Sources](#sources)

---

## Executive Summary

LangGraph is an open-source framework for building stateful, multi-actor applications with LLMs. It enables creating agent and multi-agent workflows using graph-based state machines. Databricks provides first-class integration with LangGraph through:

- **Mosaic AI Agent Framework**: Full lifecycle support for building, evaluating, and deploying LangGraph agents
- **MLflow 3 Tracing**: Automatic capture of graph execution with deep observability
- **Unity Catalog Integration**: Use governed SQL/Python functions as agent tools
- **Genie Space API**: Query structured data through natural language within LangGraph workflows
- **Vector Search**: Serverless similarity search for RAG applications
- **MCP Server Support**: Model Context Protocol integration for standardized tool access

**Key Requirements:**
- Python 3.10+
- Databricks Runtime 13.3 LTS+ or Serverless Compute
- MLflow 3.1.3+ for deployment features
- `databricks-langchain` package for native integrations

---

## 1. Running LangGraph Agents in Databricks Notebooks

### Environment Setup

```python
# Cell 1: Install dependencies
%pip install --upgrade \
    "mlflow[databricks]>=3.1" \
    langgraph \
    langchain_core \
    langchain_openai \
    databricks-langchain \
    unitycatalog-langchain[databricks]

dbutils.library.restartPython()
```

### Basic LangGraph Agent in Notebook

```python
# Cell 2: Import and configure
import mlflow
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from databricks_langchain import ChatDatabricks

# Enable automatic tracing (required on serverless compute)
mlflow.langchain.autolog()

# Set MLflow tracking
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/langgraph-workshop-demo")
```

```python
# Cell 3: Define tools and create agent
@tool
def get_customer_info(customer_id: str) -> str:
    """Retrieve customer information from the database."""
    # In production, this would query your Delta tables
    return f"Customer {customer_id}: Premium tier, Active since 2023"

@tool
def calculate_discount(amount: float, tier: str) -> float:
    """Calculate discount based on customer tier."""
    discounts = {"Premium": 0.20, "Standard": 0.10, "Basic": 0.05}
    return amount * discounts.get(tier, 0)

# Use Databricks Foundation Model API
llm = ChatDatabricks(
    endpoint="databricks-meta-llama-3-3-70b-instruct",
    temperature=0.1
)

# Create the ReAct agent
agent = create_react_agent(
    model=llm,
    tools=[get_customer_info, calculate_discount],
    prompt="You are a helpful customer service assistant."
)
```

```python
# Cell 4: Run the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "What discount can customer C123 get on a $500 purchase?"}]
})

print(result["messages"][-1].content)
```

### Streaming Output in Notebooks

```python
# Cell 5: Stream agent execution for real-time feedback
inputs = {"messages": [{"role": "user", "content": "Help me understand my account status"}]}

for chunk in agent.stream(inputs, stream_mode="updates"):
    print(chunk)
    print("---")
```

---

## 2. LangGraph + Genie Space API Integration

### Overview

The Genie Conversation API enables natural language queries against structured data. Combined with LangGraph, you can build multi-agent systems that handle both structured (SQL) and unstructured (documents) data queries.

### GenieAgent Setup

```python
from databricks_langchain.genie import GenieAgent

# Create a Genie agent for structured data queries
genie_agent = GenieAgent(
    genie_space_id="your-genie-space-id",  # From Genie Space URL
    genie_agent_name="SalesDataAgent",
    description="Queries structured sales data including revenue, orders, and customer metrics"
)
```

### Multi-Agent Supervisor with Genie

This pattern creates a supervisor that routes queries to specialized agents:

```python
from typing import Literal
from langchain_core.runnables import Runnable
from pydantic import BaseModel
from databricks_langchain.agent import UCFunctionToolkit, create_agent, create_supervisor
from databricks_langchain.chat_models import ChatDatabricks
from databricks_langchain.genie import GenieAgent

# Define agent types
class Genie(BaseModel):
    space_id: str
    name: str
    description: str

class InCodeSubAgent(BaseModel):
    tools: list[str]
    name: str
    description: str

def create_multi_agent_system(llm: Runnable):
    """Create a supervisor agent with Genie and tool-calling sub-agents."""

    agents = []
    agent_descriptions = ""

    # Add Genie agent for structured data
    genie_config = Genie(
        space_id="abc123-your-space-id",
        name="StructuredDataAgent",
        description="Queries sales metrics, revenue data, and customer analytics from Delta tables"
    )

    genie_agent = GenieAgent(
        genie_space_id=genie_config.space_id,
        genie_agent_name=genie_config.name,
        description=genie_config.description,
    )
    agents.append(genie_agent)
    agent_descriptions += f"- {genie_config.name}: {genie_config.description}\n"

    # Add in-code agent with Unity Catalog tools
    uc_toolkit = UCFunctionToolkit(
        function_names=["catalog.schema.calculate_metrics", "catalog.schema.send_notification"]
    )

    tool_agent = create_agent(
        llm,
        tools=uc_toolkit.tools,
        name="ToolAgent"
    )
    agents.append(tool_agent)
    agent_descriptions += "- ToolAgent: Executes calculations and sends notifications\n"

    # Create supervisor prompt
    supervisor_prompt = f"""
    You are a supervisor coordinating a team of specialized agents.

    Available agents:
    {agent_descriptions}

    Route queries to the appropriate agent:
    - Use StructuredDataAgent for numeric/metric questions about sales, revenue, orders
    - Use ToolAgent for calculations and actions

    Synthesize responses from multiple agents when needed.
    """

    return create_supervisor(
        agents=agents,
        model=llm,
        prompt=supervisor_prompt,
        output_mode="full_history",
    ).compile()

# Create and run the multi-agent system
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
supervisor = create_multi_agent_system(llm)

result = supervisor.invoke({
    "messages": [{"role": "user", "content": "What was Q4 revenue and how does it compare to our target?"}]
})
```

### Genie API Direct Integration

For more control, use the Genie Conversation API directly:

```python
import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

def query_genie_space(space_id: str, question: str) -> dict:
    """Query a Genie Space and return the response."""

    # Start a new conversation
    conversation = w.genie.start_conversation(
        space_id=space_id,
        content=question
    )

    # Poll for completion
    while conversation.status == "PENDING":
        conversation = w.genie.get_conversation(
            space_id=space_id,
            conversation_id=conversation.conversation_id
        )

    return {
        "answer": conversation.response.content,
        "sql_query": conversation.response.sql_query if hasattr(conversation.response, 'sql_query') else None,
        "data": conversation.response.data if hasattr(conversation.response, 'data') else None
    }
```

---

## 3. Best Practices for LangGraph in Databricks

### State Management

```python
from typing import Annotated, TypedDict
from operator import add
from langgraph.graph import StateGraph, START, END

# Use TypedDict for explicit state schemas
class AgentState(TypedDict):
    messages: Annotated[list, add]  # Accumulate messages
    context: str                     # Current context
    iteration_count: int             # Track iterations

# Keep state minimal - avoid dumping transient values
def process_node(state: AgentState) -> dict:
    # Only return what needs to persist
    return {
        "messages": [{"role": "assistant", "content": "Processed"}],
        "iteration_count": state["iteration_count"] + 1
    }
```

### Memory Configuration

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# Development: InMemorySaver (fast but non-persistent)
dev_checkpointer = InMemorySaver()

# Production: SqliteSaver or PostgresSaver
# For Databricks notebooks, SQLite works well for demos
prod_checkpointer = SqliteSaver.from_conn_string("/dbfs/tmp/checkpoints.db")

# Compile graph with checkpointer
graph = builder.compile(checkpointer=prod_checkpointer)

# Use thread_id for conversation continuity
config = {"configurable": {"thread_id": "user-123-session-456"}}
result = graph.invoke({"messages": []}, config)

# Resume later with same thread_id
saved_state = graph.get_state(config)
```

### Error Handling

```python
from langgraph.graph import StateGraph

def safe_node(state):
    """Node with error handling."""
    try:
        # Your logic here
        result = process_data(state)
        return {"status": "success", "data": result}
    except Exception as e:
        # Log to MLflow
        mlflow.log_param("error_node", "safe_node")
        mlflow.log_param("error_message", str(e))
        return {"status": "error", "error": str(e)}

def should_retry(state) -> str:
    """Conditional edge for retry logic."""
    if state.get("status") == "error" and state.get("retry_count", 0) < 3:
        return "retry"
    return "continue"

builder = StateGraph(AgentState)
builder.add_node("process", safe_node)
builder.add_conditional_edges("process", should_retry, {"retry": "process", "continue": END})
```

### Streaming Best Practices

```python
# Choose stream mode based on use case

# For chatbots - stream individual tokens
for chunk in agent.stream(inputs, stream_mode="messages"):
    print(chunk, end="", flush=True)

# For long-running agents - stream state updates
for update in agent.stream(inputs, stream_mode="updates"):
    print(f"Node: {update.get('node')}, Status: {update.get('status')}")

# For debugging - stream full values
for state in agent.stream(inputs, stream_mode="values"):
    print(f"Full state: {state}")
```

### Databricks-Specific Best Practices

1. **Use Serverless Compute**: Provides automatic scaling and latest runtime features
2. **Explicitly Enable Autolog**: On serverless, call `mlflow.langchain.autolog()` explicitly
3. **Leverage Unity Catalog**: Store tools as governed functions for discoverability
4. **Use ChatDatabricks**: Native integration with Foundation Model APIs
5. **Configure Timeouts**: Set appropriate timeouts for tool calls to external systems

---

## 4. MLflow Integration with LangGraph

### Automatic Tracing Setup

```python
import mlflow
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Enable autologging - this traces all LangGraph executions
mlflow.langchain.autolog()

# Configure MLflow to use Databricks
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/langgraph-tracing-demo")

@tool
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    return f"It's sunny in {city}"

llm = ChatOpenAI(model="gpt-4o-mini")
graph = create_react_agent(llm, [get_weather])

# This invocation is automatically traced
result = graph.invoke({
    "messages": [{"role": "user", "content": "What's the weather in SF?"}]
})

# View traces in MLflow UI: Experiment -> Traces tab
```

### Manual Span Creation

For more granular control:

```python
import mlflow

def custom_node(state):
    """Node with custom tracing spans."""

    with mlflow.start_span(name="data_validation") as span:
        span.set_attribute("input_length", len(state.get("messages", [])))
        validated = validate_input(state)
        span.set_attribute("validation_passed", validated)

    with mlflow.start_span(name="processing") as span:
        result = process_data(state)
        span.set_attribute("result_type", type(result).__name__)

    return {"processed_data": result}
```

### Logging Models for Deployment

```python
import mlflow
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksFunction

# Define resources the agent needs
resources = [
    DatabricksServingEndpoint(endpoint_name="databricks-meta-llama-3-3-70b-instruct"),
    DatabricksFunction(function_name="catalog.schema.my_tool"),
]

# Log the agent
with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model="agent.py",  # Your agent code file
        pip_requirements=[
            "mlflow>=3.1",
            "langchain",
            "langgraph",
            "databricks-langchain",
        ],
        resources=resources,
    )

    # Register to Unity Catalog
    mlflow.register_model(
        f"runs:/{mlflow.active_run().info.run_id}/agent",
        "catalog.schema.my_langgraph_agent"
    )
```

### Disabling Auto-Tracing

```python
# Disable globally
mlflow.langchain.autolog(disable=True)

# Or disable all autologging
mlflow.autolog(disable=True)
```

---

## 5. Databricks as Vector Store with LangGraph

### VectorSearchRetrieverTool Setup

```python
from databricks_langchain import VectorSearchRetrieverTool, ChatDatabricks
from langgraph.prebuilt import create_react_agent

# Create vector search retriever tool
retriever_tool = VectorSearchRetrieverTool(
    index_name="catalog.schema.document_index",
    tool_description="Search company documentation for policies, procedures, and technical guides",
    # Optional: Add filters
    # filters={"department": "engineering"}
)

# Create agent with retrieval capability
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
rag_agent = create_react_agent(
    model=llm,
    tools=[retriever_tool],
    prompt="You are a helpful assistant that answers questions using company documentation."
)

# Query with RAG
result = rag_agent.invoke({
    "messages": [{"role": "user", "content": "What is our vacation policy?"}]
})
```

### Custom Retriever Integration

```python
from databricks_langchain import DatabricksVectorSearch
from langchain_core.tools import tool

# Create vector store
vector_store = DatabricksVectorSearch(
    index_name="catalog.schema.knowledge_base",
    embedding_model="databricks-bge-large-en"  # Or your embedding endpoint
)

# Convert to retriever
retriever = vector_store.as_retriever(
    search_kwargs={"k": 5}
)

# Create custom retrieval tool with post-processing
@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information."""
    docs = retriever.invoke(query)

    # Format results
    results = []
    for i, doc in enumerate(docs, 1):
        results.append(f"{i}. {doc.page_content[:200]}...")

    return "\n\n".join(results)
```

### Agentic RAG Pattern

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from operator import add

class RAGState(TypedDict):
    messages: Annotated[list, add]
    retrieved_docs: list
    should_retrieve: bool

def route_query(state) -> str:
    """Decide whether to retrieve or answer directly."""
    last_message = state["messages"][-1]["content"]

    # Simple heuristic - in production, use LLM routing
    if any(word in last_message.lower() for word in ["policy", "procedure", "document", "guide"]):
        return "retrieve"
    return "answer"

def retrieve_docs(state):
    """Retrieve relevant documents."""
    query = state["messages"][-1]["content"]
    docs = retriever.invoke(query)
    return {"retrieved_docs": docs}

def generate_answer(state):
    """Generate answer using retrieved docs or LLM knowledge."""
    context = "\n".join([d.page_content for d in state.get("retrieved_docs", [])])

    messages = state["messages"] + [
        {"role": "system", "content": f"Context:\n{context}" if context else "No additional context."}
    ]

    response = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": response.content}]}

# Build the graph
builder = StateGraph(RAGState)
builder.add_node("retrieve", retrieve_docs)
builder.add_node("answer", generate_answer)

builder.add_conditional_edges(START, route_query, {"retrieve": "retrieve", "answer": "answer"})
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)

rag_graph = builder.compile()
```

### Reranking for Better Results

Databricks Vector Search supports built-in reranking (Public Preview):

```python
# Enable reranking for higher quality retrieval
retriever_tool = VectorSearchRetrieverTool(
    index_name="catalog.schema.document_index",
    tool_description="Search documents with reranking",
    rerank=True,  # Enable reranking
    rerank_top_k=20,  # Retrieve 20, rerank to return top k
)
```

---

## 6. Example Architectures

### Architecture 1: Simple RAG Agent

```
User Query
    |
    v
[LangGraph Agent]
    |
    +---> [Vector Search Tool] ---> Delta Table Index
    |
    +---> [LLM (ChatDatabricks)] ---> Foundation Model API
    |
    v
Response
```

### Architecture 2: Multi-Agent with Genie

```
User Query
    |
    v
[Supervisor Agent (LangGraph)]
    |
    +---> [GenieAgent] ---> Genie Space ---> Delta Tables (Structured)
    |
    +---> [RAG Agent] ---> Vector Search ---> Documents (Unstructured)
    |
    +---> [Tool Agent] ---> Unity Catalog Functions
    |
    v
[Synthesized Response]
```

### Architecture 3: Production Deployment

```
                    +-------------------+
                    |   AI Playground   |
                    |   / REST API      |
                    +--------+----------+
                             |
                             v
+------------+      +--------+----------+      +------------------+
|  MLflow    |      |  Model Serving    |      |  Unity Catalog   |
|  Tracking  |<-----|  Endpoint         |----->|  Functions       |
+------------+      +--------+----------+      +------------------+
                             |
                             v
                    +--------+----------+
                    |  LangGraph Agent  |
                    |  (ResponsesAgent) |
                    +--------+----------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
+-------+------+    +--------+-------+    +------+-------+
| Genie Space  |    | Vector Search  |    | External APIs|
| (SQL/Tables) |    | (Documents)    |    | (MCP Server) |
+--------------+    +----------------+    +--------------+
```

### Architecture 4: MCP Integration

```python
from databricks_mcp import DatabricksMCPClient
from langgraph.prebuilt import create_react_agent

# Connect to Databricks managed MCP servers
mcp_client = DatabricksMCPClient()

# Get tools from MCP servers
genie_tools = mcp_client.get_tools(server_url="mcp://genie-space/your-space-id")
uc_tools = mcp_client.get_tools(server_url="mcp://unity-catalog/your-catalog")

# Combine tools in LangGraph agent
all_tools = genie_tools + uc_tools

agent = create_react_agent(
    model=llm,
    tools=all_tools,
    prompt="You have access to structured data and Unity Catalog functions."
)
```

---

## 7. Deploying LangGraph Agents on Databricks

### Step 1: Wrap Agent with ResponsesAgent

```python
# agent.py - Your agent code file
from mlflow.pyfunc import PythonModel
from mlflow.types.agent import ResponsesAgentRequest, ResponsesAgentResponse

class MyLangGraphAgent(PythonModel):
    def load_context(self, context):
        """Load the agent when the model is loaded."""
        import mlflow
        from langgraph.prebuilt import create_react_agent
        from databricks_langchain import ChatDatabricks

        mlflow.langchain.autolog()

        self.llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
        self.agent = create_react_agent(
            model=self.llm,
            tools=self._create_tools(),
            prompt="You are a helpful assistant."
        )

    def _create_tools(self):
        """Define your tools here."""
        from langchain_core.tools import tool

        @tool
        def get_info(query: str) -> str:
            """Get information."""
            return f"Info for: {query}"

        return [get_info]

    def predict(self, context, model_input: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Handle prediction requests."""
        messages = [{"role": m.role, "content": m.content} for m in model_input.messages]

        result = self.agent.invoke({"messages": messages})

        return ResponsesAgentResponse(
            messages=[{
                "role": "assistant",
                "content": result["messages"][-1].content
            }]
        )
```

### Step 2: Log and Register the Model

```python
import mlflow
from mlflow.models.resources import DatabricksServingEndpoint

# Define resources
resources = [
    DatabricksServingEndpoint(endpoint_name="databricks-meta-llama-3-3-70b-instruct"),
]

# Log the model
with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        artifact_path="langgraph_agent",
        python_model="agent.py",
        pip_requirements=[
            "mlflow>=3.1",
            "langgraph",
            "langchain",
            "databricks-langchain",
        ],
        resources=resources,
        registered_model_name="catalog.schema.my_langgraph_agent"
    )
```

### Step 3: Deploy to Model Serving

```python
from databricks import agents

# Deploy the registered model
deployment_info = agents.deploy(
    model_name="catalog.schema.my_langgraph_agent",
    model_version=1,
    scale_to_zero=True,  # Cost-effective for demos
    environment_vars={
        "DATABRICKS_HOST": "{{secrets/scope/host}}",
        "DATABRICKS_TOKEN": "{{secrets/scope/token}}"
    }
)

print(f"Endpoint: {deployment_info.endpoint_name}")
print(f"Status: {deployment_info.status}")
```

### Step 4: Test the Deployed Agent

```python
# Test via REST API
import requests

endpoint_url = f"https://{workspace_url}/serving-endpoints/{deployment_info.endpoint_name}/invocations"

response = requests.post(
    endpoint_url,
    headers={"Authorization": f"Bearer {token}"},
    json={
        "messages": [{"role": "user", "content": "Hello, how can you help me?"}]
    }
)

print(response.json())
```

### State Management Considerations

**Important:** Databricks Model Serving is distributed. The same replica may not handle all requests in a multi-turn conversation. Design accordingly:

```python
class StatefulAgent(PythonModel):
    def predict(self, context, model_input):
        # Use external state store for multi-turn conversations
        thread_id = model_input.thread_id

        # Retrieve state from external store (Redis, DynamoDB, etc.)
        state = self.state_store.get(thread_id)

        # Process with state
        result = self.agent.invoke({"messages": messages}, config={"thread_id": thread_id})

        # Save updated state
        self.state_store.put(thread_id, result)

        return result
```

---

## 8. Sample Notebook Code Patterns

### Pattern 1: Quick Start Agent

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph langchain databricks-langchain
dbutils.library.restartPython()

# Cmd 2: Imports and Config
import mlflow
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from databricks_langchain import ChatDatabricks

mlflow.langchain.autolog()
mlflow.set_experiment("/Users/your-email/langgraph-demo")

# Cmd 3: Define Tools
@tool
def search_products(query: str) -> str:
    """Search product catalog."""
    # Replace with actual Spark SQL query
    return f"Found products matching: {query}"

@tool
def check_inventory(product_id: str) -> str:
    """Check product inventory."""
    return f"Product {product_id}: 150 units in stock"

# Cmd 4: Create Agent
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
agent = create_react_agent(llm, [search_products, check_inventory])

# Cmd 5: Test
result = agent.invoke({
    "messages": [{"role": "user", "content": "Find laptops and check inventory for the first one"}]
})
display(result)
```

### Pattern 2: RAG with Vector Search

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph databricks-langchain
dbutils.library.restartPython()

# Cmd 2: Configure
import mlflow
from databricks_langchain import ChatDatabricks, VectorSearchRetrieverTool
from langgraph.prebuilt import create_react_agent

mlflow.langchain.autolog()

# Cmd 3: Create RAG Agent
retriever = VectorSearchRetrieverTool(
    index_name="main.docs.company_policies",
    tool_description="Search company policies and procedures"
)

llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

rag_agent = create_react_agent(
    model=llm,
    tools=[retriever],
    prompt="""You are an HR assistant. Use the search tool to find relevant policies
    before answering questions. Always cite the source document."""
)

# Cmd 4: Query
result = rag_agent.invoke({
    "messages": [{"role": "user", "content": "What is our remote work policy?"}]
})
print(result["messages"][-1].content)
```

### Pattern 3: Multi-Agent with Genie

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph databricks-langchain
dbutils.library.restartPython()

# Cmd 2: Imports
import mlflow
from databricks_langchain import ChatDatabricks
from databricks_langchain.genie import GenieAgent
from databricks_langchain.agent import create_supervisor

mlflow.langchain.autolog()

# Cmd 3: Create Agents
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

# Genie agent for structured data
sales_genie = GenieAgent(
    genie_space_id="your-genie-space-id",
    genie_agent_name="SalesAnalyst",
    description="Queries sales data, revenue metrics, and customer analytics"
)

# Cmd 4: Create Supervisor
supervisor = create_supervisor(
    agents=[sales_genie],
    model=llm,
    prompt="""You coordinate data analysis. Route questions about sales,
    revenue, and metrics to the SalesAnalyst agent.""",
    output_mode="full_history"
).compile()

# Cmd 5: Query
result = supervisor.invoke({
    "messages": [{"role": "user", "content": "What was our total revenue last quarter?"}]
})
print(result["messages"][-1].content)
```

### Pattern 4: Unity Catalog Tools

```python
# Cmd 1: Setup
%pip install -U mlflow[databricks] langgraph databricks-langchain unitycatalog-langchain[databricks]
dbutils.library.restartPython()

# Cmd 2: Create UC Function (run once)
spark.sql("""
CREATE OR REPLACE FUNCTION main.default.calculate_tax(amount DOUBLE, rate DOUBLE)
RETURNS DOUBLE
LANGUAGE PYTHON
AS $$
    return amount * rate
$$
""")

# Cmd 3: Create Agent with UC Tools
import mlflow
from databricks_langchain import ChatDatabricks, UCFunctionToolkit
from langgraph.prebuilt import create_react_agent

mlflow.langchain.autolog()

# Load tools from Unity Catalog
toolkit = UCFunctionToolkit(
    function_names=["main.default.calculate_tax"]
)

llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

agent = create_react_agent(
    model=llm,
    tools=toolkit.tools,
    prompt="You are a tax calculation assistant."
)

# Cmd 4: Test
result = agent.invoke({
    "messages": [{"role": "user", "content": "Calculate 8% tax on $1500"}]
})
print(result["messages"][-1].content)
```

### Pattern 5: Full Production Pipeline

```python
# Cmd 1: Setup
%pip install -U "mlflow[databricks]>=3.1" langgraph databricks-langchain databricks-agents
dbutils.library.restartPython()

# Cmd 2: Define Agent
import mlflow
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from databricks_langchain import ChatDatabricks

@tool
def get_order_status(order_id: str) -> str:
    """Get status of an order."""
    # In production, query Delta table
    return f"Order {order_id}: Shipped, arriving tomorrow"

def create_agent():
    llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
    return create_react_agent(llm, [get_order_status])

# Cmd 3: Log to MLflow
from mlflow.models.resources import DatabricksServingEndpoint

mlflow.langchain.autolog()
mlflow.set_experiment("/Shared/production-agent")

with mlflow.start_run():
    # Log the agent
    model_info = mlflow.langchain.log_model(
        lc_model=create_agent(),
        artifact_path="agent",
        pip_requirements=["langgraph", "databricks-langchain"],
        resources=[
            DatabricksServingEndpoint(endpoint_name="databricks-meta-llama-3-3-70b-instruct")
        ],
        registered_model_name="main.default.order_assistant"
    )

# Cmd 4: Deploy
from databricks import agents

deployment = agents.deploy(
    model_name="main.default.order_assistant",
    model_version=1,
    scale_to_zero=True
)

print(f"Deployed to: {deployment.endpoint_name}")

# Cmd 5: Test Endpoint
import requests

response = requests.post(
    f"{deployment.endpoint_url}/invocations",
    headers={"Authorization": f"Bearer {dbutils.secrets.get('scope', 'token')}"},
    json={"messages": [{"role": "user", "content": "Where is order ORD-123?"}]}
)
print(response.json())
```

---

## Sources

### Official Databricks Documentation
- [Tutorial: Build, evaluate, and deploy a retrieval agent](https://docs.databricks.com/aws/en/generative-ai/tutorials/agent-framework-notebook)
- [Author AI agents in code](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)
- [Tracing LangGraph](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/integrations/langgraph)
- [LangChain on Databricks](https://docs.databricks.com/aws/en/large-language-models/langchain)
- [Integrate LangChain with Unity Catalog tools](https://docs.databricks.com/aws/en/generative-ai/agent-framework/langchain-uc-integration)
- [Use Genie in multi-agent systems](https://docs.databricks.com/aws/en/generative-ai/agent-framework/multi-agent-genie)
- [Genie Conversation API](https://docs.databricks.com/aws/en/genie/conversation-api)
- [Build and trace retriever tools](https://docs.databricks.com/aws/en/generative-ai/agent-framework/unstructured-retrieval-tools)
- [Deploy an agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/deploy-agent)
- [Use Databricks managed MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp)
- [Use Agent Bricks: Multi-Agent Supervisor](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)

### LangChain/LangGraph Documentation
- [LangChain Databricks Integration](https://python.langchain.com/docs/integrations/providers/databricks/)
- [Databricks Unity Catalog Tools](https://python.langchain.com/docs/integrations/tools/databricks/)
- [Databricks Vector Search](https://python.langchain.com/docs/integrations/vectorstores/databricks_vector_search/)
- [Build a custom RAG agent with LangGraph](https://docs.langchain.com/oss/python/langgraph/agentic-rag)

### Databricks Blog Posts
- [Announcing Genie Conversation APIs](https://www.databricks.com/blog/genie-conversation-apis-public-preview)
- [Multi-Agent Supervisor Architecture](https://www.databricks.com/blog/multi-agent-supervisor-architecture-orchestrating-enterprise-ai-scale)
- [Reranking in Mosaic AI Vector Search](https://www.databricks.com/blog/reranking-mosaic-ai-vector-search-faster-smarter-retrieval-rag-agents)
- [Build Compound AI Systems with Mosaic AI](https://www.databricks.com/blog/build-compound-ai-systems-faster-databricks-mosaic-ai)

### MLflow Resources
- [LangGraph with Model From Code](https://mlflow.org/blog/langgraph-model-from-code)
- [MLflow Tracing Integrations](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/integrations/)

### Community Resources
- [Tracing and Evaluating LangGraph AI Agents with MLflow](https://www.advancinganalytics.co.uk/blog/tracing-and-evaluating-langgraph-ai-agents-with-mlflow)
- [Building Scalable Agent Systems with LangGraph](https://medium.com/predict/building-scalable-agent-systems-with-langgraph-best-practices-for-memory-streaming-durability-5eb360d162c3)
- [Build Enterprise Chatbots with Genie API, LangChain, and LangGraph](https://medium.com/@mvkally/build-enterprise-chatbots-in-databricks-using-genie-api-langchain-and-langgraph-11e137ac7dd1)
- [Augmenting Genie Space with Multi-Step Research](https://medium.com/@hiydavid/augmenting-your-genie-space-with-multi-step-research-e11324491076)

### API Documentation
- [Databricks AI Bridge Python API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html)

---

## Confidence Assessment

| Topic | Confidence | Notes |
|-------|------------|-------|
| Basic LangGraph in Notebooks | High | Well-documented with official tutorials |
| MLflow Tracing Integration | High | Official Databricks documentation |
| Genie Space API | High | Public Preview, documented APIs |
| Multi-Agent Patterns | High | Official examples and notebooks |
| Vector Search Integration | High | Production-ready with reranking |
| Unity Catalog Tools | High | Stable integration |
| Model Deployment | High | Mosaic AI Agent Framework GA |
| MCP Integration | Medium | Newer feature, evolving |
| State Management in Serving | Medium | Requires external state store design |

---

**Last Updated:** January 26, 2026
**LangGraph Version:** 1.0.x (released October 2025)
**MLflow Version:** 3.1+
**Databricks Runtime:** 13.3 LTS+ or Serverless
