"""Workshop helper - Reference solutions for Agent Builder exercises.

This module contains reference implementations for all workshop exercises.
These solutions demonstrate best practices and can be used for verification.

SPOILER ALERT: If you're working through the workshop exercises,
try to complete them yourself before looking at these solutions!

Usage:
    >>> from src.workshop.solutions import test_all_solutions
    >>> test_all_solutions()  # Quick verification of all exercises
"""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.tools import tool

from src.workshop.agent_builder import AgentBuilder, AgentRunner
from src.workshop.tools import calculator, date_helper, mock_web_search


def _get_tool_func(tool_obj: Any) -> Callable[..., str]:
    """Extract the underlying function from a LangChain tool.

    LangChain's @tool decorator wraps functions in StructuredTool objects.
    This helper safely extracts the underlying callable.

    Args:
        tool_obj: A @tool decorated function or StructuredTool

    Returns:
        The underlying callable function
    """
    if hasattr(tool_obj, "func"):
        return tool_obj.func  # type: ignore[return-value]
    return tool_obj  # Already a plain function


def exercise_1_solution() -> AgentRunner:
    """Exercise 1: Add a calculator tool to an agent.

    This exercise demonstrates the basics of:
    - Creating an AgentBuilder instance
    - Adding a pre-built tool
    - Setting up routing rules for mock mode
    - Building and querying the agent

    Returns:
        Configured AgentRunner ready for math queries

    Example:
        >>> agent = exercise_1_solution()
        >>> result = agent.query("What is 25 * 4?")
        >>> print(result)  # Should output: 100
    """
    agent = (
        AgentBuilder("Calculator Agent")
        .set_system_prompt(
            "You are a helpful math assistant. Use the calculator tool "
            "for any mathematical calculations."
        )
        .add_tool(
            name="calculator",
            description="Evaluate mathematical expressions. Supports basic "
            "arithmetic (+, -, *, /), percentages (15% of 250), and "
            "functions (sqrt, abs, round).",
            function=_get_tool_func(calculator),
        )
        .add_routing_rule(
            keywords=[
                "calculate",
                "math",
                "what is",
                "+",
                "-",
                "*",
                "/",
                "plus",
                "minus",
                "times",
                "divided",
                "percent",
                "sqrt",
                "square root",
            ],
            tool_name="calculator",
            priority=1,
        )
        .build(mock_mode=True)
    )

    return agent


def exercise_2_solution() -> AgentRunner:
    """Exercise 2: Add a custom date helper with routing rules.

    This exercise demonstrates:
    - Adding multiple tools to an agent
    - Setting up priority-based routing rules
    - Handling different types of queries

    Returns:
        Configured AgentRunner with both calculator and date tools

    Example:
        >>> agent = exercise_2_solution()
        >>> result = agent.query("What day is today?")
        >>> print(result)  # Shows current date
        >>> result = agent.query("What is 2 + 2?")
        >>> print(result)  # Shows: 4
    """
    agent = (
        AgentBuilder("Assistant Agent")
        .set_system_prompt(
            "You are a helpful assistant that can do math calculations "
            "and answer questions about dates and times."
        )
        # Add calculator tool
        .add_tool(
            name="calculator",
            description="Evaluate mathematical expressions.",
            function=_get_tool_func(calculator),
        )
        # Add date helper tool
        .add_tool(
            name="date_helper",
            description="Answer questions about dates and times.",
            function=_get_tool_func(date_helper),
        )
        # Date queries have higher priority
        .add_routing_rule(
            keywords=[
                "today",
                "tomorrow",
                "yesterday",
                "date",
                "time",
                "day",
                "christmas",
                "new year",
                "week",
                "month",
                "year",
            ],
            tool_name="date_helper",
            priority=2,  # Higher priority
        )
        # Math queries
        .add_routing_rule(
            keywords=[
                "calculate",
                "math",
                "what is",
                "+",
                "-",
                "*",
                "/",
                "plus",
                "minus",
                "times",
                "divided",
                "percent",
            ],
            tool_name="calculator",
            priority=1,
        )
        .build(mock_mode=True)
    )

    return agent


