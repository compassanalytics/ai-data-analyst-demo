"""Supervisor Agent - LangGraph multi-agent orchestration.

This module implements the supervisor agent that routes queries to
specialized subagents (Genie for data, RAG for documents) using LangGraph.
"""

from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from src.agents.genie_agent import GenieDataAgent, GenieResult
from src.agents.rag_agent import RAGAgent, RAGResult
from src.config import Config


class AgentState(TypedDict):
    """State for the supervisor agent graph.

    Attributes:
        messages: Conversation history
        next_agent: The next agent to route to (or END)
        genie_result: Latest result from Genie agent
        rag_result: Latest result from RAG agent
        iteration_count: Number of agent iterations (for safety limits)
    """

    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    genie_result: GenieResult | None
    rag_result: RAGResult | None
    iteration_count: int


def create_agent_tools(genie_agent: GenieDataAgent, rag_agent: RAGAgent):
    """Create LangChain tools that wrap the subagents.

    Args:
        genie_agent: The Genie data agent instance
        rag_agent: The RAG agent instance

    Returns:
        List of tools for the supervisor to use
    """

    @tool
    def query_data(question: str) -> str:
        """Query structured data using natural language. Use this for questions about
        metrics, sales, revenue, products, customers, trends, and any data analysis.

        Args:
            question: Natural language question about the data

        Returns:
            Data results formatted as a markdown table with the generated SQL
        """
        result = genie_agent.query(question)

        if not result.success:
            return f"Error querying data: {result.error}"

        output_parts = []

        if result.description:
            output_parts.append(f"**Analysis:** {result.description}\n")

        output_parts.append(result.to_markdown_table())

        if result.sql:
            output_parts.append(f"\n**Generated SQL:**\n```sql\n{result.sql}\n```")

        return "\n".join(output_parts)

    @tool
    def search_documents(question: str) -> str:
        """Search company documents and policies. Use this for questions about
        policies, procedures, documentation, guides, security, compliance,
        pricing, and other non-data questions.

        Args:
            question: Natural language question about documents/policies

        Returns:
            Answer based on retrieved documents with source citations
        """
        result = rag_agent.query(question)

        if not result.success:
            return f"Error searching documents: {result.error}"

        output_parts = [result.answer]

        if result.documents:
            output_parts.append("\n" + result.format_sources())

        return "\n".join(output_parts)

    return [query_data, search_documents]


