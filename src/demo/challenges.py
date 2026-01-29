"""Challenge framework for workshop notebook interactivity.

This module provides a lightweight challenge system for guided exercises
in workshop notebooks. Follows the SLIM design principle - just enough
structure for validation and hints without unnecessary complexity.

Color scheme for difficulty badges:
- EASY: Green #10B981
- MEDIUM: Amber #F59E0B
- HARD: Red #EF4444
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.demo.feedback import (
    COLOR_SUCCESS,
    display_error,
    display_info,
    display_success,
)


class Difficulty(Enum):
    """Challenge difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# Difficulty badge colors
DIFFICULTY_COLORS = {
    Difficulty.EASY: "#10B981",  # Green
    Difficulty.MEDIUM: "#F59E0B",  # Amber
    Difficulty.HARD: "#EF4444",  # Red
}


@dataclass
class Challenge:
    """A workshop challenge with validation and hints.

    Attributes:
        id: Unique identifier for the challenge
        title: Display title
        description: Detailed instructions for the challenge
        difficulty: Challenge difficulty level
        time_estimate_minutes: Estimated time to complete
        hints: Progressive hints (revealed one at a time)
        validator: Function that validates answer, returns (success, message)
        success_message: Message to display on successful completion
        solution_code: Optional code solution (for presenter mode)
    """

    id: str
    title: str
    description: str
    difficulty: Difficulty
    time_estimate_minutes: int
    hints: list[str] = field(default_factory=list)
    validator: Callable[[Any], tuple[bool, str]] = field(default=lambda _: (True, ""))
    success_message: str = "Challenge completed!"
    solution_code: str | None = None


def _get_display():
    """Get IPython display function if available."""
    try:
        from IPython.display import HTML, display

        return display, HTML
    except ImportError:
        return None, None


def _create_difficulty_badge(difficulty: Difficulty) -> str:
    """Create HTML badge for difficulty level.

    Args:
        difficulty: The difficulty level

    Returns:
        HTML string for the badge
    """
    color = DIFFICULTY_COLORS.get(difficulty, COLOR_SUCCESS)
    label = difficulty.value.upper()

    return f"""
        <span style="
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            background-color: {color};
            color: white;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            margin-left: 8px;
        ">{label}</span>
    """


