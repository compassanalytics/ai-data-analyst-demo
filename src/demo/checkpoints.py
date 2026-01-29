"""Checkpoint system for workshop notebook interactivity.

This module provides save/restore functionality for workshop state,
allowing participants to jump to specific points in the demo or recover
from errors without re-running everything.

Supports both local (Jupyter) and Databricks environments with appropriate
storage backends.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.demo.widgets import is_databricks


# Standard checkpoint names for workshop milestones
CHECKPOINT_SETUP = "setup_complete"
CHECKPOINT_BASIC_QUERY = "basic_query_complete"
CHECKPOINT_MULTI_AGENT = "multi_agent_complete"
CHECKPOINT_REPORT_GENERATED = "report_generated"


@dataclass
class Checkpoint:
    """A saved snapshot of workshop state.

    Attributes:
        name: Unique identifier for this checkpoint
        timestamp: When the checkpoint was created (ISO format)
        config_data: Serialized Config data (excludes token)
        pipeline_state_data: Serialized PipelineState data
        space_configs_data: List of serialized GenieSpaceConfig dicts
        extras: Additional custom data for the checkpoint
    """

    name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    config_data: dict[str, Any] = field(default_factory=dict)
    pipeline_state_data: dict[str, Any] = field(default_factory=dict)
    space_configs_data: list[dict[str, Any]] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "config_data": self.config_data,
            "pipeline_state_data": self.pipeline_state_data,
            "space_configs_data": self.space_configs_data,
            "extras": self.extras,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Restore checkpoint from dictionary."""
        return cls(
            name=data["name"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            config_data=data.get("config_data", {}),
            pipeline_state_data=data.get("pipeline_state_data", {}),
            space_configs_data=data.get("space_configs_data", []),
            extras=data.get("extras", {}),
        )


class CheckpointManager:
    """Manages checkpoint storage and retrieval.

    Automatically selects appropriate storage location based on environment:
    - Local: .workshop_checkpoints/ in current directory
    - Databricks: /dbfs/workshop_checkpoints/

    Example:
        >>> manager = CheckpointManager()
        >>> checkpoint = Checkpoint(
        ...     name="setup_complete",
        ...     config_data=config.to_dict(),
        ...     pipeline_state_data=state.to_dict(include_results=True),
        ... )
        >>> manager.save(checkpoint)
        >>> restored = manager.restore("setup_complete")
    """

    # Local storage directory name
    LOCAL_DIR = ".workshop_checkpoints"
    # DBFS storage directory
    DBFS_DIR = "/dbfs/workshop_checkpoints"

    def __init__(self, base_path: Optional[str] = None) -> None:
        """Initialize checkpoint manager.

        Args:
            base_path: Override default storage path. If None, auto-detects
                      based on environment.
        """
        if base_path:
            self._storage_path = Path(base_path)
        elif is_databricks():
            self._storage_path = Path(self.DBFS_DIR)
        else:
            self._storage_path = Path(self.LOCAL_DIR)

        # Ensure storage directory exists
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Create storage directory if it doesn't exist."""
        try:
            self._storage_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            # In some environments, directory creation may fail
            # We'll handle this gracefully on first write
            pass

    def _checkpoint_file(self, name: str) -> Path:
        """Get the file path for a checkpoint.

        Args:
            name: Checkpoint name

        Returns:
            Path to the checkpoint JSON file
        """
        # Sanitize name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        return self._storage_path / f"{safe_name}.json"

    def save(self, checkpoint: Checkpoint) -> Path:
        """Save a checkpoint to storage.

        Args:
            checkpoint: The checkpoint to save

        Returns:
            Path where checkpoint was saved

        Raises:
            OSError: If unable to write to storage
        """
        self._ensure_storage_exists()
        file_path = self._checkpoint_file(checkpoint.name)

        # Serialize with datetime handling
        data = checkpoint.to_dict()
        json_str = json.dumps(data, indent=2, default=str)

        file_path.write_text(json_str, encoding="utf-8")
        return file_path

    def restore(self, name: str) -> Optional[Checkpoint]:
        """Restore a checkpoint from storage.

        Args:
            name: Name of checkpoint to restore

        Returns:
            Checkpoint if found, None otherwise
        """
        file_path = self._checkpoint_file(name)

        if not file_path.exists():
            return None

        try:
            json_str = file_path.read_text(encoding="utf-8")
            data = json.loads(json_str)
            return Checkpoint.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to restore checkpoint '{name}': {e}")
            return None

    def exists(self, name: str) -> bool:
        """Check if a checkpoint exists.

        Args:
            name: Checkpoint name to check

        Returns:
            True if checkpoint exists
        """
        return self._checkpoint_file(name).exists()

    def delete(self, name: str) -> bool:
        """Delete a checkpoint.

        Args:
            name: Checkpoint name to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = self._checkpoint_file(name)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all available checkpoints.

        Returns:
            List of checkpoint info dicts with 'name', 'timestamp', and 'path'
        """
        checkpoints = []

        if not self._storage_path.exists():
            return checkpoints

        for json_file in sorted(self._storage_path.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                checkpoints.append({
                    "name": data.get("name", json_file.stem),
                    "timestamp": data.get("timestamp", "unknown"),
                    "path": str(json_file),
                })
            except (json.JSONDecodeError, KeyError):
                # Skip invalid checkpoint files
                continue

        return checkpoints


def display_checkpoint_widget(manager: Optional[CheckpointManager] = None) -> Optional[str]:
    """Display an interactive checkpoint selection widget.

    In Databricks, displays a simple selection interface.
    In Jupyter with ipywidgets, shows an interactive dropdown.
    Falls back to text listing if widgets unavailable.

    Args:
        manager: CheckpointManager instance. Creates new one if None.

    Returns:
        Selected checkpoint name, or None if no selection made
    """
    if manager is None:
        manager = CheckpointManager()

    checkpoints = manager.list_checkpoints()

    if not checkpoints:
        print("No checkpoints available.")
        return None

    # Try to use IPython display for interactive selection
    try:
        from IPython.display import display, HTML

        # Build HTML for checkpoint list
        html_parts = [
            '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; '
            'max-width: 600px; padding: 16px; background: #f9fafb; border-radius: 8px;">',
            '<h3 style="margin: 0 0 12px 0; color: #1f2937;">Available Checkpoints</h3>',
            '<table style="width: 100%; border-collapse: collapse;">',
            '<tr style="background: #e5e7eb;">',
            '<th style="padding: 8px; text-align: left; border-bottom: 2px solid #d1d5db;">Name</th>',
            '<th style="padding: 8px; text-align: left; border-bottom: 2px solid #d1d5db;">Timestamp</th>',
            '</tr>',
        ]

        for cp in checkpoints:
            timestamp = cp["timestamp"]
            # Format timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass

            html_parts.append(
                f'<tr style="border-bottom: 1px solid #e5e7eb;">'
                f'<td style="padding: 8px; font-family: monospace; color: #3b82f6;">{cp["name"]}</td>'
                f'<td style="padding: 8px; color: #6b7280;">{timestamp}</td>'
                f'</tr>'
            )

        html_parts.extend([
            '</table>',
            '<p style="margin: 12px 0 0 0; font-size: 14px; color: #6b7280;">',
            'Use <code>manager.restore("checkpoint_name")</code> to restore a checkpoint.',
            '</p>',
            '</div>',
        ])

        display(HTML("".join(html_parts)))

        # Return the most recent checkpoint name as a suggestion
        return checkpoints[-1]["name"] if checkpoints else None

    except ImportError:
        # Fallback to text output
        print("Available Checkpoints:")
        print("-" * 50)
        for cp in checkpoints:
            print(f"  {cp['name']:<30} {cp['timestamp']}")
        print("-" * 50)
        print("\nUse manager.restore('checkpoint_name') to restore.")

        return checkpoints[-1]["name"] if checkpoints else None


def create_checkpoint(
    name: str,
    config: Any,
    pipeline_state: Any,
    space_configs: Optional[list] = None,
    extras: Optional[dict] = None,
    manager: Optional[CheckpointManager] = None,
) -> Checkpoint:
    """Convenience function to create and save a checkpoint.

    Args:
        name: Checkpoint name
        config: Config instance to serialize
        pipeline_state: PipelineState instance to serialize
        space_configs: Optional list of GenieSpaceConfig instances
        extras: Optional additional data to include
        manager: Optional CheckpointManager (creates new if None)

    Returns:
        The saved Checkpoint instance
    """
    if manager is None:
        manager = CheckpointManager()

    # Serialize space configs if provided
    space_configs_data = []
    if space_configs:
        for sc in space_configs:
            if hasattr(sc, "__dict__"):
                # Convert dataclass to dict
                space_configs_data.append({
                    "space_id": getattr(sc, "space_id", ""),
                    "name": getattr(sc, "name", ""),
                    "domain": getattr(sc, "domain", ""),
                    "timeout_seconds": getattr(sc, "timeout_seconds", 120),
                    "retry_count": getattr(sc, "retry_count", 2),
                    "retry_delay": getattr(sc, "retry_delay", 1.0),
                })

    checkpoint = Checkpoint(
        name=name,
        config_data=config.to_dict() if hasattr(config, "to_dict") else {},
        pipeline_state_data=(
            pipeline_state.to_dict(include_results=True)
            if hasattr(pipeline_state, "to_dict")
            else {}
        ),
        space_configs_data=space_configs_data,
        extras=extras or {},
    )

    manager.save(checkpoint)
    return checkpoint
