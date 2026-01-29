"""Presenter mode utilities for workshop notebooks.

This module provides presenter-specific features for running workshop demos:
- Solution cells that are hidden by default but collapsible in presenter mode
- Demo timing markers for pacing presentations
- Fallback output management for offline/unreliable demo scenarios

IMPORTANT: Presenter mode is controlled by the WORKSHOP_PRESENTER_MODE
environment variable. When not in presenter mode, presenter-only content
is completely hidden (not just collapsed).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Optional


# Environment variable for presenter mode
PRESENTER_MODE_ENV_VAR = "WORKSHOP_PRESENTER_MODE"


def is_presenter_mode() -> bool:
    """Check if presenter mode is enabled.

    Presenter mode is enabled when WORKSHOP_PRESENTER_MODE=true.

    Returns:
        True if presenter mode is enabled, False otherwise
    """
    return os.getenv(PRESENTER_MODE_ENV_VAR, "false").lower() == "true"


def set_presenter_mode(enabled: bool) -> None:
    """Enable or disable presenter mode.

    Args:
        enabled: True to enable presenter mode, False to disable
    """
    os.environ[PRESENTER_MODE_ENV_VAR] = "true" if enabled else "false"


def _get_display():
    """Get IPython display function if available."""
    try:
        from IPython.display import display, HTML
        return display, HTML
    except ImportError:
        return None, None


def _escape_html(text: str) -> str:
    """Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text
    """
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def solution_cell(
    solution_code: str,
    explanation: str = "",
    language: str = "python",  # noqa: ARG001 - reserved for future syntax highlighting
) -> str:
    """Generate HTML for a collapsible solution cell.

    Args:
        solution_code: The solution code to display
        explanation: Optional explanation text
        language: Programming language for syntax hint (reserved for future highlighting)

    Returns:
        HTML string with collapsible details element
    """
    _ = language  # Reserved for future syntax highlighting support
    code_escaped = _escape_html(solution_code)

    explanation_html = ""
    if explanation:
        explanation_escaped = _escape_html(explanation)
        explanation_html = f'''
            <div style="
                margin-bottom: 12px;
                padding: 12px;
                background-color: #f0f9ff;
                border-radius: 6px;
                font-size: 14px;
                color: #0369a1;
                line-height: 1.5;
            ">{explanation_escaped}</div>
        '''

    return f'''
    <details style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 800px;
        margin: 16px 0;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
    ">
        <summary style="
            padding: 12px 16px;
            background-color: #f9fafb;
            cursor: pointer;
            font-weight: 600;
            color: #374151;
            border-bottom: 1px solid #e5e7eb;
            user-select: none;
        ">
            &#128274; Click to reveal solution
        </summary>
        <div style="padding: 16px;">
            {explanation_html}
            <pre style="
                background-color: #1f2937;
                color: #f3f4f6;
                padding: 16px;
                border-radius: 6px;
                font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
                font-size: 13px;
                overflow-x: auto;
                margin: 0;
                line-height: 1.5;
            "><code>{code_escaped}</code></pre>
        </div>
    </details>
    '''


def display_solution(
    solution_code: str,
    explanation: str = "",
    language: str = "python",
) -> None:
    """Display a collapsible solution cell.

    IMPORTANT: This only displays content if presenter mode is enabled.
    When not in presenter mode, this function is a no-op.

    Args:
        solution_code: The solution code to display
        explanation: Optional explanation text
        language: Programming language for syntax hint
    """
    if not is_presenter_mode():
        return

    display, HTML = _get_display()
    if display and HTML:
        html = solution_cell(solution_code, explanation, language)
        display(HTML(html))
    else:
        print("=== SOLUTION (Presenter Mode) ===")
        if explanation:
            print(explanation)
            print()
        print(solution_code)
        print("=================================")


# Marker type colors
MARKER_COLORS = {
    "action": "#3B82F6",   # Blue - main action
    "pause": "#8B5CF6",    # Purple - pause/discussion
    "optional": "#6B7280", # Gray - optional section
}


def demo_marker(
    duration_minutes: int,
    action: str,
    marker_type: str = "action",
) -> str:
    """Generate HTML for a demo timing marker.

    Args:
        duration_minutes: Estimated duration in minutes
        action: Description of the action/section
        marker_type: Type of marker - "action", "pause", or "optional"

    Returns:
        HTML string for the timing marker
    """
    color = MARKER_COLORS.get(marker_type, MARKER_COLORS["action"])

    type_icons = {
        "action": "&#9654;",   # Play triangle
        "pause": "&#9208;",    # Pause symbol
        "optional": "&#9998;", # Pencil/edit
    }
    icon = type_icons.get(marker_type, type_icons["action"])

    type_label = marker_type.upper()

    return f'''
    <div style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        background-color: {color}15;
        border-left: 3px solid {color};
        border-radius: 0 6px 6px 0;
        margin: 8px 0;
        font-size: 13px;
    ">
        <span style="color: {color}; font-size: 14px;">{icon}</span>
        <span style="
            font-weight: 600;
            color: {color};
            font-size: 11px;
            text-transform: uppercase;
        ">{type_label}</span>
        <span style="color: #4b5563;">{action}</span>
        <span style="
            background-color: {color};
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        ">{duration_minutes} min</span>
    </div>
    '''


def display_demo_marker(
    duration_minutes: int,
    action: str,
    marker_type: str = "action",
) -> None:
    """Display a demo timing marker.

    IMPORTANT: This only displays if presenter mode is enabled.
    When not in presenter mode, this function is a no-op.

    Args:
        duration_minutes: Estimated duration in minutes
        action: Description of the action/section
        marker_type: Type of marker - "action", "pause", or "optional"
    """
    if not is_presenter_mode():
        return

    display, HTML = _get_display()
    if display and HTML:
        html = demo_marker(duration_minutes, action, marker_type)
        display(HTML(html))
    else:
        prefix = {
            "action": "[ACTION]",
            "pause": "[PAUSE]",
            "optional": "[OPTIONAL]",
        }.get(marker_type, "[MARKER]")
        print(f"{prefix} {action} ({duration_minutes} min)")


class FallbackOutputManager:
    """Manages fallback outputs for offline or unreliable demos.

    Provides save/load functionality for pre-recorded demo outputs
    that can be used when live services are unavailable.

    Example:
        >>> manager = FallbackOutputManager()
        >>> manager.save("basic_query", {"data": [...], "sql": "SELECT..."})
        >>> # Later, or in offline mode:
        >>> result = manager.get("basic_query")
    """

    DEFAULT_DIR = "data/demo_fallbacks"

    def __init__(self, fallback_dir: Optional[str] = None) -> None:
        """Initialize the fallback manager.

        Args:
            fallback_dir: Directory for fallback files. If None, uses DEFAULT_DIR.
        """
        if fallback_dir:
            self._dir = Path(fallback_dir)
        else:
            self._dir = Path(self.DEFAULT_DIR)

        self._cache: dict[str, Any] = {}

        # Ensure directory exists
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Will handle on write

    def _get_path(self, name: str) -> Path:
        """Get the file path for a fallback.

        Args:
            name: Fallback name

        Returns:
            Path to the JSON file
        """
        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        return self._dir / f"{safe_name}.json"

    def get(self, name: str, default: Any = None) -> Any:
        """Get a fallback output by name.

        Args:
            name: Name of the fallback
            default: Default value if not found

        Returns:
            The fallback data, or default if not found
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        file_path = self._get_path(name)

        if not file_path.exists():
            return default

        try:
            json_str = file_path.read_text(encoding="utf-8")
            data = json.loads(json_str)
            self._cache[name] = data
            return data
        except (json.JSONDecodeError, OSError):
            return default

    def save(self, name: str, data: Any) -> str:
        """Save data as a fallback output.

        Args:
            name: Name for the fallback
            data: Data to save (must be JSON-serializable)

        Returns:
            Path where fallback was saved

        Raises:
            OSError: If unable to write file
            TypeError: If data is not JSON-serializable
        """
        self._dir.mkdir(parents=True, exist_ok=True)
        file_path = self._get_path(name)

        json_str = json.dumps(data, indent=2, default=str)
        file_path.write_text(json_str, encoding="utf-8")

        # Update cache
        self._cache[name] = data

        return str(file_path)

    def list_fallbacks(self) -> list[str]:
        """List all available fallback names.

        Returns:
            List of fallback names (without .json extension)
        """
        if not self._dir.exists():
            return []

        return [f.stem for f in sorted(self._dir.glob("*.json"))]

    def delete(self, name: str) -> bool:
        """Delete a fallback.

        Args:
            name: Name of the fallback to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_path(name)

        if file_path.exists():
            file_path.unlink()
            self._cache.pop(name, None)
            return True
        return False

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()


# Global singleton
_fallback_manager: Optional[FallbackOutputManager] = None


def get_fallback_manager() -> FallbackOutputManager:
    """Get the global FallbackOutputManager instance.

    Returns:
        The global FallbackOutputManager instance
    """
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = FallbackOutputManager()
    return _fallback_manager


def load_fallback_or_execute(
    name: str,
    live_function: Callable[[], Any],
    use_fallback: bool = False,
    save_on_success: bool = False,
) -> Any:
    """Execute a live function or load fallback if needed.

    This is the primary interface for graceful degradation:
    1. If use_fallback is True, load from fallback
    2. Otherwise, try live execution
    3. If live fails and fallback exists, use fallback
    4. Optionally save successful live results as fallback

    Args:
        name: Name for the fallback
        live_function: Function to execute for live results
        use_fallback: If True, skip live execution and use fallback
        save_on_success: If True, save successful live results

    Returns:
        The result (either live or fallback)

    Raises:
        Exception: If both live execution fails and no fallback exists
    """
    manager = get_fallback_manager()

    # Force fallback mode
    if use_fallback:
        fallback = manager.get(name)
        if fallback is not None:
            return fallback
        # Fall through to try live if no fallback exists

    # Try live execution
    try:
        result = live_function()

        # Save on success if requested
        if save_on_success and result is not None:
            try:
                manager.save(name, result)
            except (TypeError, OSError):
                pass  # Don't fail if we can't save

        return result

    except Exception as e:
        # Try fallback on failure
        fallback = manager.get(name)
        if fallback is not None:
            # Optionally log that we're using fallback
            print(f"Using fallback for '{name}' (live execution failed: {e})")
            return fallback

        # Re-raise if no fallback
        raise


def display_presenter_controls() -> None:
    """Display presenter mode controls and status.

    Shows the current presenter mode status and provides
    instructions for toggling it.
    """
    display, HTML = _get_display()

    is_enabled = is_presenter_mode()
    status_color = "#10B981" if is_enabled else "#6B7280"
    status_text = "ENABLED" if is_enabled else "DISABLED"
    status_icon = "&#9989;" if is_enabled else "&#10060;"

    if display and HTML:
        html = f'''
        <div style="
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 16px 0;
            padding: 16px;
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        ">
            <div style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
            ">
                <span style="font-weight: 600; color: #1f2937;">
                    Presenter Mode
                </span>
                <span style="
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 4px 10px;
                    background-color: {status_color};
                    color: white;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                ">
                    {status_icon} {status_text}
                </span>
            </div>
            <div style="font-size: 13px; color: #6b7280; line-height: 1.5;">
                <p style="margin: 0 0 8px 0;">
                    Presenter mode shows solution cells, timing markers, and other
                    presenter-only content.
                </p>
                <p style="margin: 0;">
                    Toggle with: <code>set_presenter_mode(True)</code> or
                    <code>set_presenter_mode(False)</code>
                </p>
            </div>
        </div>
        '''
        display(HTML(html))
    else:
        print(f"Presenter Mode: {status_text}")
        print(f"Toggle with: set_presenter_mode(True/False)")
