"""Supervisor Agent - LangGraph multi-agent orchestration.

This module implements an agentic supervisor that routes queries to
multiple Genie Spaces using a multi-tool approach. The agent can:
1. Discover available spaces (list_genie_spaces)
2. Query specific spaces by name (query_genie)
3. Perform calculations on results (calculator)

This demonstrates true agentic behavior: multi-step tool call sequences
with intermediate reasoning, rather than a single tool call per turn.
"""

from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from src.agents.genie_agent import GenieDataAgent, GenieResult
from src.agents.multi_genie_orchestrator import GenieSpaceConfig
from src.config import Config
from src.workshop.tools import calculator


class AgentState(TypedDict):
    """State for the supervisor agent graph.

    Attributes:
        messages: Conversation history (tool results flow through messages)
        next_agent: The next agent to route to (or END)
        iteration_count: Number of agent iterations (for safety limits)
    """

    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    iteration_count: int


def _build_space_configs_from_config(config: Config) -> list[GenieSpaceConfig]:
    """Build a single-space config list from a Config with genie_space_id."""
    return [
        GenieSpaceConfig(
            space_id=config.genie_space_id,
            name="Data",
            domain="general data analysis",
        )
    ]


def create_agent_tools(config: Config, space_configs: list[GenieSpaceConfig]):
    """Create LangChain tools for the multi-space supervisor.

    Creates three tools:
    - list_genie_spaces: Discover available spaces and their domains
    - query_genie: Query a specific space by name
    - calculator: Math on results (imported from src.workshop.tools)

    Args:
        config: Configuration instance
        space_configs: List of Genie Space configurations

    Returns:
        Tuple of (tools list, agents dict) — agents dict for internal use
    """
    # Build one GenieDataAgent per space (lazy, same pattern as MultiGenieOrchestrator)
    agents: dict[str, GenieDataAgent] = {}

    def _get_agent(space_config: GenieSpaceConfig) -> GenieDataAgent:
        if space_config.name not in agents:
            agent_config = Config(
                databricks_host=config.databricks_host,
                databricks_token=config.databricks_token,
                genie_space_id=space_config.space_id,
                warehouse_id=config.warehouse_id,
                model_endpoint=config.model_endpoint,
                mock_mode=config.mock_mode,
                vector_search_endpoint=config.vector_search_endpoint,
                vector_search_index=config.vector_search_index,
                embedding_endpoint=config.embedding_endpoint,
                cache_enabled=config.cache_enabled,
                cache_ttl_seconds=config.cache_ttl_seconds,
                demo_mode=config.demo_mode,
                cache_max_size=config.cache_max_size,
            )
            agents[space_config.name] = GenieDataAgent(agent_config)
        return agents[space_config.name]

    # Build lookup for case-insensitive space name matching
    space_lookup: dict[str, GenieSpaceConfig] = {sc.name.lower(): sc for sc in space_configs}

    @tool
    def list_genie_spaces() -> str:
        """List all available Genie Spaces and their data domains.

        Call this first to discover which spaces are available before querying.

        Returns:
            Formatted list of space names and their domains
        """
        lines = ["**Available Genie Spaces:**\n"]
        for sc in space_configs:
            lines.append(f"- **{sc.name}**: {sc.domain}")
        return "\n".join(lines)

    @tool
    def query_genie(space_name: str, question: str) -> str:
        """Query a specific Genie Space by name.

        Use list_genie_spaces first to see available spaces.

        Args:
            space_name: Name of the Genie Space to query (case-insensitive)
            question: Natural language question about the data

        Returns:
            Data results as a markdown table with generated SQL, or error message
        """
        sc = space_lookup.get(space_name.lower())
        if sc is None:
            available = ", ".join(s.name for s in space_configs)
            return f"Error: Unknown space '{space_name}'. Available spaces: {available}"

        agent = _get_agent(sc)
        result: GenieResult = agent.query(question)

        if not result.success:
            return f"Error querying {sc.name}: {result.error}"

        output_parts = []
        if result.description:
            output_parts.append(f"**Analysis:** {result.description}\n")
        output_parts.append(result.to_markdown_table())
        if result.sql:
            output_parts.append(f"\n**Generated SQL:**\n```sql\n{result.sql}\n```")
        return "\n".join(output_parts)

    return [list_genie_spaces, query_genie, calculator], agents