def create_supervisor_agent(
    config: Config,
    genie_agent: GenieDataAgent | None = None,
    rag_agent: RAGAgent | None = None,
    checkpointer: MemorySaver | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create the supervisor agent graph.

    The supervisor uses ChatDatabricks to route queries to specialized agents:
    - Genie Agent: For structured data questions (metrics, SQL, analytics)
    - RAG Agent: For document/policy questions

    In mock_mode with no Databricks credentials, uses a simple rule-based router.

    Args:
        config: Configuration instance
        genie_agent: Optional pre-configured Genie agent
        rag_agent: Optional pre-configured RAG agent

    Returns:
        Compiled LangGraph StateGraph ready to invoke
    """
    # Initialize agents if not provided
    if genie_agent is None:
        genie_agent = GenieDataAgent(config)
    if rag_agent is None:
        rag_agent = RAGAgent(config)

    # Create tools
    tools = create_agent_tools(genie_agent, rag_agent)

    # Initialize the LLM with tools
    # In mock mode, use rule-based routing (no Databricks credentials needed)
    llm_with_tools = None
    use_mock_llm = config.mock_mode  # In mock mode, always use mock LLM routing

    if not use_mock_llm:
        from databricks_langchain import ChatDatabricks

        llm = ChatDatabricks(
            endpoint=config.model_endpoint,
            temperature=0.1,
        )
        llm_with_tools = llm.bind_tools(tools)

    # Keywords for routing in mock mode
    DATA_KEYWORDS = [
        "revenue",
        "sales",
        "product",
        "top",
        "bottom",
        "trend",
        "growth",
        "customer",
        "metric",
        "kpi",
        "data",
        "number",
        "count",
        "sum",
        "average",
        "total",
        "monthly",
        "quarterly",
        "yearly",
        "region",
        "segment",
        "analysis",
        "analyze",
        "report",
    ]
    DOC_KEYWORDS = [
        "policy",
        "document",
        "procedure",
        "guide",
        "how to",
        "security",
        "compliance",
        "pricing",
        "refund",
        "onboarding",
        "process",
        "rule",
    ]

    def mock_route_query(question: str) -> tuple[str, str]:
        """Simple rule-based routing for mock mode."""
        q_lower = question.lower()

        # Check for document-related keywords
        for kw in DOC_KEYWORDS:
            if kw in q_lower:
                return "search_documents", question

        # Default to data queries
        return "query_data", question

    # Define the supervisor node
    def supervisor_node(state: AgentState) -> dict[str, Any]:
        """The supervisor decides which tool to use or responds directly."""
        messages = state["messages"]
        iteration = state.get("iteration_count", 0)

        # Safety limit on iterations
        if iteration >= 5:
            return {
                "messages": [
                    AIMessage(
                        content="I've reached my iteration limit. Here's what I found so far based on our conversation."
                    )
                ],
                "next_agent": "end",
                "iteration_count": iteration,
            }

        # Get the last user message
        last_user_msg: str | None = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                content = msg.content
                last_user_msg = content if isinstance(content, str) else str(content)
                break

        if use_mock_llm:
            # Mock mode: use rule-based routing
            if last_user_msg and iteration == 0:
                tool_name, tool_arg = mock_route_query(last_user_msg)
                # Create a mock tool call response
                response = AIMessage(
                    content="",
                    tool_calls=[{"id": f"call_{iteration}", "name": tool_name, "args": {"question": tool_arg}}],
                )
                return {
                    "messages": [response],
                    "next_agent": "tools",
                    "iteration_count": iteration + 1,
                }
            else:
                # After tool execution, synthesize final response
                tool_results = []
                for msg in messages:
                    if hasattr(msg, "content") and isinstance(msg.content, str):
                        if "|" in msg.content or "Sources:" in msg.content:
                            tool_results.append(msg.content)

                final_content = "\n\n".join(tool_results) if tool_results else "I processed your request."
                return {
                    "messages": [AIMessage(content=f"Here's what I found:\n\n{final_content}")],
                    "next_agent": "end",
                    "iteration_count": iteration,
                }

        # Real mode: use LLM
        response = llm_with_tools.invoke(messages)

        # Check if tools were called
        if response.tool_calls:
            return {
                "messages": [response],
                "next_agent": "tools",
                "iteration_count": iteration + 1,
            }

        # No tools called - final response
        return {
            "messages": [response],
            "next_agent": "end",
            "iteration_count": iteration,
        }

    # Create the tool node
    tool_node = ToolNode(tools)

    # Define routing function
    def route_next(state: AgentState) -> Literal["tools", "supervisor", "__end__"]:
        """Route to the next node based on state."""
        next_agent = state.get("next_agent", "end")

        if next_agent == "tools":
            return "tools"
        elif next_agent == "supervisor":
            return "supervisor"
        else:
            return "__end__"

    # After tools, always go back to supervisor
    def after_tools(state: AgentState) -> dict[str, Any]:
        """Process after tool execution."""
        return {"next_agent": "supervisor"}

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("after_tools", after_tools)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Add edges
    workflow.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "tools": "tools",
            "supervisor": "supervisor",
            "__end__": END,
        },
    )
    workflow.add_edge("tools", "after_tools")
    workflow.add_edge("after_tools", "supervisor")

    # Compile and return with or without checkpointer
    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()


class SupervisorRunner:
    """High-level interface for running the supervisor agent.

    Provides a simple query interface that handles state management.

    Example:
        >>> config = Config(mock_mode=True)
        >>> runner = SupervisorRunner(config)
        >>> response = runner.query("What are our top products?")
        >>> print(response)
    """

    def __init__(
        self,
        config: Config,
        genie_agent: GenieDataAgent | None = None,
        rag_agent: RAGAgent | None = None,
        thread_id: str | None = None,
        checkpointer: MemorySaver | None = None,
    ):
        """Initialize the supervisor runner.

        Args:
            config: Configuration instance
            genie_agent: Optional pre-configured Genie agent
            rag_agent: Optional pre-configured RAG agent
            thread_id: Optional thread ID for checkpointer-based history
            checkpointer: Optional pre-configured checkpointer
        """
        self.config = config
        self.genie_agent = genie_agent or GenieDataAgent(config)
        self.rag_agent = rag_agent or RAGAgent(config)
        self._thread_id = thread_id

        # Create checkpointer if thread_id provided
        if checkpointer is not None:
            self._checkpointer = checkpointer
        elif thread_id is not None:
            self._checkpointer = MemorySaver()
        else:
            self._checkpointer = None

        self.graph = create_supervisor_agent(
            config,
            self.genie_agent,
            self.rag_agent,
            checkpointer=self._checkpointer,
        )
        self._message_history: list[BaseMessage] = []

    def query(self, question: str, reset_history: bool = False) -> str:
        """Query the supervisor agent.

        Args:
            question: Natural language question
            reset_history: Whether to reset conversation history

        Returns:
            The agent's response as a string
        """
        if reset_history:
            self._message_history = []

        user_message = HumanMessage(content=question)

        # Build initial state
        # When using checkpointer, don't pass full history - checkpointer manages it
        initial_state: AgentState
        if self._checkpointer and self._thread_id:
            initial_state = {
                "messages": [user_message],  # Only new message
                "next_agent": "supervisor",
                "genie_result": None,
                "rag_result": None,
                "iteration_count": 0,
            }
            invoke_config = {"configurable": {"thread_id": self._thread_id}}
        else:
            initial_state = {
                "messages": self._message_history + [user_message],
                "next_agent": "supervisor",
                "genie_result": None,
                "rag_result": None,
                "iteration_count": 0,
            }
            invoke_config = {}

        final_state = self.graph.invoke(initial_state, invoke_config)  # type: ignore[arg-type]

        # Update local history (for non-checkpointer mode)
        if not self._checkpointer:
            self._message_history = list(final_state["messages"])

        # Extract response
        for message in reversed(final_state["messages"]):
            if isinstance(message, AIMessage) and not message.tool_calls:
                content = message.content
                # Handle multimodal content
                if isinstance(content, str):
                    return content
                return str(content)

        return "I wasn't able to generate a response."

    @property
    def thread_id(self) -> str | None:
        """Get the current thread ID.

        Returns:
            The thread ID if using checkpointer, None otherwise
        """
        return self._thread_id

    def get_history(self) -> list[BaseMessage]:
        """Get the conversation history.

        Returns:
            List of messages in the conversation
        """
        return self._message_history.copy()

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._message_history = []
        self.genie_agent.reset_conversation()


def create_simple_supervisor(
    config: Config,
    thread_id: str | None = None,
) -> SupervisorRunner:
    """Factory function to create a ready-to-use supervisor.

    Args:
        config: Configuration instance
        thread_id: Optional thread ID for checkpointer-based history

    Returns:
        SupervisorRunner instance
    """
    return SupervisorRunner(config, thread_id=thread_id)