class ChallengeRunner:
    """Manages challenge execution, hints, and tracking.

    Provides a slim interface for running challenges in notebooks:
    - Display challenge instructions
    - Reveal progressive hints
    - Validate answers
    - Track completion status

    Example:
        >>> runner = ChallengeRunner()
        >>> runner.show_challenge(DEMO_CHALLENGES["modify_query"])
        >>> # User attempts the challenge...
        >>> runner.validate(DEMO_CHALLENGES["modify_query"], user_answer)
        >>> runner.reveal_hint("modify_query", DEMO_CHALLENGES["modify_query"])
    """

    def __init__(self) -> None:
        """Initialize the challenge runner."""
        self._hints_revealed: dict[str, int] = {}
        self._attempts: dict[str, int] = {}
        self._completed: set[str] = set()

    def show_challenge(self, challenge: Challenge) -> None:
        """Display challenge instructions with styling.

        Args:
            challenge: The challenge to display
        """
        display, HTML = _get_display()

        badge = _create_difficulty_badge(challenge.difficulty)
        time_text = f"{challenge.time_estimate_minutes} min"

        if display and HTML:
            html = f'''
            <div style="
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 16px 0;
                border: 2px solid #3B82F6;
                border-radius: 12px;
                overflow: hidden;
            ">
                <div style="
                    background: linear-gradient(135deg, #3B82F6, #1D4ED8);
                    padding: 16px 20px;
                    color: white;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    ">
                        <div style="display: flex; align-items: center;">
                            <span style="font-size: 24px; margin-right: 12px;">&#127919;</span>
                            <span style="font-size: 18px; font-weight: 600;">
                                CHALLENGE: {challenge.title}
                            </span>
                            {badge}
                        </div>
                        <span style="
                            font-size: 13px;
                            opacity: 0.9;
                        ">&#9201; {time_text}</span>
                    </div>
                </div>
                <div style="
                    padding: 20px;
                    background-color: #f8fafc;
                ">
                    <div style="
                        font-size: 15px;
                        line-height: 1.6;
                        color: #1f2937;
                        white-space: pre-wrap;
                    ">{challenge.description}</div>
                    <div style="
                        margin-top: 16px;
                        padding-top: 12px;
                        border-top: 1px solid #e5e7eb;
                        font-size: 13px;
                        color: #6b7280;
                    ">
                        &#128161; <strong>{len(challenge.hints)} hints available</strong> -
                        Call <code>runner.reveal_hint("{challenge.id}", challenge)</code> if you get stuck
                    </div>
                </div>
            </div>
            '''
            display(HTML(html))
        else:
            # Text fallback
            print("=" * 60)
            print(f"CHALLENGE: {challenge.title} [{challenge.difficulty.value.upper()}]")
            print(f"Estimated time: {time_text}")
            print("=" * 60)
            print()
            print(challenge.description)
            print()
            print(f"Hints available: {len(challenge.hints)}")
            print("=" * 60)

    def reveal_hint(self, challenge_id: str, challenge: Challenge) -> str | None:
        """Reveal the next hint for a challenge.

        Hints are revealed progressively, one at a time.

        Args:
            challenge_id: ID of the challenge
            challenge: The challenge object

        Returns:
            The revealed hint, or None if no more hints
        """
        if not challenge.hints:
            display_info("No hints available for this challenge.")
            return None

        current_hint_index = self._hints_revealed.get(challenge_id, 0)

        if current_hint_index >= len(challenge.hints):
            display_info("All hints revealed!", "You've seen all available hints for this challenge.")
            return None

        hint = challenge.hints[current_hint_index]
        self._hints_revealed[challenge_id] = current_hint_index + 1

        display, HTML = _get_display()
        hint_number = current_hint_index + 1
        remaining = len(challenge.hints) - hint_number

        if display and HTML:
            html = f"""
            <div style="
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 700px;
                margin: 8px 0;
                padding: 16px;
                background-color: #FEF3C7;
                border-left: 4px solid #F59E0B;
                border-radius: 0 8px 8px 0;
            ">
                <div style="
                    display: flex;
                    align-items: flex-start;
                ">
                    <span style="
                        font-size: 20px;
                        margin-right: 12px;
                    ">&#128161;</span>
                    <div>
                        <div style="
                            font-size: 12px;
                            font-weight: 600;
                            color: #92400E;
                            text-transform: uppercase;
                            margin-bottom: 4px;
                        ">Hint {hint_number} of {len(challenge.hints)}</div>
                        <div style="
                            font-size: 14px;
                            color: #78350F;
                            line-height: 1.5;
                        ">{hint}</div>
                        <div style="
                            font-size: 12px;
                            color: #A16207;
                            margin-top: 8px;
                        ">{remaining} hint{"s" if remaining != 1 else ""} remaining</div>
                    </div>
                </div>
            </div>
            """
            display(HTML(html))
        else:
            print(f"[HINT {hint_number}/{len(challenge.hints)}] {hint}")
            print(f"  ({remaining} hints remaining)")

        return hint

    def validate(self, challenge: Challenge, answer: Any) -> bool:
        """Validate an answer for a challenge.

        Args:
            challenge: The challenge being attempted
            answer: The participant's answer

        Returns:
            True if the answer is correct, False otherwise
        """
        # Track attempt
        self._attempts[challenge.id] = self._attempts.get(challenge.id, 0) + 1
        attempt_num = self._attempts[challenge.id]

        try:
            success, message = challenge.validator(answer)
        except Exception as e:
            display_error(f"Validation error: {e}", "Check that your answer is in the expected format.")
            return False

        if success:
            self._completed.add(challenge.id)
            details = f"Completed in {attempt_num} attempt{'s' if attempt_num != 1 else ''}."
            if message:
                details += f" {message}"
            display_success(challenge.success_message, details)
            return True
        else:
            suggestion = message if message else "Check your approach and try again."
            hints_used = self._hints_revealed.get(challenge.id, 0)
            hints_available = len(challenge.hints) - hints_used

            if hints_available > 0:
                suggestion += f" ({hints_available} hints still available)"

            display_error(f"Not quite right (attempt {attempt_num})", suggestion)
            return False

    def is_completed(self, challenge_id: str) -> bool:
        """Check if a challenge has been completed.

        Args:
            challenge_id: ID of the challenge to check

        Returns:
            True if completed, False otherwise
        """
        return challenge_id in self._completed

    def reset(self) -> None:
        """Reset all tracking state."""
        self._hints_revealed.clear()
        self._attempts.clear()
        self._completed.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get challenge completion statistics.

        Returns:
            Dictionary with completion stats
        """
        return {
            "completed": list(self._completed),
            "attempts": dict(self._attempts),
            "hints_revealed": dict(self._hints_revealed),
        }


# Global runner instance for convenience functions
_global_runner: ChallengeRunner | None = None


def get_challenge_runner() -> ChallengeRunner:
    """Get the global challenge runner instance.

    Returns:
        The global ChallengeRunner instance
    """
    global _global_runner
    if _global_runner is None:
        _global_runner = ChallengeRunner()
    return _global_runner


def run_challenge(challenge: Challenge, answer: Any) -> bool:
    """Validate a challenge answer using the global runner.

    Convenience function for one-liner validation.

    Args:
        challenge: The challenge being attempted
        answer: The participant's answer

    Returns:
        True if correct, False otherwise

    Example:
        >>> from src.demo.challenges import DEMO_CHALLENGES, run_challenge
        >>> run_challenge(DEMO_CHALLENGES["modify_query"], my_result)
    """
    return get_challenge_runner().validate(challenge, answer)


# =============================================================================
# Pre-defined Challenges
# =============================================================================


def _validate_modified_query(answer: Any) -> tuple[bool, str]:
    """Validate that a query was modified to include a filter or aggregation."""
    if answer is None:
        return False, "No result provided."

    # Check if it's a GenieResult or similar
    if hasattr(answer, "success") and not answer.success:
        return False, f"Query failed: {getattr(answer, 'error', 'Unknown error')}"

    if hasattr(answer, "data"):
        if answer.data and len(answer.data) > 0:
            return True, "Query executed successfully with results!"
        return False, "Query returned no data. Check your filter conditions."

    # Generic check - if answer is truthy and not empty
    if answer:
        return True, ""
    return False, "No valid result returned."


def _validate_custom_tool(answer: Any) -> tuple[bool, str]:
    """Validate that a custom tool was defined correctly."""
    if answer is None:
        return False, "No tool provided."

    # Check for callable
    if not callable(answer):
        return False, "Tool must be a callable function."

    # Check for docstring
    if not answer.__doc__:
        return False, "Tool should have a docstring describing its purpose."

    return True, "Tool defined correctly!"


def _validate_report_type_change(answer: Any) -> tuple[bool, str]:
    """Validate that report type was successfully changed."""
    if answer is None:
        return False, "No report provided."

    # Check if it's a string (markdown/html report)
    if isinstance(answer, str):
        if len(answer) > 100:
            return True, "Report generated successfully!"
        return False, "Report seems too short. Did the generation complete?"

    # Check for synthesis result
    if hasattr(answer, "key_insights"):
        if answer.key_insights:
            return True, "Synthesis completed successfully!"
        return False, "No insights generated. Check the pipeline execution."

    return False, "Unexpected result type."


def _validate_genie_space_added(answer: Any) -> tuple[bool, str]:
    """Validate that a new Genie Space was added to the configuration."""
    if answer is None:
        return False, "No configuration provided."

    # Check if it's a list of space configs
    if isinstance(answer, list):
        if len(answer) > 3:  # More than the default 3 spaces
            return True, f"Configuration updated with {len(answer)} spaces!"
        return False, "Add at least one new space to the configuration."

    # Check if it's a MultiGenieResult or similar
    if hasattr(answer, "results"):
        if len(answer.results) > 3:
            return True, f"Successfully queried {len(answer.results)} spaces!"
        return False, "New space not detected in results."

    return False, "Provide the updated space_configs list or query result."


# Demo notebook challenges
DEMO_CHALLENGES: dict[str, Challenge] = {
    "modify_query": Challenge(
        id="modify_query",
        title="Modify the Query",
        description="""Modify the data query to filter results by a specific condition.

