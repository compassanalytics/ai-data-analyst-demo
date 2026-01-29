"""Workshop helper - Pre-built tools for the Agent Builder workshop.

This module provides ready-to-use tools that wrap common functionality
with the @tool decorator from langchain_core.tools. These tools are
designed to be educational and demonstrate best practices.

Tools:
    calculator: Safe math evaluation using AST parsing
    date_helper: Date/time queries without external dependencies
    mock_web_search: Simulated web search for testing

Example:
    >>> from src.workshop.tools import calculator, date_helper
    >>> calculator("2 + 2")
    '4'
    >>> date_helper("what day is today")
    'Today is Tuesday, January 28, 2025'
"""

from __future__ import annotations

import ast
import math
import operator
import re
from datetime import datetime, timedelta
from langchain_core.tools import tool


# Safe operators for calculator AST evaluation
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe functions for calculator
_SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": pow,
    "min": min,
    "max": max,
}

# Safe constants
_SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval_ast(node: ast.AST) -> float | int:
    """Safely evaluate an AST node using allowlisted operations.

    Args:
        node: AST node to evaluate

    Returns:
        Numeric result of evaluation

    Raises:
        ValueError: If node contains disallowed operations
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    elif isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"Unknown variable: {node.id}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval_ast(node.left)
        right = _safe_eval_ast(node.right)
        return _SAFE_OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _safe_eval_ast(node.operand)
        return _SAFE_OPERATORS[op_type](operand)

    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are supported")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Unknown function: {func_name}")
        args = [_safe_eval_ast(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)

    elif isinstance(node, ast.Expression):
        return _safe_eval_ast(node.body)

    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


def _extract_math_expression(text: str) -> str:
    """Extract a mathematical expression from natural language text.

    Handles common patterns like "What is 2 + 2?" or "Calculate 5 * 3".

    Args:
        text: Natural language text potentially containing math

    Returns:
        Extracted expression or original text if no pattern found
    """
    # Try to find a math expression pattern in the text
    # Pattern: numbers and operators grouped together
    math_pattern = r"(\d+(?:\.\d+)?\s*(?:[+\-*/^%]\s*\d+(?:\.\d+)?)+)"
    match = re.search(math_pattern, text)
    if match:
        return match.group(1)

    # Pattern: "X% of Y"
    percent_pattern = r"(\d+(?:\.\d+)?\s*%\s*of\s*\d+(?:\.\d+)?)"
    match = re.search(percent_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern: function calls like sqrt(16)
    func_pattern = r"((?:sqrt|abs|round|floor|ceil|sin|cos|tan|log|log10|exp|pow|min|max)\s*\([^)]+\))"
    match = re.search(func_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern: just numbers with operators anywhere in text
    # More aggressive extraction
    operators_pattern = r"(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)"
    match = re.search(operators_pattern, text)
    if match:
        return f"{match.group(1)} {match.group(2)} {match.group(3)}"

    # No extraction possible, return original
    return text


def _preprocess_expression(expression: str) -> str:
    """Preprocess expression to handle percentage notation.

    Converts patterns like "15% of 250" to "(15/100) * 250".

    Args:
        expression: Math expression possibly containing percentages

    Returns:
        Normalized expression ready for AST parsing
    """
    # Handle "X% of Y" pattern
    percent_of_pattern = r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)"
    expression = re.sub(
        percent_of_pattern,
        lambda m: f"({m.group(1)}/100) * {m.group(2)}",
        expression,
        flags=re.IGNORECASE,
    )

    # Handle standalone percentages like "15%" -> "15/100"
    standalone_percent = r"(\d+(?:\.\d+)?)\s*%(?!\s*of)"
    expression = re.sub(
        standalone_percent,
        lambda m: f"({m.group(1)}/100)",
        expression,
    )

    return expression


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Supports basic arithmetic (+, -, *, /, **, %), percentages ("15% of 250"),
    and common math functions (sqrt, abs, round, floor, ceil, sin, cos, tan,
    log, log10, exp, pow, min, max).

    Uses AST-based evaluation for security - no raw eval().

    Args:
        expression: Mathematical expression to evaluate.
            Examples: "2 + 2", "sqrt(16)", "15% of 250", "round(3.7)"

    Returns:
        String result of the calculation, or error message if invalid.

    Examples:
        >>> calculator("2 + 2")
        '4'
        >>> calculator("sqrt(16)")
        '4.0'
        >>> calculator("15% of 200")
        '30.0'
        >>> calculator("round(3.7)")
        '4'
    """
    try:
        # Extract math expression from natural language if needed
        extracted = _extract_math_expression(expression.strip())
        # Preprocess for percentage handling
        processed = _preprocess_expression(extracted)

        # Parse to AST
        tree = ast.parse(processed, mode="eval")

        # Safely evaluate
        result = _safe_eval_ast(tree)

        # Format result
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(result)

    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: {e}"
    except SyntaxError:
        return f"Error: Invalid expression syntax - '{expression}'"
    except Exception as e:
        return f"Error: Could not evaluate expression - {e}"


