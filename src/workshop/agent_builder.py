"""Workshop helper - AgentBuilder for hands-on LangGraph agent building.

This module provides a fluent API that wraps LangGraph complexity,
making it easier for workshop participants to build and experiment
with AI agents without deep framework knowledge.

The AgentBuilder supports:
    - Adding custom tools with the @tool decorator
    - Rule-based routing for mock mode testing
    - Memory/persistence via LangGraph checkpointer
    - Iteration safety limits
    - Both mock and real LLM modes

Example:
    >>> from src.workshop import AgentBuilder, calculator
    >>> agent = (
    ...     AgentBuilder("Math Agent")
    ...     .set_system_prompt("You are a helpful math assistant.")
    ...     .add_tool("calculator", "Evaluate math expressions", calculator.func)
    ...     .add_routing_rule(["calculate", "math", "+", "-", "*"], "calculator")
    ...     .build(mock_mode=True)
    ... )
    >>> agent.query("What is 2 + 2?")
    '4'
"""

from __future__ import annotations

import operator
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode


class WorkshopAgentState(TypedDict):
    """State for the workshop agent graph.

    This state is passed through the LangGraph nodes and edges,
    accumulating messages and tracking routing decisions.

    Attributes:
        messages: Conversation history (uses operator.add for accumulation)
        next_step: The next node to route to ("tools", "agent", or "end")
        iteration_count: Safety counter to prevent infinite loops
    """

    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_step: str
    iteration_count: int


@dataclass
class RoutingRule:
    """Rule for keyword-based routing to tools in mock mode.

    Routing rules allow the agent to direct queries to specific tools
    based on keyword matching, useful for testing without LLM calls.

    Attributes:
        keywords: List of keywords that trigger this rule
        tool_name: Name of the tool to route to when matched
        priority: Higher priority rules are checked first (default: 0)

    Example:
        >>> rule = RoutingRule(
        ...     keywords=["weather", "temperature"],
        ...     tool_name="weather_tool",
        ...     priority=1
        ... )
        >>> rule.matches("What's the weather today?")
        True
    """

    keywords: list[str]
    tool_name: str
    priority: int = 0

    def matches(self, text: str) -> bool:
        """Check if the text matches any of this rule's keywords.

        Args:
            text: Input text to check for keyword matches

        Returns:
            True if any keyword is found in the text (case-insensitive)
        """
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.keywords)


class AgentRunner:
    """High-level interface for running a built agent.

    Provides a simple query interface that handles state management
    and conversation history. Supports both checkpointer-based and
    local history modes.

    Attributes:
        graph: The compiled LangGraph StateGraph
        thread_id: Thread ID for checkpointer-based history
        name: Display name for the agent

    Example:
        >>> runner = agent_builder.build()
        >>> response = runner.query("Hello!")
        >>> print(response)
        >>> history = runner.get_history()
    """

    def __init__(
        self,
        graph: CompiledStateGraph[Any, Any, Any, Any],
        thread_id: str | None = None,
        name: str = "Agent",
        checkpointer: MemorySaver | None = None,
    ):
        """Initialize the agent runner.

        Args:
            graph: Compiled LangGraph StateGraph
            thread_id: Optional thread ID for checkpointer-based history
            name: Display name for the agent
            checkpointer: Optional checkpointer for persistence
        """
        self.graph = graph
        self.thread_id = thread_id
        self.name = name
        self._checkpointer = checkpointer
        self._message_history: list[BaseMessage] = []

    def query(self, question: str, reset_history: bool = False) -> str:
        """Query the agent with a question.

        Args:
            question: Natural language question to ask the agent
            reset_history: If True, clears conversation history before query

        Returns:
            The agent's response as a string
        """
        if reset_history:
            self._message_history = []

        user_message = HumanMessage(content=question)

        # Build initial state
        # When using checkpointer, don't accumulate local history
        initial_state: WorkshopAgentState
        if self._checkpointer and self.thread_id:
            initial_state = {
                "messages": [user_message],
                "next_step": "agent",
                "iteration_count": 0,
            }
            invoke_config = {"configurable": {"thread_id": self.thread_id}}
        else:
            initial_state = {
                "messages": self._message_history + [user_message],
                "next_step": "agent",
                "iteration_count": 0,
            }
            invoke_config = {}

        # Invoke the graph (compiled graph has invoke method)
        final_state = self.graph.invoke(initial_state, invoke_config)  # type: ignore[arg-type]

        # Update local history only when not using checkpointer
        if not self._checkpointer:
            self._message_history = list(final_state["messages"])

        # Extract the final response
        for message in reversed(final_state["messages"]):
            if isinstance(message, AIMessage) and not message.tool_calls:
                content = message.content
                # Handle multimodal content (text + images)
                if isinstance(content, str):
                    return content
                return str(content)

        return "I wasn't able to generate a response."

    def get_history(self) -> list[BaseMessage]:
        """Get the conversation history.

        Returns:
            Copy of the message history list
        """
        return self._message_history.copy()

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._message_history = []


