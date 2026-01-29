"""Feedback and display utilities for workshop notebooks.

This module provides visual feedback functions for displaying success/error
messages, comparing outputs, and showing progress in Jupyter/Databricks notebooks.

Color scheme matches visualization.py for consistency:
- Success: Green #10B981 (same as complete status)
- Error: Red #EF4444 (same as error status)
- Warning: Amber #F59E0B (same as retrying status)
- Info: Blue #3B82F6 (same as running status)
"""

from __future__ import annotations

from typing import Any, Optional

# Color constants matching visualization.py
COLOR_SUCCESS = "#10B981"  # Green - complete status
COLOR_ERROR = "#EF4444"    # Red - error status
COLOR_WARNING = "#F59E0B"  # Amber - retrying status
COLOR_INFO = "#3B82F6"     # Blue - running status
COLOR_NEUTRAL = "#6B7280"  # Gray - pending status


def _get_display():
    """Get IPython display function if available."""
    try:
        from IPython.display import display, HTML
        return display, HTML
    except ImportError:
        return None, None


def _create_banner(
    message: str,
    color: str,
    icon: str,
    details: Optional[str] = None,
    extra_content: str = "",
) -> str:
    """Create HTML banner with consistent styling.

    Args:
        message: Main message text
        color: Banner color (hex)
        icon: Unicode icon character
        details: Optional additional details text
        extra_content: Optional extra HTML content

    Returns:
        HTML string for the banner
    """
    details_html = ""
    if details:
        details_html = f'''
            <div style="margin-top: 8px; font-size: 13px; color: #4b5563;">
                {details}
            </div>
        '''

    return f'''
    <div style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        padding: 16px;
        margin: 8px 0;
        border-radius: 8px;
        background-color: {color}15;
        border-left: 4px solid {color};
        max-width: 800px;
    ">
        <div style="display: flex; align-items: flex-start;">
            <span style="
                font-size: 20px;
                margin-right: 12px;
                line-height: 1;
            ">{icon}</span>
            <div style="flex: 1;">
                <div style="font-size: 15px; font-weight: 600; color: {color};">
                    {message}
                </div>
                {details_html}
                {extra_content}
            </div>
        </div>
    </div>
    '''


def display_success(message: str, details: Optional[str] = None) -> None:
    """Display a success message with green banner and checkmark.

    Args:
        message: Success message to display
        details: Optional additional details
    """
    display, HTML = _get_display()
    if display and HTML:
        html = _create_banner(message, COLOR_SUCCESS, "\u2713", details)
        display(HTML(html))
    else:
        print(f"[SUCCESS] {message}")
        if details:
            print(f"  {details}")


def display_error(message: str, suggestion: Optional[str] = None) -> None:
    """Display an error message with red banner and recovery suggestion.

    Args:
        message: Error message to display
        suggestion: Optional recovery suggestion
    """
    display, HTML = _get_display()

    suggestion_html = ""
    if suggestion:
        suggestion_html = f'''
            <div style="
                margin-top: 12px;
                padding: 8px 12px;
                background-color: #fef3c7;
                border-radius: 4px;
                font-size: 13px;
                color: #92400e;
            ">
                <strong>Suggestion:</strong> {suggestion}
            </div>
        '''

    if display and HTML:
        html = _create_banner(message, COLOR_ERROR, "\u2717", extra_content=suggestion_html)
        display(HTML(html))
    else:
        print(f"[ERROR] {message}")
        if suggestion:
            print(f"  Suggestion: {suggestion}")


def display_warning(message: str, details: Optional[str] = None) -> None:
    """Display a warning message with amber banner.

    Args:
        message: Warning message to display
        details: Optional additional details
    """
    display, HTML = _get_display()
    if display and HTML:
        html = _create_banner(message, COLOR_WARNING, "\u26a0", details)
        display(HTML(html))
    else:
        print(f"[WARNING] {message}")
        if details:
            print(f"  {details}")


def display_info(message: str, details: Optional[str] = None) -> None:
    """Display an info message with blue banner.

    Args:
        message: Info message to display
        details: Optional additional details
    """
    display, HTML = _get_display()
    if display and HTML:
        html = _create_banner(message, COLOR_INFO, "\u2139", details)
        display(HTML(html))
    else:
        print(f"[INFO] {message}")
        if details:
            print(f"  {details}")


