"""Demo utilities for the advanced Jupyter notebook.

This package provides state management and visualization utilities for
demonstrating multi-Genie orchestration in Databricks notebooks.

Pipeline State Management:
- PipelineState: Thread-safe state tracking with progress_callback support
- PipelineStage: Enum of pipeline execution stages
- SpaceQueryStatus: Enum of Genie Space query states
- SpaceProgress: Dataclass for tracking individual space queries
- StageResult: Dataclass for tracking stage execution results

Visualization Functions:
- render_for_notebook: Complete Markdown output for notebook display
- generate_stage_progress_text: Text-based stage progress indicator
- generate_space_progress_text: Text-based space query progress
- generate_timing_table: Timing statistics table (Markdown or text)
- generate_pipeline_diagram_text: ASCII art pipeline diagram
- generate_mermaid_diagram: Mermaid flowchart (Phase 2+)
"""

from src.demo.pipeline import (
    PipelineState,
    PipelineStage,
    SpaceQueryStatus,
    SpaceProgress,
    StageResult,
)

from src.demo.visualization import (
    render_for_notebook,
    render_progress_html,
    generate_stage_progress_text,
    generate_space_progress_text,
    generate_timing_table,
    generate_pipeline_diagram_text,
    generate_mermaid_diagram,
)

from src.demo.widgets import (
    WidgetConfig,
    DatabricksWidgets,
    LocalWidgets,
    create_widget_manager,
    get_question_for_report_type,
    is_databricks,
)

__all__ = [
    # Pipeline state management
    "PipelineState",
    "PipelineStage",
    "SpaceQueryStatus",
    "SpaceProgress",
    "StageResult",
    # Visualization functions
    "render_for_notebook",
    "render_progress_html",
    "generate_stage_progress_text",
    "generate_space_progress_text",
    "generate_timing_table",
    "generate_pipeline_diagram_text",
    "generate_mermaid_diagram",
    # Widget utilities
    "WidgetConfig",
    "DatabricksWidgets",
    "LocalWidgets",
    "create_widget_manager",
    "get_question_for_report_type",
    "is_databricks",
]
