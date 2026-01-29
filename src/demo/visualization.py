"""Visualization utilities for the advanced demo notebook.

This module provides functions to generate visual representations of
pipeline state for display in Jupyter/Databricks notebooks.

Phase 1: Text/Markdown-based visualizations (always work)
Phase 2+: HTML progress cards, Mermaid diagrams (progressive enhancement)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.demo.pipeline import PipelineState


# Status indicators for text display
STATUS_ICONS = {
    "idle": "",
    "pending": "",
    "querying": "",
    "retrying": "",
    "complete": "",
    "error": "",
    "timeout": "",
    "circuit_open": "",
    "planning": "",
    "synthesizing": "",
    "reporting": "",
}


def generate_stage_progress_text(state: PipelineState) -> str:
    """Generate text-based stage progress indicator.

    Args:
        state: Current pipeline state

    Returns:
        Formatted text showing pipeline stage progress
    """
    from src.demo.pipeline import PipelineStage

    stages = [
        PipelineStage.PLANNING,
        PipelineStage.QUERYING,
        PipelineStage.SYNTHESIZING,
        PipelineStage.REPORTING,
    ]

    lines = ["## Pipeline Progress", ""]

    for stage in stages:
        result = state.get_stage_result(stage)

        if result is None:
            # Not started
            icon = ""
            status = "Pending"
            timing = ""
        elif result.end_time is None:
            # In progress
            icon = ""
            status = "Running..."
            timing = ""
        elif result.success:
            # Complete
            icon = ""
            status = "Complete"
            timing = f" ({result.duration_seconds:.2f}s)" if result.duration_seconds else ""
        else:
            # Failed
            icon = ""
            status = f"Failed: {result.error or 'Unknown error'}"
            timing = ""

        lines.append(f"{icon} **{stage.value.title()}**: {status}{timing}")

    # Add total time if available
    total = state.total_duration_seconds
    if total is not None:
        lines.append("")
        lines.append(f"**Total Time**: {total:.2f}s")

    return "\n".join(lines)


def generate_space_progress_text(state: PipelineState) -> str:
    """Generate text-based space query progress.

    Args:
        state: Current pipeline state

    Returns:
        Formatted text showing per-space query progress
    """
    from src.demo.pipeline import SpaceQueryStatus

    space_progress = state.get_space_progress()
    if not space_progress:
        return "_No spaces configured_"

    lines = ["## Genie Space Queries", ""]

    for name, progress in space_progress.items():
        # Status icon
        status_map = {
            SpaceQueryStatus.PENDING: ("", "Pending"),
            SpaceQueryStatus.QUERYING: ("", "Querying"),
            SpaceQueryStatus.RETRYING: ("", "Retrying"),
            SpaceQueryStatus.COMPLETE: ("", "Complete"),
            SpaceQueryStatus.ERROR: ("", "Error"),
            SpaceQueryStatus.TIMEOUT: ("", "Timeout"),
            SpaceQueryStatus.CIRCUIT_OPEN: ("", "Circuit Open"),
        }

        icon, status_text = status_map.get(progress.status, ("", "Unknown"))

        # Build status line
        parts = [f"{icon} **{name}**: {status_text}"]

        # Add attempt info if retrying
        if progress.current_attempt > 1:
            parts.append(f"(attempt {progress.current_attempt})")

        # Add timing if available
        duration = progress.duration_seconds
        if duration is not None:
            parts.append(f"- {duration:.2f}s")

        # Add cache indicator
        if progress.cached:
            parts.append("[cached]")

        # Add error message if present
        if progress.error_message:
            parts.append(f"- {progress.error_message}")

        lines.append(" ".join(parts))

    return "\n".join(lines)


def generate_timing_table(state: PipelineState, format: str = "markdown") -> str:
    """Generate timing statistics table.

    Args:
        state: Current pipeline state
        format: Output format ("markdown" or "text")

    Returns:
        Formatted timing table
    """
    timing = state.get_timing_summary()

    if format == "markdown":
        return _generate_timing_table_markdown(timing)
    else:
        return _generate_timing_table_text(timing)


def _generate_timing_table_markdown(timing: dict) -> str:
    """Generate Markdown timing table."""
    lines = [
        "## Execution Timing",
        "",
        "### Pipeline Stages",
        "",
        "| Stage | Duration (s) | Status |",
        "|-------|-------------|--------|",
    ]

    for stage_name, stage_data in timing.get("stages", {}).items():
        duration = stage_data.get("duration_seconds")
        duration_str = f"{duration:.2f}" if duration is not None else "-"
        success = stage_data.get("success", False)
        error = stage_data.get("error")

        if error:
            status = f"Failed: {error[:30]}..."
        elif success:
            status = "Complete"
        elif duration is None:
            status = "Pending"
        else:
            status = "Running"

        lines.append(f"| {stage_name.title()} | {duration_str} | {status} |")

    # Add total
    total = timing.get("total_duration_seconds")
    if total is not None:
        lines.append(f"| **Total** | **{total:.2f}** | - |")

    # Space timings
    spaces = timing.get("spaces", {})
    if spaces:
        lines.extend(
            [
                "",
                "### Genie Space Queries",
                "",
                "| Space | Duration (s) | Attempts | Status |",
                "|-------|-------------|----------|--------|",
            ]
        )

        for name, space_data in spaces.items():
            duration = space_data.get("duration_seconds")
            duration_str = f"{duration:.2f}" if duration is not None else "-"
            attempts = space_data.get("current_attempt", 0)
            status = space_data.get("status", "unknown").title()

            if space_data.get("cached"):
                status += " (cached)"

            lines.append(f"| {name} | {duration_str} | {attempts} | {status} |")

    return "\n".join(lines)


def _generate_timing_table_text(timing: dict) -> str:
    """Generate plain text timing table."""
    lines = [
        "EXECUTION TIMING",
        "=" * 50,
        "",
        "Pipeline Stages:",
    ]

    for stage_name, stage_data in timing.get("stages", {}).items():
        duration = stage_data.get("duration_seconds")
        duration_str = f"{duration:.2f}s" if duration is not None else "-"
        success = stage_data.get("success", False)
        status = "OK" if success else "FAIL" if duration is not None else "PENDING"
        lines.append(f"  {stage_name.title()}: {duration_str} [{status}]")

    total = timing.get("total_duration_seconds")
    if total is not None:
        lines.append(f"  Total: {total:.2f}s")

    spaces = timing.get("spaces", {})
    if spaces:
        lines.extend(["", "Genie Space Queries:"])
        for name, space_data in spaces.items():
            duration = space_data.get("duration_seconds")
            duration_str = f"{duration:.2f}s" if duration is not None else "-"
            status = space_data.get("status", "unknown").upper()
            lines.append(f"  {name}: {duration_str} [{status}]")

    return "\n".join(lines)


def generate_pipeline_diagram_text(state: PipelineState) -> str:
    """Generate text-based pipeline diagram (ASCII art fallback).

    This is the Phase 1 fallback when Mermaid is not available.

    Args:
        state: Current pipeline state

    Returns:
        ASCII art pipeline diagram
    """
    from src.demo.pipeline import PipelineStage

    def get_box(stage: PipelineStage) -> str:
        result = state.get_stage_result(stage)
        name = stage.value.title()

        if result is None:
            return f"[ {name} ]"  # Pending
        elif result.end_time is None:
            return f"[*{name}*]"  # Running
        elif result.success:
            return f"[+{name}+]"  # Complete
        else:
            return f"[!{name}!]"  # Error

    stages = [
        PipelineStage.PLANNING,
        PipelineStage.QUERYING,
        PipelineStage.SYNTHESIZING,
        PipelineStage.REPORTING,
    ]

    boxes = [get_box(s) for s in stages]
    arrows = " --> "

    diagram = arrows.join(boxes)

    legend = """