def exercise_3_solution() -> AgentRunner:
    """Exercise 3: Build a memory-enabled agent.

    This exercise demonstrates:
    - Enabling conversation memory
    - Using thread IDs for session management
    - Maintaining context across multiple queries

    Returns:
        Configured AgentRunner with memory enabled

    Example:
        >>> agent = exercise_3_solution()
        >>> agent.query("Remember that my name is Alice")
        >>> agent.query("What is my name?")  # Should recall "Alice"
    """
    agent = (
        AgentBuilder("Memory Agent")
        .set_system_prompt(
            "You are a helpful assistant with memory. You can remember "
            "information from previous messages in our conversation."
        )
        .add_tool(
            name="calculator",
            description="Evaluate mathematical expressions.",
            function=_get_tool_func(calculator),
        )
        .add_tool(
            name="date_helper",
            description="Answer questions about dates and times.",
            function=_get_tool_func(date_helper),
        )
        .add_routing_rule(
            keywords=["today", "tomorrow", "yesterday", "date", "time"],
            tool_name="date_helper",
            priority=2,
        )
        .add_routing_rule(
            keywords=["calculate", "math", "+", "-", "*", "/"],
            tool_name="calculator",
            priority=1,
        )
        # Enable memory with a unique thread ID
        .enable_memory(thread_id="exercise-3-session")
        .build(mock_mode=True)
    )

    return agent


def exercise_4_solution() -> AgentRunner:
    """Exercise 4: Complete agent with custom tools.

    This exercise demonstrates:
    - Creating custom tools from scratch
    - Combining multiple tools with different purposes
    - Setting up comprehensive routing rules
    - Configuring max iterations for safety

    Returns:
        Configured AgentRunner with multiple custom tools

    Example:
        >>> agent = exercise_4_solution()
        >>> result = agent.query("Convert 100 miles to kilometers")
        >>> print(result)  # Shows: 100 miles = 160.934 kilometers
    """
    # Custom tool: Unit converter
    @tool
    def unit_converter(query: str) -> str:
        """Convert between common units.

        Supports conversions for:
        - Distance: miles <-> kilometers, feet <-> meters
        - Weight: pounds <-> kilograms
        - Temperature: fahrenheit <-> celsius

        Args:
            query: Conversion request, e.g., "100 miles to kilometers"

        Returns:
            Conversion result as a formatted string
        """
        query_lower = query.lower()

        # Parse the query for numbers and units
        import re

        number_match = re.search(r"(\d+(?:\.\d+)?)", query)
        if not number_match:
            return "Please provide a number to convert."

        value = float(number_match.group(1))

        # Distance conversions
        if "mile" in query_lower and "kilometer" in query_lower:
            result = value * 1.60934
            return f"{value} miles = {result:.3f} kilometers"
        elif "kilometer" in query_lower and "mile" in query_lower:
            result = value / 1.60934
            return f"{value} kilometers = {result:.3f} miles"
        elif "feet" in query_lower and "meter" in query_lower:
            result = value * 0.3048
            return f"{value} feet = {result:.3f} meters"
        elif "meter" in query_lower and "feet" in query_lower:
            result = value / 0.3048
            return f"{value} meters = {result:.3f} feet"

        # Weight conversions
        elif "pound" in query_lower and "kilogram" in query_lower:
            result = value * 0.453592
            return f"{value} pounds = {result:.3f} kilograms"
        elif "kilogram" in query_lower and "pound" in query_lower:
            result = value / 0.453592
            return f"{value} kilograms = {result:.3f} pounds"

        # Temperature conversions
        elif "fahrenheit" in query_lower and "celsius" in query_lower:
            result = (value - 32) * 5 / 9
            return f"{value}°F = {result:.1f}°C"
        elif "celsius" in query_lower and "fahrenheit" in query_lower:
            result = (value * 9 / 5) + 32
            return f"{value}°C = {result:.1f}°F"

        return (
            "Unsupported conversion. Try: miles/km, feet/meters, "
            "pounds/kg, or fahrenheit/celsius."
        )

    agent = (
        AgentBuilder("Complete Assistant")
        .set_system_prompt(
            "You are a comprehensive assistant that can perform calculations, "
            "answer date questions, convert units, and search the web."
        )
        # Add all tools
        .add_tool(
            name="calculator",
            description="Evaluate mathematical expressions.",
            function=_get_tool_func(calculator),
        )
        .add_tool(
            name="date_helper",
            description="Answer questions about dates and times.",
            function=_get_tool_func(date_helper),
        )
        .add_tool(
            name="unit_converter",
            description="Convert between units (distance, weight, temperature).",
            function=_get_tool_func(unit_converter),
        )
        .add_tool(
            name="web_search",
            description="Search the web for information.",
            function=_get_tool_func(mock_web_search),
        )
        # Set up routing rules with priorities
        .add_routing_rule(
            keywords=["convert", "miles", "kilometers", "feet", "meters",
                     "pounds", "kilograms", "fahrenheit", "celsius"],
            tool_name="unit_converter",
            priority=3,
        )
        .add_routing_rule(
            keywords=["today", "tomorrow", "yesterday", "date", "time",
                     "christmas", "new year"],
            tool_name="date_helper",
            priority=2,
        )
        .add_routing_rule(
            keywords=["calculate", "math", "+", "-", "*", "/", "percent"],
            tool_name="calculator",
            priority=1,
        )
        .add_routing_rule(
            keywords=["search", "find", "look up", "weather", "news", "who is",
                     "what is"],
            tool_name="web_search",
            priority=0,  # Lowest priority - fallback
        )
        # Configure safety and memory
        .set_max_iterations(10)
        .enable_memory(thread_id="exercise-4-session")
        .build(mock_mode=True)
    )

    return agent