class AgentBuilder:
    """Fluent API for building LangGraph agents.

    AgentBuilder wraps LangGraph complexity, providing a chainable
    interface for configuring and building AI agents. Supports both
    mock mode (for testing without credentials) and real LLM mode.

    Example:
        >>> agent = (
        ...     AgentBuilder("My Assistant")
        ...     .set_system_prompt("You are a helpful assistant.")
        ...     .add_tool("calculator", "Do math", calculator.func)
        ...     .add_routing_rule(["math", "calculate"], "calculator")
        ...     .enable_memory("session-1")
        ...     .set_max_iterations(10)
        ...     .build(mock_mode=True)
        ... )
        >>> agent.query("What is 2+2?")
        '4'
    """

    def __init__(
        self,
        name: str = "My Agent",
        model_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
    ):
        """Initialize the AgentBuilder.

        Args:
            name: Display name for the agent
            model_endpoint: Databricks model endpoint for real LLM mode
        """
        self.name = name
        self.model_endpoint = model_endpoint
        self._system_prompt: str | None = None
        self._tools: list[StructuredTool] = []
        self._tool_map: dict[str, Callable] = {}
        self._routing_rules: list[RoutingRule] = []
        self._memory_enabled: bool = False
        self._thread_id: str = "default"
        self._max_iterations: int = 5
        self._graph: StateGraph | None = None

    def set_system_prompt(self, prompt: str) -> AgentBuilder:
        """Set the system prompt for the agent.

        The system prompt provides instructions and context for the LLM,
        defining the agent's personality and behavior.

        Args:
            prompt: System prompt text

        Returns:
            Self for method chaining

        Example:
            >>> builder.set_system_prompt("You are a helpful math tutor.")
        """
        self._system_prompt = prompt
        return self

    def add_tool(
        self,
        name: str,
        description: str,
        function: Callable,
        args_schema: Any | None = None,
    ) -> AgentBuilder:
        """Add a tool to the agent.

        Tools are functions the agent can call to perform actions or
        retrieve information. In mock mode, tools are invoked via
        routing rules. In real mode, the LLM decides when to use them.

        Args:
            name: Unique identifier for the tool
            description: Description for the LLM (what the tool does)
            function: The callable to execute when the tool is invoked
            args_schema: Optional Pydantic schema for structured arguments

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_tool(
            ...     name="calculator",
            ...     description="Evaluate mathematical expressions",
            ...     function=calculator.func
            ... )
        """
        structured_tool = StructuredTool.from_function(
            func=function,
            name=name,
            description=description,
            args_schema=args_schema,
        )
        self._tools.append(structured_tool)
        self._tool_map[name] = function
        return self

    def add_routing_rule(
        self,
        keywords: list[str],
        tool_name: str,
        priority: int = 0,
    ) -> AgentBuilder:
        """Add a routing rule for mock mode.

        Routing rules enable keyword-based tool selection without
        requiring an LLM. Higher priority rules are checked first.

        Args:
            keywords: List of keywords that trigger this tool
            tool_name: Name of the tool to route to (must match add_tool name)
            priority: Higher values are checked first (default: 0)

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_routing_rule(
            ...     keywords=["calculate", "math", "+", "-"],
            ...     tool_name="calculator",
            ...     priority=1
            ... )
        """
        rule = RoutingRule(keywords=keywords, tool_name=tool_name, priority=priority)
        self._routing_rules.append(rule)
        # Sort by priority (highest first)
        self._routing_rules.sort(key=lambda r: r.priority, reverse=True)
        return self

    def enable_memory(self, thread_id: str = "default") -> AgentBuilder:
        """Enable conversation memory/persistence.

        When memory is enabled, the agent maintains conversation history
        across multiple queries using LangGraph's checkpointer.

        Args:
            thread_id: Unique identifier for the conversation thread

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_memory("user-session-123")
        """
        self._memory_enabled = True
        self._thread_id = thread_id
        return self

    def set_max_iterations(self, max_iterations: int) -> AgentBuilder:
        """Set the maximum number of agent iterations.

        This safety limit prevents infinite loops in the agent graph.
        Default is 5 iterations.

        Args:
            max_iterations: Maximum number of iterations (must be > 0)

        Returns:
            Self for method chaining

        Example:
            >>> builder.set_max_iterations(10)
        """
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        self._max_iterations = max_iterations
        return self

    def _build_graph(self, mock_mode: bool) -> StateGraph:
        """Build the LangGraph StateGraph.

        Creates the agent graph with nodes for the agent logic, tools,
        and routing. Supports both mock mode (keyword routing) and
        real mode (LLM-based routing).

        Args:
            mock_mode: If True, use keyword-based routing instead of LLM

        Returns:
            Compiled StateGraph ready for invocation
        """
        tools = self._tools
        tool_map = self._tool_map
        routing_rules = self._routing_rules
        max_iterations = self._max_iterations
        system_prompt = self._system_prompt
        # Store reference for use in closures
        infer_tool_args = self._infer_tool_args

        # Initialize LLM if not in mock mode
        llm_with_tools = None
        if not mock_mode:
            try:
                from databricks_langchain import ChatDatabricks

                llm = ChatDatabricks(
                    endpoint=self.model_endpoint,
                    temperature=0.1,
                )
                if tools:
                    llm_with_tools = llm.bind_tools(tools)
                else:
                    llm_with_tools = llm
            except ImportError:
                raise ImportError(
                    "databricks-langchain is required for real mode. Install with: pip install databricks-langchain"
                )

        def mock_route_query(question: str) -> tuple[str | None, dict[str, Any]]:
            """Route query to a tool based on keywords (mock mode).

            Args:
                question: The user's question

            Returns:
                Tuple of (tool_name, tool_args) or (None, {}) if no match
            """
            for rule in routing_rules:
                if rule.matches(question):
                    return rule.tool_name, {"input_param": question}
            return None, {}

        def agent_node(state: WorkshopAgentState) -> dict[str, Any]:
            """Main agent node - decides whether to use tools or respond."""
            messages = state["messages"]
            iteration = state.get("iteration_count", 0)

            # Safety limit on iterations
            if iteration >= max_iterations:
                print(f"[AgentBuilder] Max iterations ({max_iterations}) reached")
                return {
                    "messages": [AIMessage(content="I've reached my iteration limit. Here's what I found so far.")],
                    "next_step": "end",
                    "iteration_count": iteration,
                }

            # Get the last user message
            last_user_msg: str | None = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    content = msg.content
                    last_user_msg = content if isinstance(content, str) else str(content)
                    break

            if mock_mode:
                # Mock mode: use rule-based routing
                if last_user_msg and iteration == 0:
                    tool_name, tool_args = mock_route_query(last_user_msg)

                    if tool_name and tool_name in tool_map:
                        print(f"[AgentBuilder] Routing to: {tool_name}")
                        # Infer the correct argument name for this tool
                        tool_args = infer_tool_args(tool_name, last_user_msg)
                        # Create a mock tool call
                        response = AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": f"call_{uuid.uuid4().hex[:8]}",
                                    "name": tool_name,
                                    "args": tool_args,
                                }
                            ],
                        )
                        return {
                            "messages": [response],
                            "next_step": "tools",
                            "iteration_count": iteration + 1,
                        }
                    else:
                        # No matching tool, respond directly
                        print("[AgentBuilder] Routing to: direct response (no matching rule)")
                        return {
                            "messages": [
                                AIMessage(
                                    content=f"I received your message: '{last_user_msg}'. "
                                    "I don't have a specific tool configured for this query."
                                )
                            ],
                            "next_step": "end",
                            "iteration_count": iteration,
                        }
                else:
                    # After tool execution, synthesize response
                    tool_results: list[str] = []
                    for msg in messages:
                        if isinstance(msg, ToolMessage):
                            content = msg.content
                            tool_results.append(content if isinstance(content, str) else str(content))

                    if tool_results:
                        final_content = "\n".join(tool_results)
                        return {
                            "messages": [AIMessage(content=final_content)],
                            "next_step": "end",
                            "iteration_count": iteration,
                        }
                    else:
                        return {
                            "messages": [AIMessage(content="I processed your request.")],
                            "next_step": "end",
                            "iteration_count": iteration,
                        }
            else:
                # Real mode: use LLM
                # Prepend system message if configured
                invoke_messages = messages
                if system_prompt:
                    from langchain_core.messages import SystemMessage

                    invoke_messages = [SystemMessage(content=system_prompt)] + list(messages)

                response = llm_with_tools.invoke(invoke_messages)

                if response.tool_calls:
                    tool_name = response.tool_calls[0]["name"] if response.tool_calls else "unknown"
                    print(f"[AgentBuilder] Routing to: {tool_name}")
                    return {
                        "messages": [response],
                        "next_step": "tools",
                        "iteration_count": iteration + 1,
                    }

                return {
                    "messages": [response],
                    "next_step": "end",
                    "iteration_count": iteration,
                }

        # Create tool node
        tool_node = ToolNode(tools) if tools else None

        def route_next(
            state: WorkshopAgentState,
        ) -> Literal["tools", "agent", "__end__"]:
            """Route to the next node based on state."""
            next_step = state.get("next_step", "end")

            if next_step == "tools":
                return "tools"
            elif next_step == "agent":
                return "agent"
            else:
                return "__end__"

        def after_tools(state: WorkshopAgentState) -> dict[str, Any]:
            """Process after tool execution - route back to agent."""
            return {"next_step": "agent"}

        # Build the graph
        workflow = StateGraph(WorkshopAgentState)

        # Add nodes
        workflow.add_node("agent", agent_node)
        if tool_node:
            workflow.add_node("tools", tool_node)
            workflow.add_node("after_tools", after_tools)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add edges
        if tool_node:
            workflow.add_conditional_edges(
                "agent",
                route_next,
                {
                    "tools": "tools",
                    "agent": "agent",
                    "__end__": END,
                },
            )
            workflow.add_edge("tools", "after_tools")
            workflow.add_edge("after_tools", "agent")
        else:
            # No tools, just route to end
            workflow.add_conditional_edges(
                "agent",
                route_next,
                {
                    "agent": "agent",
                    "__end__": END,
                },
            )

        return workflow

    def _infer_tool_args(self, tool_name: str, user_input: str) -> dict[str, Any]:
        """Infer tool arguments from user input.

        Attempts to match user input to the tool's expected parameters.

        Args:
            tool_name: Name of the tool
            user_input: The user's query

        Returns:
            Dictionary of inferred arguments
        """
        # Find the tool
        for tool in self._tools:
            if tool.name == tool_name:
                # Get the first argument name from the schema
                if tool.args_schema:
                    # args_schema can be a Pydantic model class or a dict
                    if hasattr(tool.args_schema, "schema"):
                        schema = tool.args_schema.schema()  # type: ignore[union-attr]
                    else:
                        schema = tool.args_schema  # Already a dict
                    props = schema.get("properties", {})
                    if props:
                        first_arg = list(props.keys())[0]
                        return {first_arg: user_input}

                # Fallback: check function signature
                func = self._tool_map.get(tool_name)
                if func:
                    import inspect

                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    if params:
                        return {params[0]: user_input}

        # Default fallback
        return {"query": user_input}

    def build(self, mock_mode: bool = True) -> AgentRunner:
        """Build and return the agent runner.

        Compiles the LangGraph and returns an AgentRunner instance
        ready for querying.

        Args:
            mock_mode: If True, use keyword-based routing (no credentials needed).
                      If False, use Databricks LLM for intelligent routing.

        Returns:
            AgentRunner instance ready for queries

        Example:
            >>> runner = builder.build(mock_mode=True)
            >>> response = runner.query("What is 2+2?")
        """
        workflow = self._build_graph(mock_mode)

        # Set up checkpointer if memory is enabled
        checkpointer = None
        if self._memory_enabled:
            checkpointer = MemorySaver()
            compiled = workflow.compile(checkpointer=checkpointer)
        else:
            compiled = workflow.compile()

        self._graph = workflow

        return AgentRunner(
            graph=compiled,
            thread_id=self._thread_id if self._memory_enabled else None,
            name=self.name,
            checkpointer=checkpointer,
        )

    def get_graph(self) -> StateGraph | None:
        """Get the underlying StateGraph (available after build).

        Returns:
            The StateGraph if build() has been called, None otherwise
        """
        return self._graph


__all__ = [
    "WorkshopAgentState",
    "RoutingRule",
    "AgentRunner",
    "AgentBuilder",
]
