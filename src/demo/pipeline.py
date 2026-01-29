"""Pipeline state management for the advanced demo notebook.

This module provides thread-safe state tracking for the multi-agent pipeline,
integrating with MultiGenieOrchestrator's progress_callback mechanism.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.agents.multi_genie_orchestrator import MultiGenieResult
    from src.agents.planner_agent import Plan
    from src.agents.synthesizer_agent import SynthesisResult


class PipelineStage(Enum):
    """Pipeline execution stages."""

    IDLE = "idle"
    PLANNING = "planning"
    QUERYING = "querying"
    SYNTHESIZING = "synthesizing"
    REPORTING = "reporting"
    COMPLETE = "complete"
    ERROR = "error"


class SpaceQueryStatus(Enum):
    """Status of individual Genie Space queries."""

    PENDING = "pending"
    QUERYING = "querying"
    RETRYING = "retrying"
    COMPLETE = "complete"
    ERROR = "error"
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class SpaceProgress:
    """Progress tracking for a single Genie Space query.

    Attributes:
        space_name: Human-readable name of the space
        status: Current query status
        start_time: When the query started (epoch seconds)
        end_time: When the query completed (epoch seconds)
        current_attempt: Current retry attempt number
        error_message: Error message if failed
        cached: Whether result was served from cache
    """

    space_name: str
    status: SpaceQueryStatus = SpaceQueryStatus.PENDING
    start_time: float | None = None
    end_time: float | None = None
    current_attempt: int = 0
    error_message: str | None = None
    cached: bool = False

    @property
    def duration_seconds(self) -> float | None:
        """Calculate query duration in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display and serialization."""
        return {
            "space_name": self.space_name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "current_attempt": self.current_attempt,
            "error_message": self.error_message,
            "cached": self.cached,
        }


@dataclass
class StageResult:
    """Result and timing for a pipeline stage."""

    stage: PipelineStage
    start_time: float
    end_time: float | None = None
    success: bool = False
    error: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Calculate stage duration in seconds."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stage": self.stage.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "success": self.success,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageResult:
        """Restore from dictionary."""
        return cls(
            stage=PipelineStage(data["stage"]),
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            success=data.get("success", False),
            error=data.get("error"),
        )


class PipelineState:
    """Thread-safe state tracking for the multi-agent demo pipeline.

    Integrates with MultiGenieOrchestrator's progress_callback mechanism
    to track query progress across multiple Genie Spaces.

    Example:
        >>> state = PipelineState()
        >>> orchestrator = MultiGenieOrchestrator(
        ...     space_configs=configs,
        ...     progress_callback=state.get_progress_callback(),
        ... )
        >>> state.start_stage(PipelineStage.QUERYING)
        >>> result = orchestrator.query_all(question)
        >>> state.reconcile_from_result(result)
        >>> state.complete_stage(PipelineStage.QUERYING)
    """

    def __init__(self) -> None:
        """Initialize pipeline state."""
        self._lock = threading.Lock()
        self._current_stage = PipelineStage.IDLE
        self._stage_results: dict[PipelineStage, StageResult] = {}
        self._space_progress: dict[str, SpaceProgress] = {}
        self._pipeline_start: float | None = None
        self._pipeline_end: float | None = None

        # Intermediate results (set by notebook code, not callbacks)
        self.plan: Plan | None = None
        self.multi_result: MultiGenieResult | None = None
        self.synthesis_result: SynthesisResult | None = None
        self.markdown_report: str | None = None
        self.html_report: str | None = None
        self.errors: list[str] = []

    @property
    def current_stage(self) -> PipelineStage:
        """Get current pipeline stage (thread-safe)."""
        with self._lock:
            return self._current_stage

    @property
    def is_running(self) -> bool:
        """Check if pipeline is currently executing."""
        return self.current_stage not in (
            PipelineStage.IDLE,
            PipelineStage.COMPLETE,
            PipelineStage.ERROR,
        )

    @property
    def total_duration_seconds(self) -> float | None:
        """Get total pipeline duration in seconds."""
        if self._pipeline_start is None:
            return None
        end = self._pipeline_end or time.time()
        return end - self._pipeline_start

    def initialize_spaces(self, space_names: list[str]) -> None:
        """Initialize progress tracking for spaces.

        Args:
            space_names: List of Genie Space names to track
        """
        with self._lock:
            self._space_progress = {name: SpaceProgress(space_name=name) for name in space_names}

    def start_stage(self, stage: PipelineStage) -> None:
        """Mark a stage as started.

        Args:
            stage: The pipeline stage to start
        """
        with self._lock:
            now = time.time()
            if self._pipeline_start is None:
                self._pipeline_start = now

            self._current_stage = stage
            self._stage_results[stage] = StageResult(stage=stage, start_time=now)

    def complete_stage(self, stage: PipelineStage, success: bool = True) -> None:
        """Mark a stage as completed.

        Args:
            stage: The stage that completed
            success: Whether the stage succeeded
        """
        with self._lock:
            if stage in self._stage_results:
                self._stage_results[stage].end_time = time.time()
                self._stage_results[stage].success = success

            if stage == PipelineStage.REPORTING:
                self._current_stage = PipelineStage.COMPLETE
                self._pipeline_end = time.time()

    def fail_stage(self, stage: PipelineStage, error: str) -> None:
        """Mark a stage as failed.

        Args:
            stage: The stage that failed
            error: Error message
        """
        with self._lock:
            if stage in self._stage_results:
                self._stage_results[stage].end_time = time.time()
                self._stage_results[stage].success = False
                self._stage_results[stage].error = error

            self._current_stage = PipelineStage.ERROR
            self._pipeline_end = time.time()
            self.errors.append(f"[{stage.value}] {error}")

    def get_progress_callback(self) -> Callable[[str, str], None]:
        """Get a progress callback compatible with MultiGenieOrchestrator.

        The callback only mutates state; it does NOT render UI.
        Rendering should be done from the main thread after query completion.

        Returns:
            Callback function with signature (space_name: str, status: str) -> None
        """

        def callback(space_name: str, status: str) -> None:
            self._update_space_from_callback(space_name, status)

        return callback

    def _update_space_from_callback(self, space_name: str, status: str) -> None:
        """Update space progress from orchestrator callback.

        Normalizes string status messages to SpaceQueryStatus enum.

        Args:
            space_name: Name of the space
            status: Status string from orchestrator (e.g., "Querying (attempt 1)")
        """
        with self._lock:
            if space_name not in self._space_progress:
                self._space_progress[space_name] = SpaceProgress(space_name=space_name)

            progress = self._space_progress[space_name]

            # Normalize status strings to enum
            status_lower = status.lower()

            if "querying" in status_lower:
                progress.status = SpaceQueryStatus.QUERYING
                if progress.start_time is None:
                    progress.start_time = time.time()
                # Extract attempt number: "Querying (attempt N)"
                if "attempt" in status_lower:
                    try:
                        attempt_str = status.split("attempt")[1].strip().rstrip(")")
                        progress.current_attempt = int(attempt_str)
                    except (ValueError, IndexError):
                        pass

            elif "retrying" in status_lower:
                progress.status = SpaceQueryStatus.RETRYING

            elif status_lower == "complete":
                progress.status = SpaceQueryStatus.COMPLETE
                progress.end_time = time.time()

            elif "failed" in status_lower:
                progress.status = SpaceQueryStatus.ERROR
                progress.end_time = time.time()
                if "non-retryable" in status_lower:
                    progress.error_message = "Non-retryable error"

            elif "timeout" in status_lower:
                progress.status = SpaceQueryStatus.TIMEOUT
                progress.end_time = time.time()

            elif "circuit" in status_lower:
                progress.status = SpaceQueryStatus.CIRCUIT_OPEN
                progress.end_time = time.time()

    def reconcile_from_result(self, result: MultiGenieResult) -> None:
        """Reconcile space progress from final MultiGenieResult.

        This ensures accurate final state even if callbacks were missed
        (e.g., timeouts, circuit breaker rejections).

        Args:
            result: The MultiGenieResult from query execution
        """
        with self._lock:
            for name, metadata in result.metadata.items():
                if name not in self._space_progress:
                    self._space_progress[name] = SpaceProgress(space_name=name)

                progress = self._space_progress[name]

                # Set final status from metadata
                if metadata.success:
                    progress.status = SpaceQueryStatus.COMPLETE
                else:
                    # Determine specific failure type
                    if metadata.error_category:
                        category = metadata.error_category.value
                        if category == "timeout":
                            progress.status = SpaceQueryStatus.TIMEOUT
                        elif category == "circuit_open":
                            progress.status = SpaceQueryStatus.CIRCUIT_OPEN
                        else:
                            progress.status = SpaceQueryStatus.ERROR
                    else:
                        progress.status = SpaceQueryStatus.ERROR

                # Always use metadata timing as authoritative source
                # (callbacks may have race conditions with ThreadPoolExecutor)
                if metadata.query_time_seconds > 0:
                    now = time.time()
                    progress.start_time = now - metadata.query_time_seconds
                    progress.end_time = now

                progress.current_attempt = metadata.retries_used + 1
                progress.cached = metadata.cached

            # Capture errors from result
            for name, genie_result in result.results.items():
                if not genie_result.success and name in self._space_progress:
                    self._space_progress[name].error_message = genie_result.error

    def get_space_progress(self) -> dict[str, SpaceProgress]:
        """Get copy of all space progress (thread-safe).

        Returns:
            Dictionary of space name to SpaceProgress
        """
        with self._lock:
            return {k: v for k, v in self._space_progress.items()}

    def get_stage_result(self, stage: PipelineStage) -> StageResult | None:
        """Get result for a specific stage.

        Args:
            stage: The stage to get result for

        Returns:
            StageResult if stage has been started, None otherwise
        """
        with self._lock:
            return self._stage_results.get(stage)

    def get_timing_summary(self) -> dict[str, Any]:
        """Get timing summary for all stages and spaces.

        Returns:
            Dictionary with stage timings, space timings, and totals
        """
        with self._lock:
            stage_timings = {}
            for stage, result in self._stage_results.items():
                stage_timings[stage.value] = {
                    "duration_seconds": result.duration_seconds,
                    "success": result.success,
                    "error": result.error,
                }

            space_timings = {}
            for name, progress in self._space_progress.items():
                space_timings[name] = progress.to_dict()

            return {
                "stages": stage_timings,
                "spaces": space_timings,
                "total_duration_seconds": self.total_duration_seconds,
                "current_stage": self._current_stage.value,
            }

    def reset(self) -> None:
        """Reset all state for a new pipeline run."""
        with self._lock:
            self._current_stage = PipelineStage.IDLE
            self._stage_results.clear()
            self._space_progress.clear()
            self._pipeline_start = None
            self._pipeline_end = None
            self.plan = None
            self.multi_result = None
            self.synthesis_result = None
            self.markdown_report = None
            self.html_report = None
            self.errors.clear()

    def to_dict(self, include_results: bool = False) -> dict[str, Any]:
        """Serialize state for display/logging/checkpointing.

        Args:
            include_results: If True, include serializable stage_results and space_progress
                           for checkpoint restoration. Defaults to False for backward compatibility.

        Returns:
            Dictionary representation of pipeline state
        """
        base_dict = {
            "current_stage": self.current_stage.value,
            "is_running": self.is_running,
            "timing": self.get_timing_summary(),
            "has_plan": self.plan is not None,
            "has_results": self.multi_result is not None,
            "has_synthesis": self.synthesis_result is not None,
            "has_markdown": self.markdown_report is not None,
            "has_html": self.html_report is not None,
            "errors": list(self.errors),  # Copy to avoid reference issues
        }

        if include_results:
            # Include serializable data for checkpoint restoration
            with self._lock:
                base_dict["stage_results"] = {
                    stage.value: result.to_dict() for stage, result in self._stage_results.items()
                }
                base_dict["space_progress"] = {
                    name: progress.to_dict() for name, progress in self._space_progress.items()
                }
                base_dict["pipeline_start"] = self._pipeline_start
                base_dict["pipeline_end"] = self._pipeline_end

        return base_dict

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineState:
        """Restore PipelineState from dictionary.

        Creates a new PipelineState with a fresh threading.Lock, then restores
        safe fields from the serialized data.

        CRITICAL: If the restored current_stage indicates a running state
        (PLANNING, QUERYING, SYNTHESIZING, REPORTING), it is forced to IDLE
        to prevent zombie state bugs.

        Args:
            data: Dictionary from to_dict(include_results=True)

        Returns:
            New PipelineState instance with restored data
        """
        # Create fresh instance (initializes new lock)
        state = cls()

        # Restore current_stage with sanitization
        current_stage_value = data.get("current_stage", "idle")
        current_stage = PipelineStage(current_stage_value)

        # Sanitize: if state indicates "running", force to IDLE
        running_stages = {
            PipelineStage.PLANNING,
            PipelineStage.QUERYING,
            PipelineStage.SYNTHESIZING,
            PipelineStage.REPORTING,
        }
        if current_stage in running_stages:
            current_stage = PipelineStage.IDLE

        state._current_stage = current_stage

        # Restore errors
        state.errors = list(data.get("errors", []))

        # Restore pipeline timing
        state._pipeline_start = data.get("pipeline_start")
        state._pipeline_end = data.get("pipeline_end")

        # Restore stage_results if available
        stage_results_data = data.get("stage_results", {})
        for result_data in stage_results_data.values():
            result = StageResult.from_dict(result_data)
            state._stage_results[result.stage] = result

        # Restore space_progress if available
        space_progress_data = data.get("space_progress", {})
        for name, progress_data in space_progress_data.items():
            state._space_progress[name] = SpaceProgress(
                space_name=progress_data["space_name"],
                status=SpaceQueryStatus(progress_data["status"]),
                start_time=progress_data.get("start_time"),
                end_time=progress_data.get("end_time"),
                current_attempt=progress_data.get("current_attempt", 0),
                error_message=progress_data.get("error_message"),
                cached=progress_data.get("cached", False),
            )

        return state
