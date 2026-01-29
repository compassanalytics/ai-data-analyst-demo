"""Workshop helper - Agent Builder package for hands-on LangGraph workshops.

This package provides a fluent API for building LangGraph agents,
designed to make it easy for workshop participants to experiment
with agent construction without deep framework knowledge.

Main Components:
    AgentBuilder: Fluent API for configuring and building agents
    AgentRunner: Interface for querying built agents
    WorkshopAgentState: TypedDict state for the agent graph

Pre-built Tools:
    calculator: Safe math evaluation (AST-based, no raw eval)
    date_helper: Date/time queries without external dependencies
    mock_web_search: Simulated search for testing

Utilities:
    TOOL_TEMPLATE: Template for creating custom tools

Example:
    >>> from src.workshop import AgentBuilder, calculator
    >>>
    >>> # Build a simple calculator agent
    >>> agent = (
    ...     AgentBuilder("Math Agent")
    ...     .set_system_prompt("You are a helpful math assistant.")
    ...     .add_tool("calculator", "Evaluate math", calculator.func)
    ...     .add_routing_rule(["calculate", "+", "-", "*", "/"], "calculator")
    ...     .build(mock_mode=True)
    ... )
    >>>
    >>> # Query the agent
    >>> result = agent.query("What is 15% of 200?")
    >>> print(result)  # Output: 30

For exercise solutions, see:
    >>> from src.workshop.solutions import test_all_solutions
    >>> test_all_solutions()
"""

from src.workshop.agent_builder import (
    AgentBuilder,
    AgentRunner,
    RoutingRule,
    WorkshopAgentState,
)
from src.workshop.tools import (
    TOOL_TEMPLATE,
    calculator,
    date_helper,
    mock_web_search,
)

__all__ = [
    # Core classes
    "AgentBuilder",
    "AgentRunner",
    "WorkshopAgentState",
    "RoutingRule",
    # Pre-built tools
    "calculator",
    "date_helper",
    "mock_web_search",
    # Utilities
    "TOOL_TEMPLATE",
]