Legend: [ ] Pending  [* *] Running  [+ +] Complete  [! !] Error
"""

    return f"```\n{diagram}\n```\n{legend}"


def generate_mermaid_diagram(state: PipelineState) -> str:
    """Generate Mermaid flowchart diagram of pipeline stages.

    Note: Mermaid rendering requires JS support in the notebook.
    Use generate_pipeline_diagram_text() as fallback.

    Args:
        state: Current pipeline state

    Returns:
        Mermaid diagram code (to be wrapped for rendering)
    """
    from src.demo.pipeline import PipelineStage

    lines = [
        "```mermaid",
        "flowchart LR",
    ]

    stages = [
        ("A", PipelineStage.PLANNING),
        ("B", PipelineStage.QUERYING),
        ("C", PipelineStage.SYNTHESIZING),
        ("D", PipelineStage.REPORTING),
    ]

    # Add nodes with status-based styling
    for node_id, stage in stages:
        result = state.get_stage_result(stage)
        name = stage.value.title()

        if result is None:
            css_class = "pending"
        elif result.end_time is None:
            css_class = "active"
        elif result.success:
            css_class = "complete"
        else:
            css_class = "error"

        lines.append(f"    {node_id}[{name}]:::{css_class}")

    # Add edges
    lines.append("    A --> B --> C --> D")

    # Add class definitions
    lines.extend(
        [
            "",
            "    classDef pending fill:#6B7280,color:white",
            "    classDef active fill:#3B82F6,color:white",
            "    classDef complete fill:#10B981,color:white",
            "    classDef error fill:#EF4444,color:white",
        ]
    )

    lines.append("```")

    return "\n".join(lines)


def render_for_notebook(
    state: PipelineState,
    include_diagram: bool = True,
    include_spaces: bool = True,
    include_timing: bool = True,
) -> str:
    """Generate complete Markdown output for notebook display.

    Combines multiple visualizations into a single Markdown string
    suitable for display with IPython.display.Markdown().

    Args:
        state: Current pipeline state
        include_diagram: Include pipeline diagram
        include_spaces: Include space query progress
        include_timing: Include timing table

    Returns:
        Combined Markdown string
    """
    sections = []

    if include_diagram:
        sections.append(generate_stage_progress_text(state))

    if include_spaces:
        space_text = generate_space_progress_text(state)
        if space_text:
            sections.append(space_text)

    if include_timing and state.total_duration_seconds is not None:
        sections.append(generate_timing_table(state, format="markdown"))

    return "\n\n---\n\n".join(sections)


def render_progress_html(
    state: PipelineState,
    cache_stats: dict | None = None,
) -> str:
    """Generate HTML progress visualization using Jinja2 templates.

    Phase 2: HTML progress cards with color-coded status indicators.

    Args:
        state: Current pipeline state
        cache_stats: Optional cache statistics dictionary

    Returns:
        HTML string for display with IPython.display.HTML()
    """
    from src.demo.pipeline import PipelineStage

    try:
        import jinja2

        env = jinja2.Environment(
            loader=jinja2.PackageLoader("src", "templates"),
            autoescape=True,
        )
        template = env.get_template("demo/pipeline_progress.html.jinja2")

    except Exception:
        # Fallback to inline HTML if templates unavailable
        return _render_progress_html_inline(state, cache_stats)

    # Build stage data
    stage_order = [
        PipelineStage.PLANNING,
        PipelineStage.QUERYING,
        PipelineStage.SYNTHESIZING,
        PipelineStage.REPORTING,
    ]

    stages = []
    for stage in stage_order:
        result = state.get_stage_result(stage)
        if result is None:
            status = "pending"
            duration = None
            error = None
        elif result.end_time is None:
            status = "running"
            duration = None
            error = None
        elif result.success:
            status = "complete"
            duration = result.duration_seconds
            error = None
        else:
            status = "error"
            duration = result.duration_seconds
            error = result.error

        stages.append(
            {
                "name": stage.value.title(),
                "status": status,
                "duration": duration,
                "error": error,
            }
        )

    # Build space data
    spaces = []
    for name, progress in state.get_space_progress().items():
        spaces.append(
            {
                "name": name,
                "status": progress.status.value,
                "duration": progress.duration_seconds,
                "attempt": progress.current_attempt,
                "cached": progress.cached,
                "error": progress.error_message,
            }
        )

    return template.render(
        stages=stages,
        spaces=spaces,
        total_duration=state.total_duration_seconds,
        cache_stats=cache_stats,
    )


def _render_progress_html_inline(
    state: PipelineState,
    cache_stats: dict | None = None,
) -> str:
    """Inline HTML fallback when templates are unavailable."""
    from src.demo.pipeline import PipelineStage

    status_colors = {
        "pending": "#6B7280",
        "running": "#3B82F6",
        "complete": "#10B981",
        "error": "#EF4444",
    }

    stage_order = [
        PipelineStage.PLANNING,
        PipelineStage.QUERYING,
        PipelineStage.SYNTHESIZING,
        PipelineStage.REPORTING,
    ]

    # Build stage cards
    stage_html = []
    for i, stage in enumerate(stage_order):
        result = state.get_stage_result(stage)
        if result is None:
            status, duration = "pending", None
        elif result.end_time is None:
            status, duration = "running", None
        elif result.success:
            status, duration = "complete", result.duration_seconds
        else:
            status, duration = "error", result.duration_seconds

        color = status_colors.get(status, "#6B7280")
        duration_str = f"{duration:.2f}s" if duration else status.title()

        stage_html.append(f"""
        <div style="display:inline-block;padding:12px 16px;margin:4px;border-radius:8px;
                    background-color:{color}20;border-left:4px solid {color};min-width:120px;">
            <div style="font-size:14px;font-weight:600;color:{color};">{stage.value.title()}</div>
            <div style="font-size:12px;color:#666;margin-top:4px;">{duration_str}</div>
        </div>
        """)
        if i < len(stage_order) - 1:
            stage_html.append('<span style="color:#9CA3AF;font-size:18px;margin:0 4px;">&#8594;</span>')

    # Build space cards
    space_html = []
    for name, progress in state.get_space_progress().items():
        status = progress.status.value
        color = status_colors.get(status, status_colors.get("pending"))
        duration_str = f"{progress.duration_seconds:.2f}s" if progress.duration_seconds else status.title()

        space_html.append(f"""
        <div style="display:flex;align-items:center;padding:8px 12px;margin:2px 0;
                    background-color:{color}10;border-radius:4px;font-size:13px;">
            <div style="width:10px;height:10px;border-radius:50%;background-color:{color};margin-right:10px;"></div>
            <div style="flex:1;font-weight:500;">{name}</div>
            <div style="color:#666;margin-left:8px;">{duration_str}</div>
        </div>
        """)

    # Total time and cache stats
    total_html = ""
    if state.total_duration_seconds is not None:
        cache_info = ""
        if cache_stats:
            hits = cache_stats.get("hits", 0)
            misses = cache_stats.get("misses", 0)
            cache_info = f" &nbsp;|&nbsp; <strong>Cache:</strong> {hits} hits, {misses} misses"
        total_html = f"""
        <div style="margin-top:16px;padding:12px;background-color:#F3F4F6;border-radius:6px;font-size:14px;">
            <strong>Total Time:</strong> {state.total_duration_seconds:.2f}s{cache_info}
        </div>
        """

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:800px;padding:16px;">
        <div style="font-size:14px;font-weight:600;color:#374151;margin:16px 0 8px 0;padding-bottom:4px;border-bottom:1px solid #E5E7EB;">
            Pipeline Progress
        </div>
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:4px;">
            {"".join(stage_html)}
        </div>
        <div style="font-size:14px;font-weight:600;color:#374151;margin:16px 0 8px 0;padding-bottom:4px;border-bottom:1px solid #E5E7EB;">
            Genie Space Queries
        </div>
        <div>
            {"".join(space_html)}
        </div>
        {total_html}
    </div>
    """