@tool
def date_helper(query: str) -> str:
    """Answer date and time related questions.

    Handles common date queries using rule-based parsing without
    external dependencies. All responses use the current system time.

    Args:
        query: Natural language question about dates/times.
            Supported queries:
            - "what day is today" / "today" / "current date"
            - "current time" / "what time is it"
            - "tomorrow" / "what day is tomorrow"
            - "yesterday" / "what day was yesterday"
            - "days until Christmas" / "days until New Year"

    Returns:
        Human-readable answer to the date/time question.

    Examples:
        >>> date_helper("what day is today")
        'Today is Tuesday, January 28, 2025'
        >>> date_helper("days until Christmas")
        'There are 331 days until Christmas (December 25, 2025)'
    """
    query_lower = query.lower().strip()
    now = datetime.now()

    # Today queries
    if any(kw in query_lower for kw in ["today", "current date", "what day"]):
        if "time" not in query_lower:
            return f"Today is {now.strftime('%A, %B %d, %Y')}"

    # Time queries
    if any(kw in query_lower for kw in ["time", "what time", "current time"]):
        return f"The current time is {now.strftime('%I:%M %p')} ({now.strftime('%H:%M')})"

    # Tomorrow
    if "tomorrow" in query_lower:
        tomorrow = now + timedelta(days=1)
        return f"Tomorrow is {tomorrow.strftime('%A, %B %d, %Y')}"

    # Yesterday
    if "yesterday" in query_lower:
        yesterday = now - timedelta(days=1)
        return f"Yesterday was {yesterday.strftime('%A, %B %d, %Y')}"

    # Days until Christmas
    if "christmas" in query_lower:
        christmas = datetime(now.year, 12, 25)
        if now > christmas:
            christmas = datetime(now.year + 1, 12, 25)
        days = (christmas - now).days
        if days == 0:
            return "Today is Christmas! Merry Christmas!"
        return f"There are {days} days until Christmas ({christmas.strftime('%B %d, %Y')})"

    # Days until New Year
    if "new year" in query_lower:
        new_year = datetime(now.year + 1, 1, 1)
        days = (new_year - now).days
        if days == 0:
            return "Happy New Year!"
        return f"There are {days} days until New Year ({new_year.strftime('%B %d, %Y')})"

    # Weekday queries
    if "what day of the week" in query_lower:
        return f"Today is {now.strftime('%A')}"

    # Month/year queries
    if "what month" in query_lower:
        return f"The current month is {now.strftime('%B %Y')}"

    if "what year" in query_lower:
        return f"The current year is {now.year}"

    # Default: return current date and time
    return f"Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}"


# Mock search result templates
_MOCK_WEATHER = """**Weather Search Results** (Mock Data)

Current weather for {query}:
- Temperature: 72°F (22°C)
- Conditions: Partly cloudy
- Humidity: 45%
- Wind: 8 mph NW

Note: This is simulated data for workshop demonstration purposes."""

_MOCK_NEWS = """**News Search Results** (Mock Data)

Top headlines related to "{query}":

1. **Tech Industry Sees Record Growth in Q4**
   Major technology companies report strong earnings...

2. **Global Markets React to Economic Data**
   Investors analyze latest employment figures...

3. **Innovation Summit Highlights AI Advances**
   Industry leaders discuss future of artificial intelligence...

Note: This is simulated data for workshop demonstration purposes."""

_MOCK_GENERIC = """**Web Search Results** (Mock Data)

Search results for: "{query}"

1. **Wikipedia: {query}**
   A comprehensive overview and background information...
   https://en.wikipedia.org/wiki/{query}

2. **{query} - Official Website**
   The official source for information about {query}...

3. **Understanding {query}: A Complete Guide**
   Everything you need to know about {query}...

Note: This is simulated data for workshop demonstration purposes."""


@tool
def mock_web_search(query: str) -> str:
    """Perform a simulated web search (for workshop/testing purposes).

    Returns mock search results based on query keywords. This tool is
    designed for workshop demonstrations and testing agent behavior
    without requiring real API credentials.

    Args:
        query: Search query string

    Returns:
        Mock search results formatted as markdown.
        Results vary based on detected keywords (weather, news, etc.)

    Examples:
        >>> mock_web_search("weather in San Francisco")
        '**Weather Search Results** (Mock Data)...'
        >>> mock_web_search("latest tech news")
        '**News Search Results** (Mock Data)...'
    """
    query_lower = query.lower()

    # Weather queries
    if any(kw in query_lower for kw in ["weather", "temperature", "forecast"]):
        return _MOCK_WEATHER.format(query=query)

    # News queries
    if any(kw in query_lower for kw in ["news", "headlines", "latest", "recent", "today"]):
        return _MOCK_NEWS.format(query=query)

    # Generic search
    return _MOCK_GENERIC.format(query=query)


# Template for creating custom tools
TOOL_TEMPLATE = '''"""Custom tool template for workshop exercises.

Copy this template to create your own tools for the Agent Builder.
"""

from langchain_core.tools import tool


@tool
def my_custom_tool(input_param: str) -> str:
    """Brief description of what this tool does.

    A longer description explaining the tool's purpose, inputs,
    and expected outputs. Include any important notes about
    usage or limitations.

    Args:
        input_param: Description of the input parameter

    Returns:
        Description of what the tool returns

    Examples:
        >>> my_custom_tool("example input")
        'example output'
    """
    # Your implementation here
    result = f"Processed: {input_param}"
    return result


# To use this tool with AgentBuilder:
#
# from src.workshop import AgentBuilder
# from my_tools import my_custom_tool
#
# agent = (
#     AgentBuilder("My Agent")
#     .add_tool(
#         name="my_custom_tool",
#         description="Brief description for the agent",
#         function=my_custom_tool.func,  # Note: use .func to get the underlying function
#     )
#     .build()
# )
'''


__all__ = [
    "calculator",
    "date_helper",
    "mock_web_search",
    "TOOL_TEMPLATE",
]