Your task:
1. In the query cell above, change the question to filter by:
   - A specific customer segment (e.g., "AUTOMOBILE")
   - Or a specific region (e.g., "EUROPE")
   - Or a date range

2. Execute the modified query
3. Pass the result to this validation cell

Example modifications:
- "Show orders from AUTOMOBILE segment customers"
- "What is the revenue from the EUROPE region?"
- "Show orders from the last quarter"
""",
        difficulty=Difficulty.EASY,
        time_estimate_minutes=5,
        hints=[
            "Try adding a segment filter like 'from Fleet segment'",
            "Check the Velocity Motors schema - common filters include: customer segment (Individual/Fleet/Dealer), vehicle condition (New/Certified Pre-Owned/Used), region, payment_method",
            "Your modified query should return fewer rows than the original",
        ],
        validator=_validate_modified_query,
        success_message="Excellent! You successfully filtered the query results.",
        solution_code="""# Example solution - filter by customer segment
question = "Show the top 10 customers by total orders from the AUTOMOBILE segment"
result = genie.query(question)
print(result.to_markdown_table())""",
    ),
    "add_tool": Challenge(
        id="add_tool",
        title="Define a Custom Tool",
        description="""Create a custom tool function that could be used by the supervisor agent.

Your task:
1. Define a function that:
   - Has a clear docstring
   - Takes at least one parameter
   - Returns a meaningful result