def test_all_solutions() -> dict[str, bool]:
    """Run quick verification tests on all exercise solutions.

    This function tests each solution with sample queries to verify
    they work correctly. Use this after implementing your solutions
    to ensure they function as expected.

    Returns:
        Dictionary mapping exercise names to pass/fail status

    Example:
        >>> results = test_all_solutions()
        >>> print(results)
        {'exercise_1': True, 'exercise_2': True, ...}
    """
    results = {}

    # Test Exercise 1: Calculator
    print("Testing Exercise 1: Calculator Agent...")
    try:
        agent = exercise_1_solution()
        result = agent.query("What is 25 * 4?")
        # Should contain "100" in the result
        results["exercise_1"] = "100" in result
        print(f"  Query: 'What is 25 * 4?' -> '{result}'")
        print(f"  Pass: {results['exercise_1']}")
    except Exception as e:
        results["exercise_1"] = False
        print(f"  Error: {e}")

    # Test Exercise 2: Date Helper
    print("\nTesting Exercise 2: Date Helper Agent...")
    try:
        agent = exercise_2_solution()
        result = agent.query("What day is today?")
        # Should mention a day of the week
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        results["exercise_2"] = any(day in result for day in days)
        print(f"  Query: 'What day is today?' -> '{result[:80]}...'")
        print(f"  Pass: {results['exercise_2']}")
    except Exception as e:
        results["exercise_2"] = False
        print(f"  Error: {e}")

    # Test Exercise 3: Memory Agent
    print("\nTesting Exercise 3: Memory Agent...")
    try:
        agent = exercise_3_solution()
        # First query
        agent.query("What is 5 + 5?")
        # Second query - should work
        result = agent.query("What is today's date?")
        results["exercise_3"] = len(result) > 0
        print(f"  Multi-query test passed")
        print(f"  Pass: {results['exercise_3']}")
    except Exception as e:
        results["exercise_3"] = False
        print(f"  Error: {e}")

    # Test Exercise 4: Complete Agent
    print("\nTesting Exercise 4: Complete Agent...")
    try:
        agent = exercise_4_solution()
        result = agent.query("Convert 100 miles to kilometers")
        # Should mention approximately 160.934
        results["exercise_4"] = "160" in result
        print(f"  Query: 'Convert 100 miles to kilometers' -> '{result}'")
        print(f"  Pass: {results['exercise_4']}")
    except Exception as e:
        results["exercise_4"] = False
        print(f"  Error: {e}")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")

    return results


__all__ = [
    "exercise_1_solution",
    "exercise_2_solution",
    "exercise_3_solution",
    "exercise_4_solution",
    "test_all_solutions",
]
