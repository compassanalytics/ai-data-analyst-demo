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

Checkpoint System:
- Checkpoint: Dataclass for saved state snapshots
- CheckpointManager: Storage and retrieval of checkpoints
- create_checkpoint: Convenience function to create/save checkpoints
- display_checkpoint_widget: Interactive checkpoint selection

Feedback Utilities:
- display_success: Green success banner
- display_error: Red error banner with suggestions
- display_warning: Amber warning banner
- display_info: Blue info banner
- compare_output: Side-by-side output comparison
- display_progress_spinner: CSS animated spinner

Challenge Framework:
- Difficulty: Enum of challenge difficulty levels (EASY, MEDIUM, HARD)
- Challenge: Dataclass for defining workshop challenges
- ChallengeRunner: Class for managing challenge execution and hints
- DEMO_CHALLENGES: Pre-defined challenges for 01_agent_basics.ipynb
- ADVANCED_CHALLENGES: Pre-defined challenges for 02_multi_genie_orchestration.ipynb
- run_challenge: Convenience function for one-liner validation

Presenter Mode:
- is_presenter_mode: Check if presenter mode is enabled
- set_presenter_mode: Enable/disable presenter mode
- display_solution: Show collapsible solution cells (presenter only)
- display_demo_marker: Show timing annotations (presenter only)
- FallbackOutputManager: Manage fallback outputs for offline demos
- load_fallback_or_execute: Execute with fallback support
"""

from src.demo.challenges import (
    ADVANCED_CHALLENGES,
    DEMO_CHALLENGES,
    Challenge,
    ChallengeRunner,
    Difficulty,
    get_challenge_runner,
    run_challenge,
)
from src.demo.checkpoints import (
    CHECKPOINT_BASIC_QUERY,
    CHECKPOINT_MULTI_AGENT,
    CHECKPOINT_REPORT_GENERATED,
    CHECKPOINT_SETUP,
    Checkpoint,
    CheckpointManager,
    create_checkpoint,
    display_checkpoint_widget,
)
from src.demo.feedback import (
    compare_output,
    display_code_block,
    display_error,
    display_info,
    display_progress_spinner,
    display_step_indicator,
    display_success,
    display_warning,
)
from src.demo.pipeline import (
    PipelineStage,
    PipelineState,
    SpaceProgress,
    SpaceQueryStatus,
    StageResult,
)
from src.demo.presenter import (
    FallbackOutputManager,
    demo_marker,
    display_demo_marker,
    display_presenter_controls,
    display_solution,
    get_fallback_manager,
    is_presenter_mode,
    load_fallback_or_execute,
    set_presenter_mode,
    solution_cell,
)
from src.demo.visualization import (
    generate_mermaid_diagram,
    generate_pipeline_diagram_text,
    generate_space_progress_text,
    generate_stage_progress_text,
    generate_timing_table,
    render_for_notebook,
    render_progress_html,
)
from src.demo.widgets import (
    DatabricksWidgets,
    LocalWidgets,
    WidgetConfig,
    create_widget_manager,
    get_question_for_report_type,
    is_databricks,
    is_serverless,
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
    "is_serverless",
    # Checkpoint system
    "Checkpoint",
    "CheckpointManager",
    "CHECKPOINT_SETUP",
    "CHECKPOINT_BASIC_QUERY",
    "CHECKPOINT_MULTI_AGENT",
    "CHECKPOINT_REPORT_GENERATED",
    "create_checkpoint",
    "display_checkpoint_widget",
    # Feedback utilities
    "display_success",
    "display_error",
    "display_warning",
    "display_info",
    "compare_output",
    "display_progress_spinner",
    "display_code_block",
    "display_step_indicator",
    # Challenge framework
    "Difficulty",
    "Challenge",
    "ChallengeRunner",
    "DEMO_CHALLENGES",
    "ADVANCED_CHALLENGES",
    "get_challenge_runner",
    "run_challenge",
    # Presenter mode
    "is_presenter_mode",
    "set_presenter_mode",
    "solution_cell",
    "display_solution",
    "demo_marker",
    "display_demo_marker",
    "FallbackOutputManager",
    "get_fallback_manager",
    "load_fallback_or_execute",
    "display_presenter_controls",
]