2. The function should do something useful for data analysis, such as:
   - Format currency values
   - Calculate percentage changes
   - Categorize numeric values

3. Pass your function to this validation cell
""",
        difficulty=Difficulty.MEDIUM,
        time_estimate_minutes=10,
        hints=[
            "Start with a simple function like: def format_currency(amount: float) -> str:",
            "Add a docstring: '''Format amount as USD currency.'''",
            "Don't forget to include type hints for better clarity",
        ],
        validator=_validate_custom_tool,
        success_message="Great job! Your custom tool is ready to use.",
        solution_code='''# Example solution - currency formatter
def format_currency(amount: float, currency: str = "USD") -> str:
    """Format a numeric amount as currency.

    Args:
        amount: The numeric value to format
        currency: Currency code (default: USD)

    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"{amount:,.2f}"
    return f"{amount:,.2f} {currency}"

# Test it
format_currency(1234567.89)  # Returns: "$1,234,567.89"''',
    ),
}


# Advanced demo notebook challenges
ADVANCED_CHALLENGES: dict[str, Challenge] = {
    "change_report_type": Challenge(
        id="change_report_type",
        title="Change the Report Type",
        description="""Modify the pipeline to generate a different type of report.

Your task:
1. Change the report_type variable to one of:
   - "YTD Summary" (Year-to-Date)
   - "Custom Query" (with your own question)

2. Re-run the pipeline
3. Pass the generated report (markdown_report or synthesis_result) to validation

This demonstrates how the same pipeline can produce different outputs
based on configuration.
""",
        difficulty=Difficulty.EASY,
        time_estimate_minutes=5,
        hints=[
            "Look for the REPORT_QUESTIONS dictionary in the configuration cell",
            "If using 'Custom Query', make sure to also set the custom_query variable",
            "After changing the config, re-run from the configuration cell onwards",
        ],
        validator=_validate_report_type_change,
        success_message="Perfect! You've successfully customized the report type.",
        solution_code="""# Example solution - change to YTD Summary
report_type = "YTD Summary"
# Or for custom:
# report_type = "Custom Query"
# custom_query = "Analyze customer churn patterns over the last 6 months"

# Then re-run the pipeline...
question = REPORT_QUESTIONS[report_type]""",
    ),
    "add_genie_space": Challenge(
        id="add_genie_space",
        title="Add a New Genie Space",
        description="""Add a fourth Genie Space to the orchestrator configuration.

Your task:
1. Create a new GenieSpaceConfig for a domain like:
   - "Finance" (budgets, expenses, forecasts)
   - "Marketing" (campaigns, leads, conversions)
   - "Operations" (shipping, fulfillment, logistics)

2. Add it to the space_configs list
3. Re-initialize the orchestrator
4. Run a query and pass the result to validation

Note: In mock mode, any space_id works. In live mode, you'd need a real Space ID.
""",
        difficulty=Difficulty.MEDIUM,
        time_estimate_minutes=10,
        hints=[
            "Create: GenieSpaceConfig(space_id='mock-finance', name='Finance', domain='...')",
            "Append to list: space_configs.append(new_config)",
            "Re-create orchestrator with updated space_configs",
        ],
        validator=_validate_genie_space_added,
        success_message="Excellent! You've expanded the multi-agent system.",
        solution_code="""# Example solution - add Finance space
finance_space = GenieSpaceConfig(
    space_id="mock-finance-space",
    name="Finance",
    domain="budgets, expenses, forecasts, financial planning",
)

space_configs.append(finance_space)

# Re-initialize orchestrator with new config
orchestrator = MultiGenieOrchestrator(
    space_configs,
    config,
    progress_callback=state.get_progress_callback(),
)

# Query all spaces including the new one
result = orchestrator.query_all("Analyze Q4 performance across all domains")""",
    ),
}