def compare_output(
    actual: Any,
    expected: Any,
    label_actual: str = "Your Output",
    label_expected: str = "Expected Output",
) -> bool:
    """Display side-by-side comparison of actual vs expected output.

    Useful for workshop exercises where participants need to verify their results.

    Args:
        actual: The actual output to compare
        expected: The expected output
        label_actual: Label for actual output column
        label_expected: Label for expected output column

    Returns:
        True if actual equals expected, False otherwise
    """
    display, HTML = _get_display()
    matches = actual == expected

    # Convert to strings for display
    actual_str = str(actual)
    expected_str = str(expected)

    # Truncate long outputs
    max_len = 500
    if len(actual_str) > max_len:
        actual_str = actual_str[:max_len] + "..."
    if len(expected_str) > max_len:
        expected_str = expected_str[:max_len] + "..."

    # Escape HTML
    actual_str = actual_str.replace("<", "&lt;").replace(">", "&gt;")
    expected_str = expected_str.replace("<", "&lt;").replace(">", "&gt;")

    if display and HTML:
        match_color = COLOR_SUCCESS if matches else COLOR_ERROR
        match_icon = "\u2713" if matches else "\u2717"
        match_text = "Match!" if matches else "Mismatch"

        html = f'''
        <div style="
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 8px 0;
        ">
            <div style="
                display: flex;
                align-items: center;
                padding: 8px 12px;
                background-color: {match_color}15;
                border-radius: 8px 8px 0 0;
                border-left: 4px solid {match_color};
            ">
                <span style="font-size: 18px; margin-right: 8px;">{match_icon}</span>
                <span style="font-weight: 600; color: {match_color};">{match_text}</span>
            </div>
            <div style="
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                padding: 16px;
                background-color: #f9fafb;
                border-radius: 0 0 8px 8px;
                border: 1px solid #e5e7eb;
                border-top: none;
            ">
                <div>
                    <div style="
                        font-size: 12px;
                        font-weight: 600;
                        color: #6b7280;
                        text-transform: uppercase;
                        margin-bottom: 8px;
                    ">{label_actual}</div>
                    <pre style="
                        background-color: white;
                        padding: 12px;
                        border-radius: 4px;
                        border: 1px solid #e5e7eb;
                        font-size: 13px;
                        overflow-x: auto;
                        margin: 0;
                        white-space: pre-wrap;
                        word-break: break-word;
                    ">{actual_str}</pre>
                </div>
                <div>
                    <div style="
                        font-size: 12px;
                        font-weight: 600;
                        color: #6b7280;
                        text-transform: uppercase;
                        margin-bottom: 8px;
                    ">{label_expected}</div>
                    <pre style="
                        background-color: white;
                        padding: 12px;
                        border-radius: 4px;
                        border: 1px solid #e5e7eb;
                        font-size: 13px;
                        overflow-x: auto;
                        margin: 0;
                        white-space: pre-wrap;
                        word-break: break-word;
                    ">{expected_str}</pre>
                </div>
            </div>
        </div>
        '''
        display(HTML(html))
    else:
        print(f"{'=' * 60}")
        print(f"Comparison: {'MATCH' if matches else 'MISMATCH'}")
        print(f"{'=' * 60}")
        print(f"\n{label_actual}:")
        print(f"-" * 40)
        print(actual_str)
        print(f"\n{label_expected}:")
        print(f"-" * 40)
        print(expected_str)
        print(f"{'=' * 60}")

    return matches


