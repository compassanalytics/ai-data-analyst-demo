"""Widget helpers for Databricks and Jupyter notebook interactivity.

This module provides widget abstractions that work in both Databricks notebooks
(using dbutils.widgets) and local Jupyter (using ipywidgets with fallback).

Phase 2: Databricks-first approach with minimal local fallbacks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WidgetConfig:
    """Configuration gathered from widgets.

    Attributes:
        report_type: Selected report type
        cache_enabled: Whether caching is enabled
        mock_mode: Whether mock mode is enabled
        verbose: Whether verbose output is enabled
        custom_question: Custom question if report_type is "Custom"
    """

    report_type: str = "Q4 Executive Report"
    cache_enabled: bool = True
    mock_mode: bool = False
    verbose: bool = False
    custom_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_type": self.report_type,
            "cache_enabled": self.cache_enabled,
            "mock_mode": self.mock_mode,
            "verbose": self.verbose,
            "custom_question": self.custom_question,
        }


def is_databricks() -> bool:
    """Check if running in Databricks environment."""
    return "DATABRICKS_RUNTIME_VERSION" in os.environ


def is_serverless() -> bool:
    """Check if running on serverless Databricks compute.

    Serverless compute does not have the DBFS FUSE mount available at /dbfs.
    """
    return is_databricks() and not Path("/dbfs").exists()


def _get_dbutils():
    """Get dbutils object in Databricks environment."""
    if not is_databricks():
        return None
    try:
        # In Databricks, dbutils is available globally
        import builtins

        return getattr(builtins, "dbutils", None)
    except Exception:
        return None


class DatabricksWidgets:
    """Widget manager for Databricks notebooks.

    Uses dbutils.widgets for native Databricks widget support.
    """

    def __init__(self) -> None:
        """Initialize Databricks widgets."""
        self._dbutils = _get_dbutils()
        self._initialized = False

    def setup(self) -> None:
        """Create all widgets in the notebook."""
        if not self._dbutils:
            print("Warning: dbutils not available. Widgets not created.")
            return

        try:
            widgets = self._dbutils.widgets

            # Report type dropdown
            widgets.dropdown(
                "report_type",
                "Q4 Executive Report",
                ["Q4 Executive Report", "YTD Summary", "Custom"],
                "Report Type",
            )

            # Cache toggle
            widgets.dropdown(
                "cache_enabled",
                "true",
                ["true", "false"],
                "Cache Enabled",
            )

            # Mock mode toggle
            widgets.dropdown(
                "mock_mode",
                "false",
                ["true", "false"],
                "Mock Mode",
            )

            # Verbose toggle
            widgets.dropdown(
                "verbose",
                "false",
                ["true", "false"],
                "Verbose Output",
            )

            # Custom question text
            widgets.text(
                "custom_question",
                "",
                "Custom Question",
            )

            self._initialized = True
            print("Widgets created. Use the dropdowns above to configure the demo.")

        except Exception as e:
            print(f"Warning: Could not create widgets: {e}")

    def get_config(self) -> WidgetConfig:
        """Get current widget values as WidgetConfig."""
        if not self._dbutils:
            return WidgetConfig()

        try:
            widgets = self._dbutils.widgets
            return WidgetConfig(
                report_type=widgets.get("report_type"),
                cache_enabled=widgets.get("cache_enabled").lower() == "true",
                mock_mode=widgets.get("mock_mode").lower() == "true",
                verbose=widgets.get("verbose").lower() == "true",
                custom_question=widgets.get("custom_question"),
            )
        except Exception:
            return WidgetConfig()

    def remove_all(self) -> None:
        """Remove all widgets."""
        if not self._dbutils:
            return

        try:
            self._dbutils.widgets.removeAll()
            self._initialized = False
        except Exception:
            pass


class LocalWidgets:
    """Widget manager for local Jupyter notebooks.

    Uses ipywidgets when available, falls back to environment variables.
    """

    def __init__(self) -> None:
        """Initialize local widgets."""
        self._widgets: dict[str, Any] = {}
        self._container: Any = None
        self._ipywidgets_available = False

        try:
            import ipywidgets

            self._ipywidgets_available = True
        except ImportError:
            pass

    def setup(self) -> None:
        """Create widgets or show configuration instructions."""
        if not self._ipywidgets_available:
            print("ipywidgets not available. Using environment variables for configuration.")
            print("\nSet these environment variables before running:")
            print("  REPORT_TYPE='Q4 Executive Report'  # or 'YTD Summary', 'Custom'")
            print("  CACHE_ENABLED='true'")
            print("  MOCK_MODE='true'")
            print("  VERBOSE='false'")
            print("  CUSTOM_QUESTION=''")
            return

        try:
            import ipywidgets as widgets
            from IPython.display import display

            # Create widgets
            self._widgets["report_type"] = widgets.Dropdown(
                options=["Q4 Executive Report", "YTD Summary", "Custom"],
                value="Q4 Executive Report",
                description="Report Type:",
                style={"description_width": "100px"},
            )

            self._widgets["cache_enabled"] = widgets.ToggleButton(
                value=True,
                description="Cache Enabled",
                button_style="success",
                icon="check",
            )

            self._widgets["mock_mode"] = widgets.ToggleButton(
                value=os.getenv("MOCK_MODE", "false").lower() == "true",
                description="Mock Mode",
                button_style="info" if os.getenv("MOCK_MODE", "false").lower() == "true" else "",
            )

            self._widgets["verbose"] = widgets.ToggleButton(
                value=False,
                description="Verbose",
                button_style="",
            )

            self._widgets["custom_question"] = widgets.Text(
                value="",
                placeholder="Enter custom question...",
                description="Custom Q:",
                style={"description_width": "100px"},
                layout=widgets.Layout(width="400px"),
            )

            # Layout
            row1 = widgets.HBox(
                [
                    self._widgets["report_type"],
                    self._widgets["cache_enabled"],
                ]
            )
            row2 = widgets.HBox(
                [
                    self._widgets["mock_mode"],
                    self._widgets["verbose"],
                ]
            )
            row3 = self._widgets["custom_question"]

            self._container = widgets.VBox([row1, row2, row3])
            display(self._container)

        except Exception as e:
            print(f"Warning: Could not create widgets: {e}")
            print("Using environment variables for configuration.")

    def get_config(self) -> WidgetConfig:
        """Get current widget values as WidgetConfig."""
        if self._widgets:
            return WidgetConfig(
                report_type=self._widgets["report_type"].value,
                cache_enabled=self._widgets["cache_enabled"].value,
                mock_mode=self._widgets["mock_mode"].value,
                verbose=self._widgets["verbose"].value,
                custom_question=self._widgets["custom_question"].value,
            )

        # Fallback to environment variables
        return WidgetConfig(
            report_type=os.getenv("REPORT_TYPE", "Q4 Executive Report"),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            mock_mode=os.getenv("MOCK_MODE", "false").lower() == "true",
            verbose=os.getenv("VERBOSE", "false").lower() == "true",
            custom_question=os.getenv("CUSTOM_QUESTION", ""),
        )

    def remove_all(self) -> None:
        """Clear widgets."""
        if self._container:
            self._container.close()
        self._widgets.clear()
        self._container = None


def create_widget_manager() -> DatabricksWidgets | LocalWidgets:
    """Create appropriate widget manager for the current environment.

    Returns:
        DatabricksWidgets if in Databricks, LocalWidgets otherwise
    """
    if is_databricks():
        return DatabricksWidgets()
    return LocalWidgets()


def get_question_for_report_type(config: WidgetConfig) -> str:
    """Get the question to analyze based on report type.

    Args:
        config: Widget configuration

    Returns:
        Question string for the selected report type
    """
    questions = {
        "Q4 Executive Report": (
            "Generate a Q4 executive report analyzing sales performance, customer trends, and inventory status"
        ),
        "YTD Summary": (
            "Provide a year-to-date summary of business performance including "
            "revenue trends, customer acquisition, and operational metrics"
        ),
        "Custom": config.custom_question or "Analyze the current business state",
    }
    return questions.get(config.report_type, questions["Q4 Executive Report"])