def _mock_plan_tool_calls(
    question: str,
    space_configs: list[GenieSpaceConfig],
) -> list[dict[str, Any]]:
    """Plan a deterministic sequence of tool calls for mock mode.

    Matches question keywords against each space's domain to decide which
    spaces to query, then builds the call sequence.

    Args:
        question: The user's question
        space_configs: Available space configurations

    Returns:
        List of tool call dicts: {"name": str, "args": dict}
    """
    q_lower = question.lower()
    calls: list[dict[str, Any]] = []

    # Always start with list_genie_spaces
    calls.append({"name": "list_genie_spaces", "args": {}})

    # Match question words against each space's domain keywords (bidirectional)
    q_words = q_lower.split()
    matched_spaces: list[GenieSpaceConfig] = []
    for sc in space_configs:
        domain_keywords = [kw.strip().lower() for kw in sc.domain.split(",")]
        # Check if any domain keyword appears in the question OR
        # any question word starts with a domain keyword (or vice versa)
        if any(kw in q_lower or any(w.startswith(kw) or kw.startswith(w) for w in q_words) for kw in domain_keywords):
            matched_spaces.append(sc)

    # If no match, default to first space
    if not matched_spaces:
        matched_spaces = [space_configs[0]]

    # Add a query_genie call per matched space
    for sc in matched_spaces:
        calls.append(
            {
                "name": "query_genie",
                "args": {"space_name": sc.name, "question": question},
            }
        )

    # Add calculator if math keywords present
    math_keywords = [
        "calculate",
        "compute",
        "ratio",
        "percentage",
        "percent",
        "average",
        "sum",
        "difference",
        "compare",
        "growth",
        "margin",
    ]
    if any(kw in q_lower for kw in math_keywords):
        calls.append(
            {
                "name": "calculator",
                "args": {"expression": "100 * 1.15"},  # placeholder demo calculation
            }
        )

    return calls