def display_progress_spinner(message: str) -> str:
    """Generate HTML string with CSS animated progress spinner.

    Note: This returns an HTML string rather than displaying directly,
    allowing the caller to manage the display lifecycle.

    Args:
        message: Message to display next to spinner

    Returns:
        HTML string with animated spinner

    Example:
        >>> from IPython.display import display, HTML
        >>> spinner_html = display_progress_spinner("Processing...")
        >>> handle = display(HTML(spinner_html), display_id=True)
        >>> # ... do work ...
        >>> handle.update(HTML("<div>Done!</div>"))
    """
    return f'''
    <div style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        display: flex;
        align-items: center;
        padding: 12px 16px;
        background-color: {COLOR_INFO}15;
        border-radius: 8px;
        border-left: 4px solid {COLOR_INFO};
        max-width: 400px;
        margin: 8px 0;
    ">
        <style>
            @keyframes workshop-spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
        <div style="
            width: 20px;
            height: 20px;
            border: 3px solid {COLOR_INFO}30;
            border-top: 3px solid {COLOR_INFO};
            border-radius: 50%;
            animation: workshop-spin 1s linear infinite;
            margin-right: 12px;
            flex-shrink: 0;
        "></div>
        <span style="font-size: 14px; color: #374151;">{message}</span>
    </div>
    '''


def display_code_block(
    code: str,
    language: str = "python",  # noqa: ARG001 - reserved for future syntax highlighting
    title: Optional[str] = None,
) -> None:
    """Display a styled code block.

    Args:
        code: Code to display
        language: Programming language for syntax hint (reserved for future use)
        title: Optional title for the code block
    """
    display, HTML = _get_display()

    # Escape HTML
    code_escaped = code.replace("<", "&lt;").replace(">", "&gt;")

    if display and HTML:
        title_html = ""
        if title:
            title_html = f'''
                <div style="
                    font-size: 12px;
                    font-weight: 600;
                    color: #6b7280;
                    padding: 8px 12px;
                    background-color: #e5e7eb;
                    border-radius: 8px 8px 0 0;
                ">{title}</div>
            '''

        html = f'''
        <div style="
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 8px 0;
        ">
            {title_html}
            <pre style="
                background-color: #1f2937;
                color: #f3f4f6;
                padding: 16px;
                border-radius: {'0 0 8px 8px' if title else '8px'};
                font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
                font-size: 13px;
                overflow-x: auto;
                margin: 0;
                line-height: 1.5;
            "><code>{code_escaped}</code></pre>
        </div>
        '''
        display(HTML(html))
    else:
        if title:
            print(f"--- {title} ---")
        print(code)


def display_step_indicator(
    current_step: int,
    total_steps: int,
    step_name: str,
    completed_steps: Optional[list[str]] = None,  # noqa: ARG001 - reserved for step labels
) -> None:
    """Display a workshop step progress indicator.

    Args:
        current_step: Current step number (1-indexed)
        total_steps: Total number of steps
        step_name: Name of the current step
        completed_steps: Optional list of completed step names (reserved for future use)
    """
    display, HTML = _get_display()

    if display and HTML:
        # Build step indicators
        step_indicators = []
        for i in range(1, total_steps + 1):
            if i < current_step:
                # Completed
                color = COLOR_SUCCESS
                icon = "\u2713"
            elif i == current_step:
                # Current
                color = COLOR_INFO
                icon = str(i)
            else:
                # Upcoming
                color = COLOR_NEUTRAL
                icon = str(i)

            step_indicators.append(f'''
                <div style="
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    background-color: {color};
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 600;
                    font-size: 14px;
                ">{icon}</div>
            ''')

        # Add connectors between steps
        connected_indicators = []
        for i, indicator in enumerate(step_indicators):
            connected_indicators.append(indicator)
            if i < len(step_indicators) - 1:
                connector_color = COLOR_SUCCESS if i < current_step - 1 else COLOR_NEUTRAL
                connected_indicators.append(f'''
                    <div style="
                        width: 40px;
                        height: 3px;
                        background-color: {connector_color};
                    "></div>
                ''')

        html = f'''
        <div style="
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 16px;
            background-color: #f9fafb;
            border-radius: 8px;
            max-width: 600px;
            margin: 8px 0;
        ">
            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0;
                margin-bottom: 16px;
            ">
                {''.join(connected_indicators)}
            </div>
            <div style="
                text-align: center;
                font-size: 16px;
                font-weight: 600;
                color: #1f2937;
            ">
                Step {current_step} of {total_steps}: {step_name}
            </div>
        </div>
        '''
        display(HTML(html))
    else:
        progress = "[" + "=" * current_step + " " * (total_steps - current_step) + "]"
        print(f"{progress} Step {current_step}/{total_steps}: {step_name}")