def create_supervisor_agent(
    config: Config,
    space_configs: list[GenieSpaceConfig] | None = None,
    checkpointer: MemorySaver | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create the supervisor agent graph.

    The supervisor uses an LLM (or mock routing) to drive a multi-step
    tool-calling loop across multiple Genie Spaces.

    Args:
        config: Configuration instance
        space_configs: List of Genie Space configurations. Falls back to
            a single space from config.genie_space_id if not provided.
        checkpointer: Optional LangGraph checkpointer for stateful threads

    Returns:
        Compiled LangGraph StateGraph ready to invoke
    """
    if space_configs is None:
        space_configs = _build_space_configs_from_config(config)

    # Create tools
    tools, _agents = create_agent_tools(config, space_configs)

    # Initialize the LLM with tools
    llm_with_tools = None
    use_mock_llm = config.mock_mode

    if not use_mock_llm:
        from databricks_langchain import ChatDatabricks

        llm = ChatDatabricks(
            endpoint=config.model_endpoint,
            temperature=0.1,
        )
        llm_with_tools = llm.bind_tools(tools)

    # Define the supervisor node
    def supervisor_node(state: AgentState) -> dict[str, Any]:
        """The supervisor decides which tool to use or responds directly."""
        messages = state["messages"]
        iteration = state.get("iteration_count", 0)

        # Safety limit on iterations (raised to 10 for multi-step sequences)
        if iteration >= 10:
            return {
                "messages": [
                    AIMessage(
                        content="I've reached my iteration limit. Here's what I found so far based on our conversation."
                    )
                ],
                "next_agent": "end",
                "iteration_count": iteration,
            }

        # Get the original user message (first HumanMessage in this turn)
        original_question: str | None = None
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content
                original_question = content if isinstance(content, str) else str(content)
                break

        if use_mock_llm:
            # Mock mode: deterministic multi-step tool calling
            # Build the plan from the original question
            plan = _mock_plan_tool_calls(original_question or "", space_configs)

            # Count completed ToolMessages to know where we are in the plan
            completed_tool_calls = sum(1 for msg in messages if isinstance(msg, ToolMessage))

            if completed_tool_calls < len(plan):
                # Execute the next planned call
                next_call = plan[completed_tool_calls]
                response = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": f"call_{iteration}",
                            "name": next_call["name"],
                            "args": next_call["args"],
                        }
                    ],
                )
                return {
                    "messages": [response],
                    "next_agent": "tools",
                    "iteration_count": iteration + 1,
                }
            else:
                # All planned calls done — synthesize final response
                tool_results = []
                for msg in messages:
                    if isinstance(msg, ToolMessage):
                        tool_name = getattr(msg, "name", "unknown")
                        tool_results.append(f"### {tool_name}\n{msg.content}")

                combined = "\n\n".join(tool_results) if tool_results else "I processed your request."
                return {
                    "messages": [AIMessage(content=f"Here's what I found:\n\n{combined}")],
                    "next_agent": "end",
                    "iteration_count": iteration,
                }

        # Real mode: use LLM with system prompt describing the multi-tool workflow
        system_messages: list[BaseMessage] = []
        if iteration == 0:
            from langchain_core.messages import SystemMessage

            space_list = ", ".join(f"{sc.name} ({sc.domain})" for sc in space_configs)
            system_messages = [
                SystemMessage(
                    content=(
                        "You are a data analyst assistant with access to multiple Genie Spaces. "
                        "Follow this workflow:\n"
                        "1. Call list_genie_spaces to see available data domains\n"
                        "2. Call query_genie for each relevant space\n"
                        "3. Use calculator if you need to compute ratios, percentages, or comparisons\n"
                        "4. Synthesize results into a clear response\n\n"
                        f"Available spaces: {space_list}\n\n"
                        "Always query the most relevant spaces for the question. "
                        "For cross-domain questions, query multiple spaces."
                    )
                )
            ]

        # Real mode: use LLM (with retry for malformed model responses)
        max_retries = 2
        last_error = None
        augmented_messages = system_messages + list(messages)
        for attempt in range(max_retries):
            try:
                response = llm_with_tools.invoke(augmented_messages)

                if response.tool_calls:
                    return {
                        "messages": [response],
                        "next_agent": "tools",
                        "iteration_count": iteration + 1,
                    }

                return {
                    "messages": [response],
                    "next_agent": "end",
                    "iteration_count": iteration,
                }
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    continue

        return {
            "messages": [
                AIMessage(
                    content=f"The model produced an invalid response after {max_retries} attempts. "
                    f"Try rephrasing your question. Error: {last_error}"
                )
            ],
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
        space_configs: list[GenieSpaceConfig] | None = None,
        thread_id: str | None = None,
        checkpointer: MemorySaver | None = None,
    ):
        """Initialize the supervisor runner.

        Args:
            config: Configuration instance
            space_configs: Optional list of Genie Space configurations.
                Falls back to a single space from config.genie_space_id.
            thread_id: Optional thread ID for checkpointer-based history
            checkpointer: Optional pre-configured checkpointer
        """
        self.config = config
        self._thread_id = thread_id

        # Create checkpointer if thread_id provided
        if checkpointer is not None:
            self._checkpointer = checkpointer
        elif thread_id is not None:
            self._checkpointer = MemorySaver()
        else:
            self._checkpointer = None

        self.verbose = False

        self.graph = create_supervisor_agent(
            config,
            space_configs=space_configs,
            checkpointer=self._checkpointer,
        )
        self._message_history: list[BaseMessage] = []

    def query(self, question: str, reset_history: bool = False, verbose: bool = False) -> str:
        """Query the supervisor agent.

        Args:
            question: Natural language question
            reset_history: Whether to reset conversation history
            verbose: Whether to print raw tool outputs before the final response

        Returns:
            The agent's response as a string
        """
        if reset_history:
            self._message_history = []

        user_message = HumanMessage(content=question)

        # Build initial state
        initial_state: AgentState
        if self._checkpointer and self._thread_id:
            initial_state = {
                "messages": [user_message],
                "next_agent": "supervisor",
                "iteration_count": 0,
            }
            invoke_config = {"configurable": {"thread_id": self._thread_id}}
        else:
            initial_state = {
                "messages": self._message_history + [user_message],
                "next_agent": "supervisor",
                "iteration_count": 0,
            }
            invoke_config = {}

        final_state = self.graph.invoke(initial_state, invoke_config)  # type: ignore[arg-type]

        # Update local history (for non-checkpointer mode)
        if not self._checkpointer:
            self._message_history = list(final_state["messages"])

        # Print raw tool outputs when verbose is enabled
        if verbose or self.verbose:
            for message in final_state["messages"]:
                if isinstance(message, ToolMessage):
                    tool_name = getattr(message, "name", "unknown")
                    print(f"--- Raw Tool Output ({tool_name}) ---")
                    print(message.content)
                    print("-" * 60)

        # Extract response
        for message in reversed(final_state["messages"]):
            if isinstance(message, AIMessage) and not message.tool_calls:
                content = message.content
                if isinstance(content, str):
                    return content
                return str(content)

        return "I wasn't able to generate a response."

    @property
    def thread_id(self) -> str | None:
        """Get the current thread ID."""
        return self._thread_id

    def get_history(self) -> list[BaseMessage]:
        """Get the conversation history."""
        return self._message_history.copy()

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._message_history = []


def create_simple_supervisor(
    config: Config,
    space_configs: list[GenieSpaceConfig] | None = None,
    thread_id: str | None = None,
) -> SupervisorRunner:
    """Factory function to create a ready-to-use supervisor.

    Args:
        config: Configuration instance
        space_configs: Optional list of Genie Space configurations
        thread_id: Optional thread ID for checkpointer-based history

    Returns:
        SupervisorRunner instance
    """
    return SupervisorRunner(config, space_configs=space_configs, thread_id=thread_id)
